"""
Rule-based multimodal threat fusion engine.

Combines acoustic + vision events within a time window to produce
a single explainable threat score and severity label.

Extended (multi-node integration):
  run_hazard_fusion_for_node() handles VCN1 hazard-type nodes (fire,
  air quality, water level) and implements the cross-signal disambiguation
  case: acoustic "no human speech" + elevated fire/smoke → UNATTENDED_FIRE_RISK.
  The original compute_fusion() and run_fusion_for_node() are not modified.
"""

from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AcousticEvent, VisionEvent, HazardEvent, Threat, Alert, Node
from app.config import FUSION_WINDOW_SECONDS
from app.websocket_manager import ws_manager
from app.schemas import AlertOut


def compute_fusion(
    acoustic_conf: float = 0.0,
    vision_person_conf: float = 0.0,
    vision_vehicle_conf: float = 0.0,
) -> tuple[float, str, str]:
    """
    Returns (fused_score, label, severity).
    When only acoustic is present (no vision nodes deployed), acoustic
    confidence is used directly so high-confidence detections still alert.
    """
    has_vision = vision_person_conf > 0.0 or vision_vehicle_conf > 0.0

    if has_vision:
        # Full multimodal fusion
        score = 0.5 * acoustic_conf + 0.3 * vision_person_conf + 0.2 * vision_vehicle_conf
        # Corroboration bonuses
        if acoustic_conf > 0.7 and vision_person_conf > 0.7:
            score = min(1.0, score + 0.15)
        if acoustic_conf > 0.7 and vision_vehicle_conf > 0.7:
            score = min(1.0, score + 0.10)
    else:
        # Acoustic-only mode — use acoustic confidence directly
        score = acoustic_conf

    if score >= 0.85:
        label = "POSSIBLE ILLEGAL LOGGING — HIGH CONFIDENCE"
        severity = "critical"
    elif score >= 0.6:
        label = "SUSPICIOUS ACTIVITY — VERIFY"
        severity = "medium"
    else:
        label = "LOW CONFIDENCE / MONITOR"
        severity = "low"

    return round(score, 4), label, severity


