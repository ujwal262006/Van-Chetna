"""
10_simulate_events.py

Generates realistic fake sensor events and runs them through the (already
working, already tested) fusion engine from 08_fusion_engine.py. Serves two
purposes:

  1. TEST HARNESS for Member 3: gives the backend real, correctly-shaped
     JSON to develop against, starting NOW -- no need to wait for real
     hardware. Point this at the backend's POST /events endpoint once it
     exists (see --post-to flag).

  2. DEMO FALLBACK: if real hardware has any trouble on demo day, this
     script drives the exact same backend + dashboard with realistic event
     sequences, so the SOFTWARE can still be demoed convincingly. This is a
     required part of the architecture doc's failure-proofing plan, not
     optional polish.

Every event this generates matches SCHEMAS.md section 1 exactly -- if you
change the schema, update both this file and SCHEMAS.md together.

Usage:
  # Print simulated events + fused results to console (no backend needed)
  python 10_simulate_events.py

  # Run the "illegal logging" demo scenario specifically
  python 10_simulate_events.py --scenario logging

  # POST events to a running backend as they're generated
  python 10_simulate_events.py --post-to http://localhost:8000/events
"""

import argparse
import json
import random
import time
import sys
from datetime import datetime, timezone

sys.path.insert(0, ".")
from importlib.util import spec_from_file_location, module_from_spec


def _load_fusion_module():
    spec = spec_from_file_location("fusion_engine", "08_fusion_engine.py")
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


fusion = _load_fusion_module()

NODE_LOCATIONS = {
    "NODE_01": (30.4520, 77.5890),
    "NODE_02": (30.4521, 77.5891),
}

ACOUSTIC_CLASSES = ["normal_environmental", "animal", "human_activity", "vehicle", "chainsaw", "fire"]
VISION_CLASSES = ["person", "vehicle"]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def make_acoustic_event(node_id, event_class, confidence, battery_pct=None):
    lat, lon = NODE_LOCATIONS.get(node_id, (0.0, 0.0))
    return {
        "node_id": node_id,
        "event_id": f"evt_{int(time.time()*1000)}_{random.randint(100,999)}",
        "timestamp": now_iso(),
        "sensor_type": "acoustic",
        "class": event_class,
        "confidence": round(confidence, 3),
        "battery_pct": battery_pct if battery_pct is not None else random.randint(60, 100),
        "lat": lat,
        "lon": lon,
    }


def make_vision_event(node_id, event_class, confidence, battery_pct=None):
    lat, lon = NODE_LOCATIONS.get(node_id, (0.0, 0.0))
    return {
        "node_id": node_id,
        "event_id": f"evt_{int(time.time()*1000)}_{random.randint(100,999)}",
        "timestamp": now_iso(),
        "sensor_type": "vision",
        "class": event_class,
        "confidence": round(confidence, 3),
        "battery_pct": battery_pct if battery_pct is not None else random.randint(60, 100),
        "lat": lat,
        "lon": lon,
    }


def raw_event_to_sensor_event(raw):
    """Converts the SCHEMAS.md JSON shape into the SensorEvent dataclass
    08_fusion_engine.py expects."""
    return fusion.SensorEvent(
        node_id=raw["node_id"],
        sensor_type=raw["sensor_type"],
        event_class=raw["class"],
        confidence=raw["confidence"],
        timestamp=raw["timestamp"],
        lat=raw.get("lat"),
        lon=raw.get("lon"),
    )


def post_event(url, raw_event):
    try:
        import requests
        resp = requests.post(url, json=raw_event, timeout=3)
        print(f"  -> POSTed to backend, status {resp.status_code}")
    except ImportError:
        print("  -> 'requests' not installed (pip install requests) -- skipping POST, printing only")
    except Exception as e:
        print(f"  -> POST failed ({e}) -- backend may not be running yet, that's OK for now")


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

def scenario_random_background(n_events=15, post_to=None):
    """Ambient forest noise -- mostly normal, occasional low-confidence blips.
    Good for testing the backend doesn't choke on high-volume low-signal traffic."""
    print("=== SCENARIO: Random background noise (no real threats) ===\n")
    events = []
    for _ in range(n_events):
        node = random.choice(list(NODE_LOCATIONS.keys()))
        cls = random.choices(
            ACOUSTIC_CLASSES,
            weights=[40, 20, 15, 10, 3, 2],  # mostly normal/animal, rare chainsaw/fire
        )[0]
        conf = random.uniform(0.3, 0.6) if cls == "normal_environmental" else random.uniform(0.5, 0.95)
        raw = make_acoustic_event(node, cls, conf)
        events.append(raw)
        print(json.dumps(raw))
        if post_to:
            post_event(post_to, raw)
        time.sleep(0.3)
    return events


def scenario_logging_demo(post_to=None):
    """The headline demo moment: chainsaw + person + vehicle, all corroborating,
    within the same time window -- should produce a CRITICAL fused alert."""
    print("=== SCENARIO: Illegal logging demo (full corroboration) ===\n")
    raw_events = [
        make_acoustic_event("NODE_01", "chainsaw", 0.91),
        make_vision_event("NODE_02", "person", 0.87),
        make_vision_event("NODE_02", "vehicle", 0.76),
    ]
    sensor_events = []
    for raw in raw_events:
        print(f"Event: {json.dumps(raw)}")
        if post_to:
            post_event(post_to, raw)
        sensor_events.append(raw_event_to_sensor_event(raw))
        time.sleep(0.5)

    print("\n--- Running fusion engine on this batch ---")
    results = fusion.process_event_batch(sensor_events, window_sec=30.0)
    for r in results:
        print(json.dumps(r, indent=2))
    return raw_events, results


def scenario_acoustic_only_chainsaw(post_to=None):
    """Your CURRENT real capability: acoustic node alone detects a chainsaw.
    Should produce a MEDIUM ("SUSPICIOUS ACTIVITY") alert, not critical --
    this is what your actual hardware will produce until a vision node exists."""
    print("=== SCENARIO: Acoustic-only chainsaw detection (current real capability) ===\n")
    raw = make_acoustic_event("NODE_01", "chainsaw", 0.88)
    print(f"Event: {json.dumps(raw)}")
    if post_to:
        post_event(post_to, raw)

    sensor_event = raw_event_to_sensor_event(raw)
    results = fusion.process_event_batch([sensor_event], window_sec=30.0)
    for r in results:
        print(json.dumps(r, indent=2))
    return [raw], results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=["background", "logging", "acoustic_only", "all"],
                         default="all", help="Which scenario to run")
    parser.add_argument("--post-to", default=None,
                         help="Backend URL to POST events to, e.g. http://localhost:8000/events")
    args = parser.parse_args()

    if args.scenario in ("background", "all"):
        scenario_random_background(post_to=args.post_to)
        print()
    if args.scenario in ("acoustic_only", "all"):
        scenario_acoustic_only_chainsaw(post_to=args.post_to)
        print()
    if args.scenario in ("logging", "all"):
        scenario_logging_demo(post_to=args.post_to)


if __name__ == "__main__":
    main()
