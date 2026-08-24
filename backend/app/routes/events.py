"""
Event ingestion and retrieval endpoints.
POST /events — Gateway posts raw LoRa-payload events here.
GET /events — Dashboard fetches recent raw events.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Node, AcousticEvent, VisionEvent
from app.schemas import EventIn, EventOut, EventResponse
from app.fusion import run_fusion_for_node

router = APIRouter()


@router.post("/events", response_model=EventResponse, status_code=201)
async def ingest_event(event: EventIn, db: AsyncSession = Depends(get_db)):
    """
    Receives a LoRa-payload-shaped event from the gateway.
    Stores it, updates node status, and triggers fusion.
    """
    now = datetime.utcnow()
    # Strip timezone info — DB uses naive timestamps (all assumed UTC)
    recorded_at = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00")).replace(tzinfo=None)

    # Upsert node
    node = await db.get(Node, event.node_id)
    if node is None:
        node = Node(
            node_id=event.node_id,
            node_type=event.sensor_type,
            lat=event.lat,
            lon=event.lon,
            last_seen=now,
            battery_pct=event.battery_pct,
            status="online",
        )
        db.add(node)
    else:
        node.last_seen = now
        node.battery_pct = event.battery_pct
        node.status = "online"
        node.lat = event.lat
        node.lon = event.lon

    # Store event based on sensor type
    if event.sensor_type == "acoustic":
        # Check for duplicate event_id
        existing = await db.execute(
            select(AcousticEvent).where(AcousticEvent.event_id == event.event_id)
        )
        if existing.scalars().first():
            return EventResponse(id=0, event_id=event.event_id, status="duplicate")

        db_event = AcousticEvent(
            event_id=event.event_id,
            node_id=event.node_id,
            event_class=event.event_class,
            confidence=event.confidence,
            lat=event.lat,
            lon=event.lon,
            recorded_at=recorded_at,
        )
        db.add(db_event)
    elif event.sensor_type == "vision":
        existing = await db.execute(
            select(VisionEvent).where(VisionEvent.event_id == event.event_id)
        )
        if existing.scalars().first():
            return EventResponse(id=0, event_id=event.event_id, status="duplicate")

        db_event = VisionEvent(
            event_id=event.event_id,
            node_id=event.node_id,
            event_class=event.event_class,
            confidence=event.confidence,
            lat=event.lat,
            lon=event.lon,
            recorded_at=recorded_at,
        )
        db.add(db_event)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown sensor_type: {event.sensor_type}")

    await db.commit()
    await db.refresh(db_event)

    # Run fusion engine
    await run_fusion_for_node(db, event.node_id)

    return EventResponse(id=db_event.id, event_id=event.event_id, status="accepted")


@router.get("/events", response_model=list[EventOut])
async def get_events(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns recent events (both acoustic and vision) in LoRaEvent shape.
    """
    # Fetch acoustic events
    acoustic_result = await db.execute(
        select(AcousticEvent).order_by(AcousticEvent.recorded_at.desc()).limit(limit).offset(offset)
    )
    acoustic_events = acoustic_result.scalars().all()

    # Fetch vision events
    vision_result = await db.execute(
        select(VisionEvent).order_by(VisionEvent.recorded_at.desc()).limit(limit).offset(offset)
    )
    vision_events = vision_result.scalars().all()

    # Combine and sort by timestamp
    all_events: list[EventOut] = []

    for e in acoustic_events:
        node = await db.get(Node, e.node_id)
        all_events.append(EventOut(
            node_id=e.node_id,
            event_id=e.event_id,
            timestamp=e.recorded_at.isoformat(),
            sensor_type="acoustic",
            event_class=e.event_class,
            confidence=e.confidence,
            battery_pct=node.battery_pct if node else 0,
            lat=e.lat,
            lon=e.lon,
        ))

    for e in vision_events:
        node = await db.get(Node, e.node_id)
        all_events.append(EventOut(
            node_id=e.node_id,
            event_id=e.event_id,
            timestamp=e.recorded_at.isoformat(),
            sensor_type="vision",
            event_class=e.event_class,
            confidence=e.confidence,
            battery_pct=node.battery_pct if node else 0,
            lat=e.lat,
            lon=e.lon,
        ))

    # Sort combined list by timestamp descending
    all_events.sort(key=lambda x: x.timestamp, reverse=True)

    return all_events[:limit]
