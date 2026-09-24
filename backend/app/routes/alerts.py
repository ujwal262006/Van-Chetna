"""
Alert endpoints.
GET /alerts — Dashboard fetches fused/scored alerts.
POST /alerts/{id}/acknowledge — Officer acknowledges an alert.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.models import Alert, Threat
from app.schemas import AlertOut, AcknowledgeIn

router = APIRouter()


@router.get("/alerts", response_model=list[AlertOut])
async def get_alerts(
    limit: int = 100,
    offset: int = 0,
    node_id: Optional[str] = Query(default=None, description="Filter by node ID"),
    severity: Optional[str] = Query(default=None, description="Filter by severity: critical|medium|low"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns alerts joined with their threats, newest first.
    Optional filters: node_id, severity.
    Default limit raised to 100 so hazard alerts aren't hidden behind
    a wall of acoustic alerts.
    """
    q = (
        select(Alert, Threat)
        .join(Threat, Alert.threat_id == Threat.id)
        .order_by(Threat.created_at.desc())
    )
    if node_id:
        q = q.where(Threat.node_id == node_id)
    if severity:
        q = q.where(Threat.severity == severity.lower())
    q = q.limit(limit).offset(offset)

    result = await db.execute(q)
    rows = result.all()

    alerts_out = []
    for alert, threat in rows:
        alerts_out.append(AlertOut(
            id=alert.id,
            fused_score=threat.fused_score,
            label=threat.label,
            severity=threat.severity,
            acoustic_confidence=threat.acoustic_confidence,
            vision_person_confidence=threat.vision_person_confidence,
            vision_vehicle_confidence=threat.vision_vehicle_confidence,
            acoustic_class=threat.acoustic_class,
            node_id=threat.node_id,
            generated_at=threat.created_at.isoformat(),
            acknowledged=alert.acknowledged,
            acknowledged_by=alert.acknowledged_by,
        ))

    return alerts_out


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    body: AcknowledgeIn,
    db: AsyncSession = Depends(get_db),
):
    """
    Marks an alert as acknowledged by an officer.
    """
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.acknowledged = True
    alert.acknowledged_by = body.acknowledged_by
    alert.acknowledged_at = datetime.utcnow()

    await db.commit()
    return {"status": "acknowledged", "id": alert_id}