async def run_fusion_for_node(db: AsyncSession, node_id: str):
    """
    Check recent events for a node within the fusion window.
    If threshold met, create a Threat + Alert and broadcast via WebSocket.
    """
    window_start = datetime.utcnow() - timedelta(seconds=FUSION_WINDOW_SECONDS)

    # Get recent acoustic events for this node
    acoustic_result = await db.execute(
        select(AcousticEvent)
        .where(AcousticEvent.node_id == node_id)
        .where(AcousticEvent.recorded_at >= window_start)
        .order_by(AcousticEvent.recorded_at.desc())
        .limit(5)
    )
    acoustic_events = acoustic_result.scalars().all()

    # Get recent vision events for this node (or nearby nodes)
    vision_result = await db.execute(
        select(VisionEvent)
        .where(VisionEvent.node_id == node_id)
        .where(VisionEvent.recorded_at >= window_start)
        .order_by(VisionEvent.recorded_at.desc())
        .limit(5)
    )
    vision_events = vision_result.scalars().all()

    # Extract max confidences
    acoustic_conf = max((e.confidence for e in acoustic_events), default=0.0)
    acoustic_class = None
    if acoustic_events:
        best_acoustic = max(acoustic_events, key=lambda e: e.confidence)
        acoustic_class = best_acoustic.event_class

    vision_person_conf = max(
        (e.confidence for e in vision_events if e.event_class == "person"), default=0.0
    )
    vision_vehicle_conf = max(
        (e.confidence for e in vision_events if e.event_class == "vehicle"), default=0.0
    )

    # Only create a threat if we have at least one meaningful signal
    if acoustic_conf < 0.5 and vision_person_conf < 0.5 and vision_vehicle_conf < 0.5:
        return None

    fused_score, label, severity = compute_fusion(
        acoustic_conf, vision_person_conf, vision_vehicle_conf
    )

    # Get node for lat/lon
    node = await db.get(Node, node_id)
    lat = node.lat if node else 0.0
    lon = node.lon if node else 0.0

    # Check if a threat already exists for this node in the current window
    existing_result = await db.execute(
        select(Threat)
        .where(Threat.node_id == node_id)
        .where(Threat.created_at >= window_start)
        .order_by(Threat.created_at.desc())
        .limit(1)
    )
    existing_threat = existing_result.scalars().first()

    if existing_threat:
        # Update the existing threat with new fused data.
        # Also refresh created_at so this alert sorts to the top of the feed
        # when severity escalates — without this, a hazard alert created once
        # at low severity stays buried under newer acoustic alerts forever.
        existing_threat.fused_score = fused_score
        existing_threat.label = label
        existing_threat.severity = severity
        existing_threat.acoustic_confidence = acoustic_conf
        existing_threat.vision_person_confidence = vision_person_conf
        existing_threat.vision_vehicle_confidence = vision_vehicle_conf
        existing_threat.acoustic_class = acoustic_class
        existing_threat.created_at = datetime.utcnow()
        threat = existing_threat
        # Get associated alert
        alert_result = await db.execute(
            select(Alert).where(Alert.threat_id == threat.id)
        )
        alert = alert_result.scalars().first()
    else:
        # Create new threat
        threat = Threat(
            fused_score=fused_score,
            label=label,
            severity=severity,
            acoustic_confidence=acoustic_conf,
            vision_person_confidence=vision_person_conf,
            vision_vehicle_confidence=vision_vehicle_conf,
            acoustic_class=acoustic_class,
            node_id=node_id,
            lat=lat,
            lon=lon,
            created_at=datetime.utcnow(),
        )
        db.add(threat)
        await db.flush()

        # Create associated alert
        alert = Alert(threat_id=threat.id)
        db.add(alert)

    await db.flush()
    await db.commit()

    # Broadcast to WebSocket clients (only critical and medium)
    if severity in ("critical", "medium"):
        alert_out = AlertOut(
            id=alert.id,
            fused_score=fused_score,
            label=label,
            severity=severity,
            acoustic_confidence=acoustic_conf,
            vision_person_confidence=vision_person_conf,
            vision_vehicle_confidence=vision_vehicle_conf,
            acoustic_class=acoustic_class,
            node_id=node_id,
            generated_at=threat.created_at.isoformat(),
            acknowledged=False,
            acknowledged_by=None,
        )
        await ws_manager.broadcast(alert_out.model_dump_json(by_alias=True))

    return threat


# ── Hazard severity helpers ──────────────────────────────────────────────────

# Firmware emits uppercase NORMAL/WATCH/WARNING/CRITICAL; DB stores lowercase.
# Maps firmware/DB lowercase severity to a normalised 0–1 score for fusion math.
_SEV_TO_SCORE: dict[str, float] = {
    "normal":   0.10,
    "watch":    0.45,
    "warning":  0.70,
    "critical": 0.95,
}

# Firmware risk scores are 0–100 integers; normalise to 0–1.
def _normalise_risk(risk_score: int) -> float:
    return max(0.0, min(1.0, risk_score / 100.0))


