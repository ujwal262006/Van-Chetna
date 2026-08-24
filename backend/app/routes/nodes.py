"""
Node status endpoint.
GET /nodes/status — Returns all nodes with health info.
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Node
from app.schemas import NodeStatusOut
from app.config import NODE_OFFLINE_MINUTES

router = APIRouter()


@router.get("/nodes/status", response_model=list[NodeStatusOut])
async def get_node_status(db: AsyncSession = Depends(get_db)):
    """
    Returns all registered nodes with online/offline status.
    A node is considered offline if not seen for NODE_OFFLINE_MINUTES.
    """
    result = await db.execute(select(Node))
    nodes = result.scalars().all()

    cutoff = datetime.utcnow() - timedelta(minutes=NODE_OFFLINE_MINUTES)

    nodes_out = []
    for node in nodes:
        # Auto-update status based on last_seen
        status = "online" if node.last_seen and node.last_seen >= cutoff else "offline"
        if node.status != status:
            node.status = status

        nodes_out.append(NodeStatusOut(
            node_id=node.node_id,
            last_seen=node.last_seen.isoformat() if node.last_seen else "",
            battery_pct=node.battery_pct,
            status=status,
            lat=node.lat,
            lon=node.lon,
        ))

    await db.commit()
    return nodes_out
