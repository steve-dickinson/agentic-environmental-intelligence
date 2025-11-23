---
layout: default
title: Architecture
---

**Navigation**: [Home](index.md) | [Changelog](changelog.md) | [Architecture](architecture.md) | [GitHub](https://github.com/steve-dickinson/agentic-environmental-intelligence)

# System Architecture

> **⚠️ Note**: This is a proof of concept and personal project, not a production system. The architecture described here is for educational and demonstration purposes.

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│              Scheduled Agentic Workflow (LangGraph)          │
│  ┌────────┐    ┌──────────┐    ┌─────────────┐             │
│  │ Agent  │───▶│  Tools   │───▶│  Analysis   │             │
│  │  LLM   │    │ (MCP)    │    │  Pipeline   │             │
│  └────────┘    └──────────┘    └─────────────┘             │
│         │                │                    │              │
│         │   Every 2 Hours (Docker Scheduler)  │              │
└─────────────────────────────────────────────────────────────┘
         │                │                    │
         ▼                ▼                    ▼
┌─────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   OpenAI    │  │  EA Data APIs    │  │ Triple Storage   │
│   GPT-4     │  ├──────────────────┤  ├──────────────────┤
└─────────────┘  │ Flood Monitoring │  │ MongoDB          │
                 │   Hydrology      │  │ (Incidents +     │
                 │   Rainfall       │  │  Agent Logs)     │
                 │ Public Registers │  │                  │
                 └──────────────────┘  │ PostgreSQL       │
                                       │ (pgvector RAG)   │
                                       │                  │
                                       │ Neo4j            │
                                       │ (Knowledge Graph)│
                                       └──────────────────┘
                                                │
                                                ▼
                                       ┌──────────────────┐
                                       │ Streamlit        │
                                       │ 3-Page Dashboard │
                                       ├──────────────────┤
                                       │ 1. Incidents     │
                                       │ 2. Agent Runs    │
                                       │ 3. RAG vs Graph  │
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
├─ incident_id (UUID, indexed)
├─ content_hash (SHA-256, indexed) ← NEW: Duplicate detection
├─ created_at (datetime)
├─ readings (array)
│   └─ {station_id, value, timestamp, source, coordinates}
├─ alerts (array)
│   └─ {summary, priority, suggested_actions}
└─ permits (array)
    └─ {permit_id, operator, type, distance}

agent_run_logs ← NEW: Execution tracking
├─ _id (ObjectId)
├─ run_id (UUID, unique index)
├─ timestamp (datetime, descending index)
├─ duration_seconds (float)
├─ stations_fetched (int)
├─ readings_fetched (int)
├─ flood_warnings_fetched (int)
├─ clusters_found (int)
├─ cluster_details (array)
│   └─ {type, station_count, station_ids, center_lat, center_lon}
├─ rag_searches_performed (int)
├─ rag_results (array)
│   └─ {similar_incidents_found, avg_similarity, best_similarity}
├─ incidents_created (int, indexed)
├─ incidents_duplicate (int)
├─ incident_ids_created (array)
├─ incident_ids_duplicate (array)
├─ mongodb_stored (int)
├─ pgvector_stored (int)
├─ neo4j_stored (int)
├─ errors (array)
└─ openai_api_calls (int)

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
├─ id (UUID, primary key)
├─ run_id (UUID) ← NEW: Track which run created this
├─ embedding (vector(1536))
├─ summary_text (text)
├─ created_at (timestamp)
└─ UNIQUE CONSTRAINT (id) ← NEW: Prevent duplicates

Indexes:
├─ id (unique, for duplicate detection)
└─ embedding (HNSW for cosine similarity search)

Purpose: RAG semantic search and similarity analysis
```

### Neo4j Graph Database ← NEW
```
Nodes:
├─ Incident
│   └─ Properties: incident_id, summary, priority, timestamp
├─ Station
│   └─ Properties: station_id, label, lat, lon, source
├─ Permit
│   └─ Properties: permit_id, operator, type, distance
└─ Location
    └─ Properties: name, lat, lon

Relationships:
├─ (Incident)-[:MEASURED_AT]->(Station)
├─ (Incident)-[:NEAR_PERMIT]->(Permit)
├─ (Station)-[:IN_CATCHMENT]->(Location)
└─ (Incident)-[:SIMILAR_TO]->(Incident)

Current Stats: 77 nodes, 72 relationships
Purpose: Causal reasoning and multi-hop queries
```

### Storage Flow with Duplicate Detection

```
New Incident Generated
        │
        ▼
    MongoDB Check
    ├─ Generate content_hash (SHA-256)
    ├─ Query: existing incident with same hash?
    ├─ Within 24h window?
    │
    ├─ YES: Return existing incident (skip storage)
    │         Log: "ℹ️ Duplicate incident detected"
    │
    └─ NO: Continue to storage
        │
        ▼
    PostgreSQL Check
    ├─ Query: embeddings exist for incident_id?
    │
    ├─ YES: Skip embedding generation
    │         (Saves OpenAI API call)
    │
    └─ NO: Generate embedding
        │   Store to pgvector
        │
        ▼
    Neo4j Check
    ├─ Query: node exists for incident_id?
    │
    ├─ YES: Skip graph creation
    │
    └─ NO: Create incident node
            Create station relationships
            Link to permits
            
Result: Idempotent storage across all 3 databases
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
Development & Production (Docker Compose)
  │
  ├─ Core Infrastructure
  │   ├─ MongoDB (port 27017)
  │   │   ├─ incidents collection
  │   │   ├─ agent_run_logs collection
  │   │   └─ station_metadata collection
  │   │
  │   ├─ PostgreSQL (port 5432)
  │   │   ├─ pgvector extension
  │   │   └─ incident_embeddings table
  │   │
  │   ├─ Neo4j (port 7474, 7687)
  │   │   ├─ Incident nodes
  │   │   ├─ Station nodes
  │   │   └─ Relationships
  │   │
  │   └─ pgAdmin (port 5050)
  │
  ├─ Scheduled Agent Execution ← NEW
  │   ├─ Docker service: agent
  │   ├─ Command: infinite loop with 7200s sleep
  │   ├─ Restart policy: unless-stopped
  │   ├─ Environment: RUN_INTERVAL_HOURS=2
  │   └─ Runs: Every 2 hours continuously
  │
  ├─ Python Environment (uv)
  │   ├─ Dependencies via pyproject.toml
  │   └─ UV package manager
  │
  ├─ Execution Scripts
  │   ├─ scripts/run_agent.py (single run)
  │   ├─ scripts/view_run_logs.py (statistics)
  │   └─ scripts/sync_stations.py (metadata)
  │
  └─ Streamlit Dashboard (port 8501)
      ├─ Page 1: Incident Dashboard
      ├─ Page 2: Agent Runs (analytics)
      └─ Page 3: RAG vs Knowledge Graph

Scheduled Execution Flow
  │
  ▼
[Agent Container Starts]
  │
  └─ while true; do
      │
      ├─ Generate unique run_id (UUID)
      ├─ Track start timestamp
      │
      ├─ Execute: uv run python scripts/run_agent.py
      │   │
      │   ├─ Fetch data from EA APIs
      │   ├─ Detect anomalies
      │   ├─ Cluster spatially
      │   ├─ Search permits
      │   ├─ Correlate rainfall
      │   ├─ Generate incidents
      │   ├─ RAG enrichment
      │   ├─ Store to 3 databases (with duplicate detection)
      │   └─ Build AgentRunLog
      │
      ├─ Save run log to MongoDB
      │   └─ agent_run_logs collection
      │
      ├─ Print summary:
      │   ⏱️ Duration: 145.3s
      │   📊 Readings: 8,247
      │   🗺️ Clusters: 3
      │   📝 Incidents: 5 (2 new, 3 duplicate)
      │   🔍 RAG: 2 searches (88% avg similarity)
      │
      ├─ sleep 7200 (2 hours)
      │
      └─ [Loop repeats]

Monitoring Commands
  │
  ├─ docker-compose logs -f agent
  │   └─ Real-time execution monitoring
  │
  ├─ uv run python scripts/view_run_logs.py
  │   └─ Aggregate statistics (7-day default)
  │
  └─ uv run streamlit run streamlit_app.py
      └─ Interactive dashboard with Agent Runs page
```

### Production Considerations (Future)

```
Current: Single Docker Host
  │
Future: Cloud Infrastructure
  │
  ├─ Managed Databases
  │   ├─ MongoDB Atlas (incidents + logs)
  │   ├─ Cloud SQL PostgreSQL (pgvector)
  │   └─ Neo4j Aura (knowledge graph)
  │
  ├─ Container Orchestration
  │   ├─ Kubernetes for agent scheduling
  │   ├─ Horizontal scaling for parallel processing
  │   └─ Service mesh for reliability
  │
  ├─ Observability
  │   ├─ Prometheus metrics
  │   ├─ Grafana dashboards
  │   └─ Structured logging (ELK stack)
  │
  └─ API Gateway
      ├─ REST API for external access
      ├─ Webhook alerts to stakeholders
      └─ Authentication/authorization
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
