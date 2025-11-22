---
layout: default
title: Architecture
---

# System Architecture

> **⚠️ Note**: This is a proof of concept and personal project, not a production system. The architecture described here is for educational and demonstration purposes.

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Agentic Workflow (LangGraph)              │
│  ┌────────┐    ┌──────────┐    ┌─────────────┐             │
│  │ Agent  │───▶│  Tools   │───▶│  Analysis   │             │
│  │  LLM   │    │ (MCP)    │    │  Pipeline   │             │
│  └────────┘    └──────────┘    └─────────────┘             │
└─────────────────────────────────────────────────────────────┘
         │                │                    │
         ▼                ▼                    ▼
┌─────────────┐  ┌──────────────────┐  ┌──────────────┐
│   OpenAI    │  │  EA Data APIs    │  │   Storage    │
│   GPT-4     │  ├──────────────────┤  ├──────────────┤
└─────────────┘  │ Flood Monitoring │  │   MongoDB    │
                 │   Hydrology      │  │  PostgreSQL  │
                 │   Rainfall       │  │  (pgvector)  │
                 │ Public Registers │  └──────────────┘
                 └──────────────────┘
```

## Agent Decision Flow

```
START
  │
  ▼
┌───────────────────────┐
│  Initialize Mission   │
│  - Set system prompt  │
│  - Define workflow    │
└───────────────────────┘
  │
  ▼
┌───────────────────────┐
│   Agent Thinking      │◀──────────┐
│   (LLM Decision)      │           │
└───────────────────────┘           │
  │                                 │
  ├─ Tool Call? ──Yes──▶ Execute Tools
  │                      (Flood/Hydro/Rainfall/Permits)
  │                                 │
  ├─ Has Data? ──Yes──▶ Detect Anomalies
  │                      - Threshold check
  │                      - Temporal filter
  │                      - Spatial clustering
  │                                 │
  ├─ Anomalies? ─Yes──▶ Generate Incidents
  │                      - Per-cluster analysis
  │                      - Rainfall correlation
  │                      - Permit enrichment
  │                      - Context-aware summaries
  │                                 │
  └─ Complete ──────────────────────┘
  │
  ▼
END
```

## Data Processing Pipeline

### 1. Collection Phase
```
API Calls (Parallel)
├─ Flood Monitoring API → 761 stations
├─ Hydrology API        → 1,000 stations
└─ Rainfall API         → 383 stations
                            │
                            ▼
                  Coordinate Enrichment
                  (MongoDB Station Repo)
                            │
                            ▼
                  Standardized Readings
                  {station_id, value, timestamp,
                   source, lat, lon, easting, northing}
```

### 2. Detection Phase
```
All Readings (9,000+)
        │
        ▼
Threshold Filter (configurable)
        │
        ▼
Anomalies (100-200)
        │
        ▼
Temporal Filter (24h)
        │
        ▼
Recent Anomalies (50-100)
        │
        ▼
Spatial Clustering (10km)
        │
        ▼
Incident Clusters (3-7)
```

### 3. Enrichment Phase
```
For Each Cluster:
  │
  ├─ Calculate Center Point
  │   (average lat/lon)
  │
  ├─ Search Permits (1km radius)
  │   - Discharge consents
  │   - Waste operations
  │   - Flood risk activities
  │
  ├─ Check Rainfall (10km, 24h)
  │   - Total precipitation
  │   - Max reading
  │   - Station count
  │
  └─ Generate Alert Summary
      - Priority classification
      - Data-driven content
      - Source-aware language
      - Actionable recommendations
```

## Storage Architecture

### MongoDB Collections
```
incidents
├─ _id (ObjectId)
├─ created_at (datetime)
├─ readings (array)
│   └─ {station_id, value, timestamp, source, coordinates}
├─ alerts (array)
│   └─ {summary, priority, suggested_actions}
└─ permits (array)
    └─ {permit_id, operator, type, distance}

station_metadata
├─ _id (composite: "source:station_id")
├─ source (flood|hydrology|rainfall)
├─ station_id (string)
├─ lat, lon (WGS84)
├─ easting, northing (British National Grid)
├─ label (string)
└─ last_seen (datetime)
```

### PostgreSQL (pgvector)
```
incident_embeddings
├─ incident_id (UUID, FK to MongoDB)
├─ embedding (vector(1536))
├─ summary_text (text)
└─ created_at (timestamp)

Purpose: Semantic search and similarity analysis
```

## MCP Tools Pattern

```python
@tool
async def get_flood_readings(parameter: str) -> dict:
    """Fetch latest flood monitoring data."""
    client = FloodClient()
    readings = await client.get_latest_readings(parameter)
    return {"readings": [...], "count": len(readings)}
