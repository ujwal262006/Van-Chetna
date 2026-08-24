"""
Rule-based multimodal threat fusion engine.

Combines acoustic + vision events within a time window to produce
a single explainable threat score and severity label.
"""

from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AcousticEvent, VisionEvent, Threat, Alert, Node
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
    Mirrors the fusion logic from the MVP plan §15.
    """
    score = 0.5 * acoustic_conf + 0.3 * vision_person_conf + 0.2 * vision_vehicle_conf

    # Corroboration bonuses
    if acoustic_conf > 0.7 and vision_person_conf > 0.7:
        score = min(1.0, score + 0.15)
    if acoustic_conf > 0.7 and vision_vehicle_conf > 0.7:
        score = min(1.0, score + 0.10)

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
        # Update the existing threat with new fused data
        existing_threat.fused_score = fused_score
        existing_threat.label = label
        existing_threat.severity = severity
        existing_threat.acoustic_confidence = acoustic_conf
        existing_threat.vision_person_confidence = vision_person_conf
        existing_threat.vision_vehicle_confidence = vision_vehicle_conf
        existing_threat.acoustic_class = acoustic_class
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
