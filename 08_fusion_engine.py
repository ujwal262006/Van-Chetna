"""
08_fusion_engine.py

The rule-based multimodal fusion engine from the architecture doc (Section 15).
Combines acoustic events (from your trained model) with vision events (from
whichever teammate builds that node, or simulated for now) into one
explainable threat score.

This is standalone and testable RIGHT NOW, even with zero hardware connected --
it just needs event dicts shaped like what your gateway will eventually produce.
That's the point: you can build and demo this before the backend/frontend/
hardware are finished, then wire it in once they are.

Run: python 08_fusion_engine.py     (runs the built-in self-test scenarios)
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timezone
import json


@dataclass
class SensorEvent:
    node_id: str
    sensor_type: str        # 'acoustic' | 'vision'
    event_class: str        # e.g. 'chainsaw', 'person', 'vehicle'
    confidence: float
    timestamp: str           # ISO8601
    lat: Optional[float] = None
    lon: Optional[float] = None


def fuse_events(acoustic_event: Optional[SensorEvent],
                 vision_person_event: Optional[SensorEvent] = None,
                 vision_vehicle_event: Optional[SensorEvent] = None) -> dict:
    """
    Matches Section 15 of the architecture doc. Only events within the same
    time window (caller's responsibility to have already grouped them -- see
    group_events_by_window below) should be passed in together.
    """
    acoustic_conf = acoustic_event.confidence if acoustic_event else 0.0
    vision_person_conf = vision_person_event.confidence if vision_person_event else 0.0
    vision_vehicle_conf = vision_vehicle_event.confidence if vision_vehicle_event else 0.0

    score = 0.5 * acoustic_conf + 0.3 * vision_person_conf + 0.2 * vision_vehicle_conf

    # Corroboration bonus: independent signals agreeing is stronger evidence
    # than any single signal alone -- this is the actual "innovation" point
    # for judges, not just a bigger number.
    if acoustic_conf > 0.7 and vision_person_conf > 0.7:
        score = min(1.0, score + 0.15)
    if acoustic_conf > 0.7 and vision_vehicle_conf > 0.7:
        score = min(1.0, score + 0.10)

    # IMPORTANT: with the weights above, acoustic-only can never exceed 0.5,
    # so it could never cross the 0.6 "SUSPICIOUS" threshold no matter how
    # confident the detection is. That's wrong -- a highly confident chainsaw
    # detection is meaningful evidence on its own, especially since acoustic
    # is your only built sensor right now. A single strong acoustic signal
    # earns "SUSPICIOUS ACTIVITY -- VERIFY" on its own merit; only
    # MULTIMODAL corroboration earns the top "CRITICAL" tier. This keeps the
    # fusion bonus meaningful (corroboration still gets you to CRITICAL
    # faster) without making single-sensor detections look artificially weak.
    strong_acoustic_alone = acoustic_conf >= 0.85 and vision_person_conf == 0.0 and vision_vehicle_conf == 0.0

    if score >= 0.85:
        label = "POSSIBLE ILLEGAL LOGGING — HIGH CONFIDENCE"
        severity = "critical"
    elif score >= 0.6 or strong_acoustic_alone:
        label = "SUSPICIOUS ACTIVITY — VERIFY"
        severity = "medium"
    else:
        label = "LOW CONFIDENCE / MONITOR"
        severity = "low"

    return {
        "fused_score": round(score, 3),
        "label": label,
        "severity": severity,
        "acoustic_confidence": round(acoustic_conf, 3),
        "vision_person_confidence": round(vision_person_conf, 3),
        "vision_vehicle_confidence": round(vision_vehicle_conf, 3),
        "acoustic_class": acoustic_event.event_class if acoustic_event else None,
        "node_id": acoustic_event.node_id if acoustic_event else (
            vision_person_event.node_id if vision_person_event else None
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def group_events_by_window(events: list[SensorEvent], window_sec: float = 30.0) -> list[list[SensorEvent]]:
    """
    Groups events that fall within `window_sec` of each other into clusters,
    so events from independent sensors reporting the "same" real-world moment
    get fused together, per Section 15's "same node cluster within a defined
    time window" rule.
    """
    def to_epoch(ts):
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()

    sorted_events = sorted(events, key=lambda e: to_epoch(e.timestamp))
    groups, current_group, window_start = [], [], None

    for e in sorted_events:
        t = to_epoch(e.timestamp)
        if window_start is None or (t - window_start) <= window_sec:
            current_group.append(e)
            if window_start is None:
                window_start = t
        else:
            groups.append(current_group)
            current_group = [e]
            window_start = t
    if current_group:
        groups.append(current_group)
    return groups


def process_event_batch(events: list[SensorEvent], window_sec: float = 30.0) -> list[dict]:
    """
    Full pipeline: group events by time window, then fuse each group.
    This is what the backend calls whenever new events arrive.
    """
    results = []
    for group in group_events_by_window(events, window_sec):
        acoustic = next((e for e in group if e.sensor_type == "acoustic"), None)
        vision_person = next((e for e in group if e.sensor_type == "vision" and e.event_class == "person"), None)
        vision_vehicle = next((e for e in group if e.sensor_type == "vision" and e.event_class == "vehicle"), None)
        if acoustic or vision_person or vision_vehicle:
            results.append(fuse_events(acoustic, vision_person, vision_vehicle))
    return results


# ---------------------------------------------------------------------------
# Self-test: demonstrates the exact demo scenario from your architecture doc
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 70)
    print("SCENARIO 1: Acoustic-only chainsaw detection (your current real capability)")
    print("=" * 70)
    acoustic_only = [
        SensorEvent("NODE_01", "acoustic", "chainsaw", 0.91, "2026-08-15T14:31:22+00:00", 30.4520, 77.5890),
    ]
    for r in process_event_batch(acoustic_only):
        print(json.dumps(r, indent=2))

    print("\n" + "=" * 70)
    print("SCENARIO 2: Chainsaw + person + vehicle, all corroborating (full demo moment)")
    print("=" * 70)
    full_corroboration = [
        SensorEvent("NODE_01", "acoustic", "chainsaw", 0.91, "2026-08-15T14:31:22+00:00", 30.4520, 77.5890),
        SensorEvent("NODE_02", "vision", "person", 0.87, "2026-08-15T14:31:30+00:00", 30.4521, 77.5891),
        SensorEvent("NODE_02", "vision", "vehicle", 0.76, "2026-08-15T14:31:35+00:00", 30.4521, 77.5891),
    ]
    for r in process_event_batch(full_corroboration):
        print(json.dumps(r, indent=2))

    print("\n" + "=" * 70)
    print("SCENARIO 3: Weak/uncertain single signal (should NOT be a critical alert)")
    print("=" * 70)
    weak_signal = [
        SensorEvent("NODE_01", "acoustic", "vehicle", 0.45, "2026-08-15T14:31:22+00:00"),
    ]
    for r in process_event_batch(weak_signal):
        print(json.dumps(r, indent=2))

    print("\n" + "=" * 70)
    print("SCENARIO 4: Events too far apart in time (30+ min gap -> NOT fused together)")
    print("=" * 70)
    far_apart = [
        SensorEvent("NODE_01", "acoustic", "chainsaw", 0.9, "2026-08-15T14:00:00+00:00"),
        SensorEvent("NODE_02", "vision", "person", 0.9, "2026-08-15T14:45:00+00:00"),
    ]
    for r in process_event_batch(far_apart, window_sec=30.0):
        print(json.dumps(r, indent=2))
    print("(Should print TWO separate results, each scored on its own -- not one fused event)")
