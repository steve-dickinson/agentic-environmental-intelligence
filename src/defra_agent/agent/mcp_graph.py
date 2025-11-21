"""Enhanced agent graph with MCP tool integration."""

from collections.abc import Mapping
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from defra_agent.domain.models import Incident
from defra_agent.services.incident_service import IncidentService
from defra_agent.services.summariser import AlertSummariser
from defra_agent.storage.mongo_repo import IncidentRepository
from defra_agent.storage.pgvector_repo import IncidentVectorRepository
from defra_agent.tools.flood_client import FloodClient
from defra_agent.tools.hydrology_client import HydrologyClient
from defra_agent.tools.mcp_tools import (
    get_flood_readings,
    get_hydrology_readings,
    search_public_registers,
)
from defra_agent.tools.public_registers_client import PublicRegistersClient


class MCPGraphState(dict):
    """State for MCP-enhanced agent graph."""

    incident: Incident | None
    messages: list[dict[str, Any]]
    next_action: str


# Define the tools available to the agent
mcp_tools = [
    get_flood_readings,
    get_hydrology_readings,
    search_public_registers,
]


def build_incident_service() -> IncidentService:
    """Build the incident detection service."""
    flood_client = FloodClient()
    hydrology_client = HydrologyClient()
    public_registers_client = PublicRegistersClient()
    summariser = AlertSummariser()
    incident_repo = IncidentRepository()
    vector_repo = IncidentVectorRepository()

    return IncidentService(
        flood_client=flood_client,
        hydrology_client=hydrology_client,
        public_registers_client=public_registers_client,
        summariser=summariser,
        incident_repo=incident_repo,
        vector_repo=vector_repo,
    )


def init_state(_: Mapping[str, Any]) -> MCPGraphState:
    """Initialize the agent state."""
    return MCPGraphState(
        incident=None,
        messages=[],
        next_action="run_cycle",
    )


async def run_cycle(state: MCPGraphState) -> MCPGraphState:
    """Run the standard detection cycle."""
    service = build_incident_service()
    incident = await service.run_detection_cycle()
    state["incident"] = incident
    state["next_action"] = "end"
    return state


def route_after_cycle(
    state: MCPGraphState,
) -> Literal["tools", "__end__"]:
    """Route based on whether tools are needed."""
    # For now, just end after cycle
    # In future, could route to tools for additional analysis
    return END


def build_mcp_graph() -> Any:
    """Build the agent graph with MCP tool integration.

    This graph demonstrates how MCP tools can be integrated alongside
    the existing detection cycle. The tools are available for the agent
    to call when needed for additional data retrieval or analysis.
    """
    graph = StateGraph(MCPGraphState)

    # Add nodes
    graph.add_node("init", init_state)
    graph.add_node("run_cycle", run_cycle)
    graph.add_node("tools", ToolNode(mcp_tools))

    # Add edges
    graph.add_edge(START, "init")
    graph.add_edge("init", "run_cycle")
    graph.add_conditional_edges(
        "run_cycle",
        route_after_cycle,
        {
            "tools": "tools",
            END: END,
        },
    )
    graph.add_edge("tools", END)

    return graph.compile()
