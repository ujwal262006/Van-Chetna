from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


# --- Incoming LoRa event (POST /events) ---

class EventIn(BaseModel):
    node_id: str
    event_id: str
    timestamp: str  # ISO8601
    sensor_type: str  # 'acoustic' | 'vision'
    event_class: str = Field(alias="class")
    confidence: float
    battery_pct: int
    lat: float
    lon: float

    model_config = {"populate_by_name": True}


# --- Response shapes matching frontend types exactly ---

class EventOut(BaseModel):
    node_id: str
    event_id: str
    timestamp: str
    sensor_type: str
    # Frontend expects "class" as the JSON key
    event_class: str = Field(serialization_alias="class")
    confidence: float
    battery_pct: int
    lat: float
    lon: float

    model_config = {"populate_by_name": True, "by_alias": True}


class AlertOut(BaseModel):
    id: int
    fused_score: float
    label: str
    severity: str
    acoustic_confidence: float
    vision_person_confidence: float
    vision_vehicle_confidence: float
    acoustic_class: Optional[str]
    node_id: str
    generated_at: str
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None


class NodeStatusOut(BaseModel):
    node_id: str
    last_seen: str
    battery_pct: int
    status: str
    lat: Optional[float] = None
    lon: Optional[float] = None


class AcknowledgeIn(BaseModel):
    acknowledged_by: str


class EventResponse(BaseModel):
    id: int
    event_id: str
    status: str = "accepted"