def compute_hazard_score(
    hazard_type: str,
    risk_score: int,
    severity: str,
    acoustic_class: str | None = None,
    acoustic_conf: float = 0.0,
) -> tuple[float, str, str]:
    """
    Produce (fused_score, label, backend_severity) for a single hazard-type node.

    NOTE — all thresholds here are MVP rule-based defaults derived from the
    firmware's own placeholder scoring logic.  They have not been validated
    against real-world sensor readings at a deployment site.  Labels and
    severity values should be treated as approximate indicators until
    field calibration is completed per the firmware README.

    Cross-signal case (FIRE hazard only):
        When the forest node's acoustic pipeline reports no human speech
        (acoustic_class is not 'human_activity' / 'chainsaw' / 'gunshot' /
        'vehicle' AND acoustic_conf is below a low threshold) alongside
        elevated fire risk, confidence of an UNATTENDED fire event is raised.
        This is surfaced as a distinct label rather than a generic fire alert.
    """
    norm_score = _normalise_risk(risk_score)

    # ── Fire / Smoke ──────────────────────────────────────────────────────────
    if hazard_type == "FIRE":
        # Determine whether the acoustic context suggests human presence.
        # If acoustic_class is absent or is a "no-human" class and confidence
        # is below 0.5, we treat the area as unpopulated.
        human_presence_classes = {"human_activity", "chainsaw", "gunshot", "vehicle"}
        human_likely = (
            acoustic_class in human_presence_classes
            and acoustic_conf >= 0.5
        )

        if severity in ("warning", "critical"):
            if not human_likely and acoustic_conf < 0.5:
                # Cross-signal disambiguation: elevated fire + no acoustic human signal
                # → raise confidence of an UNATTENDED fire (no one nearby to have lit it)
                boosted_score = min(1.0, norm_score + 0.15)
                fused_label = "UNATTENDED FIRE RISK — POSSIBLE WILDFIRE (no human activity detected)"
                backend_severity = "critical" if boosted_score >= 0.75 else "medium"
                return round(boosted_score, 4), fused_label, backend_severity
            else:
                # Human likely present — fire may be deliberate but not unattended
                fused_label = "FIRE/SMOKE DETECTED — POSSIBLE DELIBERATE BURN OR CAMPFIRE"
                backend_severity = "critical" if norm_score >= 0.75 else "medium"
                return norm_score, fused_label, backend_severity
        elif severity == "watch":
            fused_label = "ELEVATED SMOKE/HEAT — MONITOR CLOSELY"
            return norm_score, fused_label, "medium"
        else:
            fused_label = "FIRE MODULE — NORMAL CONDITIONS"
            return norm_score, fused_label, "low"

    # ── Air Quality ───────────────────────────────────────────────────────────
    elif hazard_type == "AIR_QUALITY":
        if severity == "critical":
            fused_label = "CRITICAL AIR QUALITY ANOMALY — POSSIBLE INDUSTRIAL RELEASE"
            backend_severity = "critical"
        elif severity == "warning":
            fused_label = "ELEVATED POLLUTION DETECTED — VERIFY SOURCE"
            backend_severity = "medium"
        elif severity == "watch":
            fused_label = "AIR QUALITY ABOVE BASELINE — MONITOR"
            backend_severity = "medium"
        else:
            fused_label = "AIR QUALITY — NORMAL CONDITIONS"
            backend_severity = "low"
        return norm_score, fused_label, backend_severity

    # ── Water Level / Flash-Flood ─────────────────────────────────────────────
    elif hazard_type == "WATER_LEVEL":
        if severity == "critical":
            fused_label = "CRITICAL WATER LEVEL — FLASH FLOOD RISK"
            backend_severity = "critical"
        elif severity == "warning":
            fused_label = "RISING WATER LEVEL — POTENTIAL FLOOD WARNING"
            backend_severity = "medium"
        elif severity == "watch":
            fused_label = "WATER LEVEL ELEVATED — WATCH REQUIRED"
            backend_severity = "medium"
        else:
            fused_label = "WATER LEVEL — NORMAL CONDITIONS"
            backend_severity = "low"
        return norm_score, fused_label, backend_severity

    # ── Unknown hazard type (should not reach here) ────────────────────────────
    return norm_score, f"HAZARD DETECTED — {hazard_type}", "medium"


