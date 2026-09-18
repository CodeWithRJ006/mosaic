from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Hub(Base):
    __tablename__ = "hubs"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    operating_start = Column(String, default="00:00")
    operating_end = Column(String, default="23:59")
    transfer_capacity = Column(Integer, default=100)
    status = Column(String, default="OPEN")

class Vehicle(Base):
    __tablename__ = "vehicles"
    
    id = Column(String, primary_key=True)
    max_weight = Column(Float, nullable=False)
    max_volume = Column(Float, nullable=False)
    current_location = Column(String, nullable=False)
    schedule = Column(JSON, nullable=False)
    shift_start = Column(DateTime, nullable=False)
    shift_end = Column(DateTime, nullable=False)

class Shipment(Base):
    __tablename__ = "shipments"
    
    id = Column(String, primary_key=True)
    weight = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    sla_deadline = Column(DateTime, nullable=False)
    current_location = Column(String, nullable=False)
    planned_route = Column(JSON, nullable=False)
    status = Column(String, nullable=False)

class Event(Base):
    __tablename__ = "events"
    
    id = Column(String, primary_key=True)
    type = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    payload = Column(JSON, nullable=False)
    state_version = Column(Integer, nullable=False)

class RecoveryPlan(Base):
    __tablename__ = "recovery_plans"
    
    plan_id = Column(String, primary_key=True)
    incident_id = Column(String, nullable=False)
    state_version = Column(Integer, nullable=False)
    incident_version = Column(Integer, nullable=False)
    strategy = Column(String, nullable=False)
    status = Column(String, nullable=False)
    
    vehicles = Column(JSON, nullable=False)
    transfers = Column(JSON, nullable=False)
    
    eta = Column(DateTime, nullable=False)
    incremental_cost = Column(Float, nullable=False)
    extra_distance = Column(Float, nullable=False)
    sla_margin_minutes = Column(Float, nullable=False)
    
    constraint_checks = Column(JSON, nullable=False)
    rejection_reasons = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False)
