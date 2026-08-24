from datetime import datetime
from sqlalchemy import String, Float, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Node(Base):
    __tablename__ = "nodes"

    node_id: Mapped[str] = mapped_column(String, primary_key=True)
    node_type: Mapped[str] = mapped_column(String, default="acoustic")  # 'acoustic' | 'vision'
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    battery_pct: Mapped[int] = mapped_column(Integer, default=100)
    status: Mapped[str] = mapped_column(String, default="online")  # 'online' | 'offline'


class AcousticEvent(Base):
    __tablename__ = "acoustic_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    node_id: Mapped[str] = mapped_column(String, ForeignKey("nodes.node_id"))
    event_class: Mapped[str] = mapped_column(String)  # 'chainsaw', 'vehicle', etc.
    confidence: Mapped[float] = mapped_column(Float)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(DateTime)


class VisionEvent(Base):
    __tablename__ = "vision_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    node_id: Mapped[str] = mapped_column(String, ForeignKey("nodes.node_id"))
    event_class: Mapped[str] = mapped_column(String)  # 'person', 'vehicle'
    confidence: Mapped[float] = mapped_column(Float)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(DateTime)


class Threat(Base):
    __tablename__ = "threats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fused_score: Mapped[float] = mapped_column(Float)
    label: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String)  # 'critical' | 'medium' | 'low'
    acoustic_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    vision_person_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    vision_vehicle_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    acoustic_class: Mapped[str | None] = mapped_column(String, nullable=True)
    node_id: Mapped[str] = mapped_column(String, ForeignKey("nodes.node_id"))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    alert: Mapped["Alert"] = relationship(back_populates="threat", uselist=False)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    threat_id: Mapped[int] = mapped_column(Integer, ForeignKey("threats.id"), unique=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_by: Mapped[str | None] = mapped_column(String, nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    threat: Mapped["Threat"] = relationship(back_populates="alert")