async def run_hazard_fusion_for_node(db: AsyncSession, node_id: str):
    """
    Fusion for VCN1 hazard-type nodes (fire, air_quality, water_level).

    For FIRE nodes on the forest boundary, this function also queries the
    most recent acoustic events for FOR01 (or whichever acoustic node shares
    the same site) to apply the cross-signal disambiguation rule.

    Reuses the existing Threat/Alert tables so all alerts are visible in
    the same dashboard feed, consistent with acoustic/vision alerts.
    """
    window_start = datetime.utcnow() - timedelta(seconds=FUSION_WINDOW_SECONDS)

    # Get the highest-risk hazard reading for this node in the fusion window.
    # Order by risk_score DESC first so the most threatening reading drives
    # fusion — not the most recently arrived one.  When the simulator sends
    # readings every ~6s and multiple land in the same second (CRITICAL then
    # WATCH 300ms later), ordering by recorded_at alone would non-deterministically
    # pick the lower-risk event.  risk_score DESC, recorded_at DESC as tiebreaker
    # guarantees the worst-case reading is always used.
    hazard_result = await db.execute(
        select(HazardEvent)
        .where(HazardEvent.node_id == node_id)
        .where(HazardEvent.recorded_at >= window_start)
        .order_by(HazardEvent.risk_score.desc(), HazardEvent.recorded_at.desc())
        .limit(1)
    )
    latest_hazard = hazard_result.scalars().first()
    if not latest_hazard:
        return None

    # For fire nodes, look up recent acoustic context from the forest node.
    # The forest acoustic node ID is FOR01's paired acoustic node (NODE_01 by
    # convention in this deployment).  If that pairing differs in your setup,
    # update FOREST_ACOUSTIC_NODE_ID or pass it as config.
    # NOTE: This cross-signal lookup is scoped to the same fusion window so
    # we only correlate events that happened around the same time.
    acoustic_class: str | None = None
    acoustic_conf: float = 0.0

    if latest_hazard.hazard_type == "FIRE":
        # Look for any recent acoustic human-presence event in the window.
        # We deliberately pick the highest-confidence HUMAN-PRESENCE class
        # event, not just the highest-confidence event overall — a normal/animal
        # detection at 0.98 confidence should not suppress a human_activity at
        # 0.85 confidence from signalling human presence.
        human_presence_classes = {"human_activity", "chainsaw", "gunshot", "vehicle"}
        acoustic_q = await db.execute(
            select(AcousticEvent)
            .where(AcousticEvent.recorded_at >= window_start)
            .order_by(AcousticEvent.recorded_at.desc())
            .limit(10)
        )
        recent_acoustic = acoustic_q.scalars().all()
        # First try to find a human-presence class event
        human_events = [e for e in recent_acoustic if e.event_class in human_presence_classes]
        if human_events:
            best = max(human_events, key=lambda e: e.confidence)
        elif recent_acoustic:
            best = max(recent_acoustic, key=lambda e: e.confidence)
        else:
            best = None
        if best:
            acoustic_class = best.event_class
            acoustic_conf = best.confidence

    fused_score, label, severity = compute_hazard_score(
        hazard_type=latest_hazard.hazard_type,
        risk_score=latest_hazard.risk_score,
        severity=latest_hazard.severity,
        acoustic_class=acoustic_class,
        acoustic_conf=acoustic_conf,
    )

    # Only create a threat for watch/warning/critical — skip normal-condition readings
    if latest_hazard.severity == "normal" and severity == "low":
        return None

    node = await db.get(Node, node_id)
    lat = node.lat if node else 0.0
    lon = node.lon if node else 0.0

    # Upsert threat in the shared threats table
    existing_result = await db.execute(
        select(Threat)
        .where(Threat.node_id == node_id)
        .where(Threat.created_at >= window_start)
        .order_by(Threat.created_at.desc())
        .limit(1)
    )
    existing_threat = existing_result.scalars().first()

    if existing_threat:
        existing_threat.fused_score = fused_score
        existing_threat.label = label
        existing_threat.severity = severity
        existing_threat.acoustic_class = f"{latest_hazard.hazard_type}:{latest_hazard.risk_score}"
        existing_threat.created_at = datetime.utcnow()   # refresh so it sorts to top on escalation
        threat = existing_threat
        alert_result = await db.execute(
            select(Alert).where(Alert.threat_id == threat.id)
        )
        alert = alert_result.scalars().first()
    else:
        threat = Threat(
            fused_score=fused_score,
            label=label,
            severity=severity,
            acoustic_confidence=0.0,
            vision_person_confidence=0.0,
            vision_vehicle_confidence=0.0,
            acoustic_class=f"{latest_hazard.hazard_type}:{latest_hazard.risk_score}",
            node_id=node_id,
            lat=lat,
            lon=lon,
            created_at=datetime.utcnow(),
        )
        db.add(threat)
        await db.flush()
        alert = Alert(threat_id=threat.id)
        db.add(alert)

    await db.flush()
    await db.commit()

    # Broadcast to WebSocket clients for medium and critical
    if severity in ("critical", "medium"):
        alert_out = AlertOut(
            id=alert.id,
            fused_score=fused_score,
            label=label,
            severity=severity,
            acoustic_confidence=0.0,
            vision_person_confidence=0.0,
            vision_vehicle_confidence=0.0,
            acoustic_class=f"{latest_hazard.hazard_type}:{latest_hazard.risk_score}",
            node_id=node_id,
            generated_at=threat.created_at.isoformat(),
            acknowledged=False,
            acknowledged_by=None,
        )
        await ws_manager.broadcast(alert_out.model_dump_json(by_alias=True))

    return threat
