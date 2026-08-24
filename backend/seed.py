"""
Seed script — populates the database with sample nodes and events for testing.
Run: python seed.py
"""

import asyncio
import random
from datetime import datetime, timedelta

from app.database import engine, async_session, Base
from app.models import Node, AcousticEvent, VisionEvent


NODES = [
    {"node_id": "NODE_01", "node_type": "acoustic", "lat": 21.1458, "lon": 79.0882, "battery_pct": 78},
    {"node_id": "NODE_02", "node_type": "acoustic", "lat": 21.1502, "lon": 79.0925, "battery_pct": 91},
    {"node_id": "NODE_03", "node_type": "acoustic", "lat": 21.1535, "lon": 79.0850, "battery_pct": 12},
    {"node_id": "NODE_04", "node_type": "vision", "lat": 21.1480, "lon": 79.0960, "battery_pct": 64},
]

ACOUSTIC_CLASSES = ["chainsaw", "vehicle", "human_activity", "animal", "normal", "gunshot"]
VISION_CLASSES = ["person", "vehicle"]


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        # Create nodes
        for n in NODES:
            node = await db.get(Node, n["node_id"])
            if not node:
                node = Node(
                    node_id=n["node_id"],
                    node_type=n["node_type"],
                    lat=n["lat"],
                    lon=n["lon"],
                    last_seen=datetime.utcnow() - timedelta(seconds=random.randint(5, 300)),
                    battery_pct=n["battery_pct"],
                    status="online",
                )
                db.add(node)

        await db.commit()

        # Create sample acoustic events
        for i in range(15):
            node = random.choice(NODES[:3])  # acoustic nodes
            event = AcousticEvent(
                event_id=f"evt_seed_{i:03d}",
                node_id=node["node_id"],
                event_class=random.choice(ACOUSTIC_CLASSES),
                confidence=round(random.uniform(0.5, 0.98), 2),
                lat=node["lat"],
                lon=node["lon"],
                recorded_at=datetime.utcnow() - timedelta(seconds=random.randint(10, 7200)),
            )
            db.add(event)

        # Create sample vision events
        for i in range(5):
            node = NODES[3]  # vision node
            event = VisionEvent(
                event_id=f"evt_vis_seed_{i:03d}",
                node_id=node["node_id"],
                event_class=random.choice(VISION_CLASSES),
                confidence=round(random.uniform(0.5, 0.95), 2),
                lat=node["lat"],
                lon=node["lon"],
                recorded_at=datetime.utcnow() - timedelta(seconds=random.randint(10, 3600)),
            )
            db.add(event)

        await db.commit()
        print("✅ Seeded database with nodes and sample events.")


if __name__ == "__main__":
    asyncio.run(seed())
