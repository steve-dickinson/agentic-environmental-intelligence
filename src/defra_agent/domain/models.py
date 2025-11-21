from dataclasses import dataclass
from datetime import datetime
from enum import Enum


@dataclass
class Reading:
    station_id: str
    value: float
    timestamp: datetime
    source: str | None = None
    easting: int | None = None
    northing: int | None = None
    lat: float | None = None
    lon: float | None = None


class AlertPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Alert:
    summary: str
    priority: AlertPriority
    suggested_actions: list[str]


@dataclass
class Permit:
    permit_id: str
    operator_name: str
    register_label: str | None = None
    registration_type: str | None = None
    site_address: str | None = None
    site_postcode: str | None = None
    distance_km: float | None = None

@dataclass
class Incident:
    id: str
    readings: list[Reading]
    alerts: list[Alert]
    permits: list[Permit] | None = None
