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
    node_type: str   # 'acoustic'|'vision'|'fire'|'air_quality'|'water_level'
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


# ── New: VCN1 hazard-event schemas ──────────────────────────────────────────

class HazardEventIn(BaseModel):
    """
    Incoming VCN1-protocol hazard reading (POST /hazard-events).
    Populated by the vcn1_gateway_bridge.py serial reader.
    """
    node_id: str
    event_id: str
    timestamp: str          # ISO8601 — bridge generates this from wall clock
    hazard_type: str        # 'FIRE' | 'AIR_QUALITY' | 'WATER_LEVEL'
    risk_score: int         # 0–100
    severity: str           # 'normal'|'watch'|'warning'|'critical' (lowercased by bridge)
    confidence: int         # 0–100
    sensor_value_1: Optional[float] = None
    sensor_value_2: Optional[float] = None
    sensor_value_3: Optional[float] = None
    rssi: Optional[int] = None
    snr: Optional[float] = None
    lat: float = 0.0
    lon: float = 0.0


class HazardEventOut(BaseModel):
    """
    Single hazard reading returned by GET /hazard-events and GET /nodes/{id}/hazard-events.
    """
    id: int
    event_id: str
    node_id: str
    hazard_type: str
    risk_score: int
    severity: str
    confidence: int
    sensor_value_1: Optional[float]
    sensor_value_2: Optional[float]
    sensor_value_3: Optional[float]
    rssi: Optional[int]
    snr: Optional[float]
    recorded_at: str        # ISO string


class HazardEventResponse(BaseModel):
    id: int
    event_id: str
    status: str = "accepted"


class NodeCurrentStatus(BaseModel):
    """
    Extended per-node snapshot combining NodeStatusOut with the latest
    hazard reading (if the node is a hazard-type node).
    """
    node_id: str
    node_type: str
    last_seen: str
    battery_pct: int
    status: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    # Latest hazard reading — None for acoustic/vision nodes
    latest_hazard: Optional[HazardEventOut] = None


class MultiNodeSummary(BaseModel):
    """
    Top-level payload for GET /nodes/summary — one entry per registered node
    with its current status and latest hazard reading (if applicable).
    """
    nodes: list[NodeCurrentStatus]
    total_online: int
    total_offline: int
