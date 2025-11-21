from dataclasses import dataclass
from datetime import datetime
from enum import Enum


@dataclass
class Reading:
    station_id: str
    value: float
    timestamp: datetime
    source: str | None = None


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
    activity: str | None = None
    location: str | None = None
    easting: float | None = None
    northing: float | None = None


@dataclass
class Incident:
    id: str
    readings: list[Reading]
    alerts: list[Alert]
    permits: list[Permit] | None = None
