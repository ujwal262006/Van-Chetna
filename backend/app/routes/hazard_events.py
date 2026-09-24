"""
Hazard-event ingestion and retrieval endpoints.

POST /hazard-events
    Called by vcn1_gateway_bridge.py for every valid VCN1 packet
    received from the LoRa gateway (URB01, RIV01, FOR01 fire module).

GET /hazard-events
    Returns recent hazard readings across all nodes, newest first.
    Supports filtering by hazard_type and/or node_id.

GET /hazard-events/{node_id}/history
    Time-series history for a single node — used by the frontend
    trend panel (mirrors the existing GET /events pattern).
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.models import Node, HazardEvent
from app.schemas import (
    HazardEventIn, HazardEventOut, HazardEventResponse
)
from app.fusion import run_hazard_fusion_for_node

router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────────────────────

HAZARD_TYPE_TO_NODE_TYPE: dict[str, str] = {
    "FIRE":        "fire",
    "AIR_QUALITY": "air_quality",
    "WATER_LEVEL": "water_level",
}


def _event_out(e: HazardEvent) -> HazardEventOut:
    return HazardEventOut(
        id=e.id,
        event_id=e.event_id,
        node_id=e.node_id,
        hazard_type=e.hazard_type,
        risk_score=e.risk_score,
        severity=e.severity,
        confidence=e.confidence,
        sensor_value_1=e.sensor_value_1,
        sensor_value_2=e.sensor_value_2,
        sensor_value_3=e.sensor_value_3,
        rssi=e.rssi,
        snr=e.snr,
        recorded_at=e.recorded_at.isoformat(),
    )


# ── POST /hazard-events ───────────────────────────────────────────────────────

@router.post("/hazard-events", response_model=HazardEventResponse, status_code=201)
async def ingest_hazard_event(
    event: HazardEventIn,
    db: AsyncSession = Depends(get_db),
):
    """
    Receives a parsed VCN1 hazard reading from the gateway bridge.
    - Upserts the Node row (creating it on first contact, using the
      hazard_type to derive node_type).
    - Deduplicates on event_id.
    - Stores the HazardEvent row.
    - Triggers the hazard fusion engine for this node.
    """
    now = datetime.utcnow()
    recorded_at = datetime.fromisoformat(
        event.timestamp.replace("Z", "+00:00")
    ).replace(tzinfo=None)

    # Derive node_type from hazard_type
    node_type = HAZARD_TYPE_TO_NODE_TYPE.get(event.hazard_type, "fire")

    # Upsert node
    node = await db.get(Node, event.node_id)
    if node is None:
        node = Node(
            node_id=event.node_id,
            node_type=node_type,
            lat=event.lat,
            lon=event.lon,
            last_seen=now,
            battery_pct=100,   # hazard nodes don't report battery over VCN1
            status="online",
        )
        db.add(node)
    else:
        node.last_seen = now
        node.status = "online"
        # Update lat/lon if the bridge supplies non-zero values (static install,
        # so this rarely changes, but keeps the row fresh)
        if event.lat != 0.0:
            node.lat = event.lat
        if event.lon != 0.0:
            node.lon = event.lon

    # Deduplicate
    existing = await db.execute(
        select(HazardEvent).where(HazardEvent.event_id == event.event_id)
    )
    if existing.scalars().first():
        return HazardEventResponse(id=0, event_id=event.event_id, status="duplicate")

    db_event = HazardEvent(
        event_id=event.event_id,
        node_id=event.node_id,
        hazard_type=event.hazard_type,
        risk_score=event.risk_score,
        severity=event.severity,
        confidence=event.confidence,
        sensor_value_1=event.sensor_value_1,
        sensor_value_2=event.sensor_value_2,
        sensor_value_3=event.sensor_value_3,
        rssi=event.rssi,
        snr=event.snr,
        recorded_at=recorded_at,
    )
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)

    # Trigger hazard-aware fusion
    await run_hazard_fusion_for_node(db, event.node_id)

    return HazardEventResponse(
        id=db_event.id,
        event_id=event.event_id,
        status="accepted",
    )


# ── GET /hazard-events ────────────────────────────────────────────────────────

@router.get("/hazard-events", response_model=list[HazardEventOut])
async def get_hazard_events(
    limit: int = 50,
    offset: int = 0,
    node_id: Optional[str] = Query(default=None),
    hazard_type: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns recent hazard readings, newest first.
    Optional filter params: node_id, hazard_type.
    """
    q = select(HazardEvent).order_by(HazardEvent.recorded_at.desc())
    if node_id:
        q = q.where(HazardEvent.node_id == node_id)
    if hazard_type:
        q = q.where(HazardEvent.hazard_type == hazard_type.upper())
    q = q.limit(limit).offset(offset)

    result = await db.execute(q)
    events = result.scalars().all()
    return [_event_out(e) for e in events]


# ── GET /hazard-events/{node_id}/history ─────────────────────────────────────

@router.get("/hazard-events/{node_id}/history", response_model=list[HazardEventOut])
async def get_node_hazard_history(
    node_id: str,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """
    Time-series readings for a single hazard node, newest first.
    Used by the frontend trend sparkline / chart.
    """
    result = await db.execute(
        select(HazardEvent)
        .where(HazardEvent.node_id == node_id)
        .order_by(HazardEvent.recorded_at.desc())
        .limit(limit)
    )
    events = result.scalars().all()
    if not events:
        raise HTTPException(status_code=404, detail=f"No hazard events found for node {node_id}")
    return [_event_out(e) for e in events]
