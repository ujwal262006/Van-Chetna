"""
Node status endpoints.
GET /nodes/status   — Returns all nodes with health info (existing, extended with node_type).
GET /nodes/summary  — Returns all nodes with health + latest hazard reading per node.
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Node, HazardEvent
from app.schemas import NodeStatusOut, NodeCurrentStatus, MultiNodeSummary, HazardEventOut
from app.config import NODE_OFFLINE_MINUTES

router = APIRouter()


@router.get("/nodes/status", response_model=list[NodeStatusOut])
async def get_node_status(db: AsyncSession = Depends(get_db)):
    """
    Returns all registered nodes with online/offline status.
    A node is considered offline if not seen for NODE_OFFLINE_MINUTES.
    Extended: now includes node_type so the frontend can render distinct
    icons per environment type.
    """
    result = await db.execute(select(Node))
    nodes = result.scalars().all()

    cutoff = datetime.utcnow() - timedelta(minutes=NODE_OFFLINE_MINUTES)

    nodes_out = []
    for node in nodes:
        status = "online" if node.last_seen and node.last_seen >= cutoff else "offline"
        if node.status != status:
            node.status = status

        nodes_out.append(NodeStatusOut(
            node_id=node.node_id,
            node_type=node.node_type,
            last_seen=node.last_seen.isoformat() if node.last_seen else "",
            battery_pct=node.battery_pct,
            status=status,
            lat=node.lat,
            lon=node.lon,
        ))

    await db.commit()
    return nodes_out


@router.get("/nodes/summary", response_model=MultiNodeSummary)
async def get_nodes_summary(db: AsyncSession = Depends(get_db)):
    """
    Unified multi-node summary: every node with its current health AND
    its latest hazard reading (for fire/air_quality/water_level nodes).
    Acoustic/vision nodes have latest_hazard=null.

    This is the primary endpoint for the frontend dashboard's multi-node
    status panel and map legend.
    """
    result = await db.execute(select(Node))
    nodes = result.scalars().all()

    cutoff = datetime.utcnow() - timedelta(minutes=NODE_OFFLINE_MINUTES)
    hazard_types = {"fire", "air_quality", "water_level"}

    node_summaries = []
    online_count = 0
    offline_count = 0

    for node in nodes:
        status = "online" if node.last_seen and node.last_seen >= cutoff else "offline"
        if node.status != status:
            node.status = status

        if status == "online":
            online_count += 1
        else:
            offline_count += 1

        latest_hazard_out: HazardEventOut | None = None

        if node.node_type in hazard_types:
            hazard_result = await db.execute(
                select(HazardEvent)
                .where(HazardEvent.node_id == node.node_id)
                .order_by(HazardEvent.recorded_at.desc())
                .limit(1)
            )
            latest = hazard_result.scalars().first()
            if latest:
                latest_hazard_out = HazardEventOut(
                    id=latest.id,
                    event_id=latest.event_id,
                    node_id=latest.node_id,
                    hazard_type=latest.hazard_type,
                    risk_score=latest.risk_score,
                    severity=latest.severity,
                    confidence=latest.confidence,
                    sensor_value_1=latest.sensor_value_1,
                    sensor_value_2=latest.sensor_value_2,
                    sensor_value_3=latest.sensor_value_3,
                    rssi=latest.rssi,
                    snr=latest.snr,
                    recorded_at=latest.recorded_at.isoformat(),
                )

        node_summaries.append(NodeCurrentStatus(
            node_id=node.node_id,
            node_type=node.node_type,
            last_seen=node.last_seen.isoformat() if node.last_seen else "",
            battery_pct=node.battery_pct,
            status=status,
            lat=node.lat,
            lon=node.lon,
            latest_hazard=latest_hazard_out,
        ))

    await db.commit()

    return MultiNodeSummary(
        nodes=node_summaries,
        total_online=online_count,
        total_offline=offline_count,
    )
