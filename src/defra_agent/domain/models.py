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


@dataclass
class ClusterInfo:
    """Information about a spatial or anomaly cluster."""
    type: str  # "spatial" or "anomaly"
    station_count: int
    station_ids: list[str]
    center_lat: float | None = None
    center_lon: float | None = None


@dataclass
class RAGSearchResult:
    """Results from RAG similarity search."""
    similar_incidents_found: int
    avg_similarity: float | None = None
    best_similarity: float | None = None
    similar_incident_ids: list[str] | None = None


@dataclass
class AgentRunLog:
    """Complete log of an agent execution run."""
    run_id: str
    timestamp: datetime
    
    # Data collection phase
    stations_fetched: int
    readings_fetched: int
    flood_warnings_fetched: int
    
    # Clustering phase
    clusters_found: int
    cluster_details: list[ClusterInfo]
    
    # RAG enrichment phase
    rag_searches_performed: int
    rag_results: list[RAGSearchResult]
    
    # Incident creation phase
    incidents_created: int
    incidents_duplicate: int
    incident_ids_created: list[str]
    incident_ids_duplicate: list[str]
    
    # Storage phase
    mongodb_stored: int
    pgvector_stored: int
    neo4j_stored: int
    
    # Performance metrics
    duration_seconds: float
    errors: list[str] | None = None
    
    # Optional metadata
    openai_api_calls: int | None = None
