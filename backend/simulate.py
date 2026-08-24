"""
Event simulator — sends fake sensor events to POST /events at regular intervals.
Simulates a live sensor network for demo/testing without hardware.

Run: python simulate.py
"""

import asyncio
import random
import time
import httpx

API_URL = "http://localhost:8000"

NODES = [
    {"node_id": "NODE_01", "sensor_type": "acoustic", "lat": 21.1458, "lon": 79.0882, "battery_pct": 78},
    {"node_id": "NODE_02", "sensor_type": "acoustic", "lat": 21.1502, "lon": 79.0925, "battery_pct": 91},
    {"node_id": "NODE_04", "sensor_type": "vision", "lat": 21.1480, "lon": 79.0960, "battery_pct": 64},
]

ACOUSTIC_CLASSES = ["chainsaw", "vehicle", "human_activity", "animal", "normal"]
VISION_CLASSES = ["person", "vehicle"]

# Weights: make threatening events less frequent but present
ACOUSTIC_WEIGHTS = [0.15, 0.15, 0.1, 0.1, 0.5]


async def send_event(client: httpx.AsyncClient, node: dict):
    """Generate and send a single simulated event."""
    is_vision = node["sensor_type"] == "vision"

    if is_vision:
        event_class = random.choice(VISION_CLASSES)
    else:
        event_class = random.choices(ACOUSTIC_CLASSES, weights=ACOUSTIC_WEIGHTS, k=1)[0]

    # Non-normal events get higher confidence
    if event_class == "normal":
        confidence = round(random.uniform(0.8, 0.99), 2)
    else:
        confidence = round(random.uniform(0.6, 0.95), 2)

    payload = {
        "node_id": node["node_id"],
        "event_id": f"evt_{int(time.time() * 1000)}_{random.randint(100, 999)}",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sensor_type": node["sensor_type"],
        "class": event_class,
        "confidence": confidence,
        "battery_pct": node["battery_pct"] - random.randint(0, 3),
        "lat": node["lat"],
        "lon": node["lon"],
    }

    try:
        resp = await client.post(f"{API_URL}/events", json=payload)
        status = "✅" if resp.status_code == 201 else f"⚠️  {resp.status_code}"
        print(f"{status} [{node['node_id']}] {event_class} ({confidence}) → {resp.json().get('status', '')}")
    except Exception as e:
        print(f"❌ [{node['node_id']}] Error: {e}")


async def main():
    print("🌲 Forest Guard Event Simulator")
    print(f"   Sending events to {API_URL}/events")
    print("   Press Ctrl+C to stop.\n")

    async with httpx.AsyncClient() as client:
        while True:
            node = random.choice(NODES)
            await send_event(client, node)
            # Random interval: 2-8 seconds between events
            await asyncio.sleep(random.uniform(2, 8))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 Simulator stopped.")