```

**Available Tools:**
- `get_flood_readings` - River levels, flow rates
- `get_hydrology_readings` - Groundwater, water quality
- `get_rainfall_readings` - Precipitation data
- `search_public_registers` - Environmental permits

## Client Architecture

```
BaseClient Pattern
├─ FloodClient
│   ├─ get_latest_readings()
│   └─ _enrich_coordinates()
│
├─ HydrologyClient
│   ├─ get_latest_readings()
│   └─ _enrich_coordinates()
│
├─ RainfallClient
│   ├─ get_latest_readings()
│   ├─ get_rainfall_near_location()
│   ├─ calculate_total_rainfall()
│   └─ _enrich_coordinates()
│
└─ PublicRegistersClient
    ├─ search_by_coordinates()
    └─ search_by_postcode()
```

## Coordinate Enrichment Strategy

```
Reading from API (minimal data)
  │
  ▼
Extract station_id
  │
  ▼
Query MongoDB station_metadata
  ├─ Try source-specific lookup
  ├─ Fallback to alternate sources
  └─ Use cached metadata
  │
  ▼
Enrich Reading Object
  {
    station_id: "3400TH",
    value: 4.55,
    timestamp: "2025-11-22T00:00:00Z",
    source: "flood",
    easting: 361234,      ← Added
    northing: 175890,     ← Added
    lat: 51.4195,         ← Added
    lon: -0.3087          ← Added
  }
```

## Clustering Algorithm

```python
def cluster_anomalies_spatially(
    readings, 
    max_distance_km=10.0,
    min_cluster_size=2
):
    """DBSCAN-like spatial clustering."""
    
    clusters = []
    used = set()
    
    for reading in readings:
        if reading in used:
            continue
            
        cluster = [reading]
        used.add(reading)
        
        # Find nearby readings
        for other in readings:
            if other in used:
                continue
            
            distance = haversine(
                reading.lat, reading.lon,
                other.lat, other.lon
            )
            
            if distance <= max_distance_km:
                cluster.append(other)
                used.add(other)
        
        if len(cluster) >= min_cluster_size:
            clusters.append(cluster)
    
    return clusters
```

## Alert Generation Strategy

```
Cluster Analysis
  │
  ├─ Determine source(s): flood, hydrology, or mixed
  │
  ├─ Calculate statistics
  │   ├─ Max value
  │   ├─ Average value
  │   └─ Station count
  │
  ├─ Check rainfall (if flood cluster)
  │   └─ Categorize: heavy/moderate/light/none
  │
  ├─ Analyze permits
  │   ├─ Count by type
  │   └─ Categorize activities
  │
  └─ Generate summary
      ├─ Source-specific language
      ├─ Data-driven details
      ├─ Rainfall context (if applicable)
      ├─ Permit information
      └─ Actionable recommendations
```

## Deployment Architecture

```
Development
  │
  ├─ Docker Compose
  │   ├─ MongoDB (port 27017)
  │   ├─ PostgreSQL (port 5432)
  │   └─ pgAdmin (port 5050)
  │
  ├─ Python Virtual Env (uv)
  │   └─ Dependencies
  │
  └─ Local Execution
      ├─ Agent scripts
      └─ Streamlit dashboard

Production (Future)
  │
  ├─ Cloud Infrastructure
  │   ├─ MongoDB Atlas
  │   ├─ Cloud SQL (PostgreSQL)
  │   └─ Container hosting
  │
  ├─ Scheduled Jobs
  │   └─ Periodic monitoring cycles
  │
  └─ API Gateway
      ├─ REST API
      └─ Webhook alerts
```

## Performance Optimizations

### 1. Batch Database Queries
```python
# Bad: N queries
for station_id in station_ids:
    metadata = repo.get_station(source, station_id)

# Good: 1 query
metadata_map = repo.bulk_get_stations(source, station_ids)
```

### 2. Parallel Tool Execution
```python
# LangGraph automatically parallelizes independent tool calls
response = await agent.invoke({"messages": [message]})
# Flood + Hydro + Rainfall called simultaneously
```

### 3. Smart Caching
```python
class RainfallClient:
    def __init__(self):
        self._metadata_cache = {}  # Avoid re-fetching
```

### 4. Message Reduction
```python
def reduce_messages(left, right):
    """Trim large ToolMessage content to summaries."""
    # Prevents token bloat in agent context
```

---

[Back to Home](index.md)
