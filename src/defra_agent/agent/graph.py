from collections.abc import Mapping
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from defra_agent.domain.models import Incident
from defra_agent.services.incident_service import IncidentService
from defra_agent.services.summariser import AlertSummariser
from defra_agent.storage.mongo_repo import IncidentRepository
from defra_agent.storage.pgvector_repo import IncidentVectorRepository
from defra_agent.tools.flood_client import FloodClient
from defra_agent.tools.hydrology_client import HydrologyClient


class GraphState(TypedDict):
    """Simple state mapping to hold the incident for this run."""

    incident: Incident | None


def build_incident_service() -> IncidentService:
    flood_client = FloodClient()
    hydrology_client = HydrologyClient()
    summariser = AlertSummariser()
    incident_repo = IncidentRepository()
    vector_repo = IncidentVectorRepository()
    return IncidentService(
        flood_client=flood_client,
        hydrology_client=hydrology_client,
        summariser=summariser,
        incident_repo=incident_repo,
        vector_repo=vector_repo,
    )


def init_state(_: Mapping[str, Any]) -> GraphState:
    return GraphState(incident=None)


async def run_cycle(state: GraphState) -> GraphState:
    service = build_incident_service()
    incident = await service.run_detection_cycle()
    state["incident"] = incident
    return state


def build_graph() -> Any:
    """Build and compile the LangGraph state graph."""
    graph = StateGraph(GraphState)
    graph.add_node("init", init_state)
    graph.add_node("run_cycle", run_cycle)
    graph.add_edge(START, "init")
    graph.add_edge("init", "run_cycle")
    graph.add_edge("run_cycle", END)
    return graph.compile()
