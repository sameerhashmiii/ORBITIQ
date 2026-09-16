"""SQLAlchemy models. Normalized tables (no giant JSON blob state)."""
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Cell(Base):
    __tablename__ = "cells"
    cell_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mcc: Mapped[int] = mapped_column(Integer, default=310)
    mnc: Mapped[int] = mapped_column(Integer, default=260)
    tac: Mapped[int] = mapped_column(Integer, default=0)
    radio: Mapped[str] = mapped_column(String(16), default="LTE")
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    range_m: Mapped[int] = mapped_column(Integer, default=1000)
    samples: Mapped[int] = mapped_column(Integer, default=10)


class Satellite(Base):
    __tablename__ = "satellites"
    sat_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    tle_line1: Mapped[str] = mapped_column(String(256), default="")
    tle_line2: Mapped[str] = mapped_column(String(256), default="")


class Device(Base):
    __tablename__ = "devices"
    device_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    mobility_profile: Mapped[str] = mapped_column(String(32), default="urban")


class Telemetry(Base):
    __tablename__ = "telemetry"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.device_id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    rsrp_dbm: Mapped[float] = mapped_column(Float, default=-100)
    sinr_db: Mapped[float] = mapped_column(Float, default=5)
    latency_ms: Mapped[float] = mapped_column(Float, default=45)
    packet_loss_pct: Mapped[float] = mapped_column(Float, default=0.5)
    throughput_mbps: Mapped[float] = mapped_column(Float, default=25)


class Event(Base):
    __tablename__ = "events"
    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    type: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(16))
    lat: Mapped[float] = mapped_column(Float, default=0)
    lon: Mapped[float] = mapped_column(Float, default=0)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)


class Prediction(Base):
    __tablename__ = "predictions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64), default="")
    probability: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    horizon_min: Mapped[int] = mapped_column(Integer, default=5)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Recommendation(Base):
    __tablename__ = "recommendations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(64))
    recommended_sat: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[float] = mapped_column(Float)
    explanation: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SimulationRun(Base):
    __tablename__ = "simulation_runs"
    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    seed: Mapped[int] = mapped_column(Integer, default=42)
    n_devices: Mapped[int] = mapped_column(Integer, default=0)
    scenario: Mapped[str] = mapped_column(String(128), default="baseline")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)


class DataSource(Base):
    __tablename__ = "data_sources"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    source: Mapped[str] = mapped_column(String(256), default="")
    type: Mapped[str] = mapped_column(String(64), default="real")
    license: Mapped[str] = mapped_column(String(128), default="")
    classification: Mapped[str] = mapped_column(String(32), default="REAL")
