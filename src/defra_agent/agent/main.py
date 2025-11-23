import asyncio
import uuid
from datetime import datetime
from time import time

from defra_agent.agent.graph import build_graph
from defra_agent.domain.models import AgentRunLog, ClusterInfo, RAGSearchResult
from defra_agent.storage.run_log_repo import RunLogRepository


async def run_once_async() -> None:
    """Execute a single agent run with comprehensive logging."""
    run_id = str(uuid.uuid4())
    start_time = time()
    timestamp = datetime.now()
    
    print(f"\n🚀 Agent Run ID: {run_id}")
    print(f"   Timestamp: {timestamp.isoformat()}")
    
    graph = build_graph()
    result = await graph.ainvoke({})
    
    duration = time() - start_time
    
    # Extract metrics from final state
    flood_readings = len(result.get("flood_readings", []))
    hydrology_readings = len(result.get("hydrology_readings", []))
    
    clusters = result.get("clusters", [])
    cluster_details = []
    for cluster in clusters:
        # Calculate cluster center
        lats = [r.lat for r in cluster if r.lat]
        lons = [r.lon for r in cluster if r.lon]
        
        cluster_details.append(
            ClusterInfo(
                type="spatial",  # All clusters are spatial after anomaly detection
                station_count=len(cluster),
                station_ids=[r.station_id for r in cluster][:10],  # First 10
                center_lat=sum(lats) / len(lats) if lats else None,
                center_lon=sum(lons) / len(lons) if lons else None,
            )
        )
    
    # RAG search results (simplified - could enhance with per-incident tracking)
    similar_incidents = result.get("similar_incidents", [])
    rag_results = []
    if similar_incidents:
        similarities = [s.similarity for s in similar_incidents]
        rag_results.append(
            RAGSearchResult(
                similar_incidents_found=len(similar_incidents),
                avg_similarity=sum(similarities) / len(similarities) if similarities else None,
                best_similarity=max(similarities) if similarities else None,
                similar_incident_ids=[s.incident_id for s in similar_incidents],
            )
        )
    
    incidents = result.get("incidents", [])
    
    # Track created vs duplicate (need to check logs or implement tracking)
    # For now, assume all are created (duplicate detection logs aren't captured yet)
    incident_ids_created = [inc.id for inc in incidents]
    
    # Build run log
    run_log = AgentRunLog(
        run_id=run_id,
        timestamp=timestamp,
        stations_fetched=flood_readings + hydrology_readings,  # Approximate
        readings_fetched=flood_readings + hydrology_readings,
        flood_warnings_fetched=0,  # Not tracked yet
        clusters_found=len(clusters),
        cluster_details=cluster_details,
        rag_searches_performed=1 if similar_incidents else 0,
        rag_results=rag_results,
        incidents_created=len(incidents),
        incidents_duplicate=0,  # Will need to track this
        incident_ids_created=incident_ids_created,
        incident_ids_duplicate=[],
        mongodb_stored=len(incidents),
        pgvector_stored=len(incidents),
        neo4j_stored=len(incidents),  # Assume success if no errors
        duration_seconds=round(duration, 2),
        errors=None,
    )
    
    # Save to MongoDB
    log_repo = RunLogRepository()
    log_repo.save_run_log(run_log)
    log_repo.close()
    
    print(f"\n📊 Run Summary:")
    print(f"   Duration: {duration:.2f}s")
    print(f"   Readings: {run_log.readings_fetched}")
    print(f"   Clusters: {run_log.clusters_found}")
    print(f"   Incidents: {run_log.incidents_created}")
    print(f"   RAG Searches: {run_log.rag_searches_performed}")
    print(f"   ✅ Run log saved to database")


def run_once() -> None:
    """Entry point wrapper for the script command."""
    asyncio.run(run_once_async())


if __name__ == "__main__":
    run_once()
