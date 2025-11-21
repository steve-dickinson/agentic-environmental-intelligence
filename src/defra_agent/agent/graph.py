"""Agentic environmental monitoring graph with LLM-driven decision making."""

import json
from typing import Annotated, Any, Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from defra_agent.config import settings
from defra_agent.domain.anomaly_detector import detect_threshold_anomalies
from defra_agent.domain.clustering import (
    cluster_anomalies_spatially,
    filter_recent_readings,
    get_cluster_center,
)
from defra_agent.domain.models import Alert, AlertPriority, Incident, Permit, Reading
from defra_agent.storage.mongo_repo import IncidentRepository
from defra_agent.storage.pgvector_repo import IncidentVectorRepository
from defra_agent.tools.mcp_tools import (
    get_flood_readings,
    get_hydrology_readings,
    search_public_registers,
)


def reduce_messages(left: list[BaseMessage], right: list[BaseMessage]) -> list[BaseMessage]:
    """Custom message reducer that trims large ToolMessage content to prevent token bloat."""
    # Combine messages
    all_messages = left + right

    # Trim ToolMessage content to just summaries
    trimmed = []
    for msg in all_messages:
        if isinstance(msg, ToolMessage):
            # Parse the content and replace with summary
            try:
                content = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                if "readings" in content and len(content["readings"]) > 0:
                    summary = {"count": len(content["readings"]), "data_type": "readings"}
                elif "entries" in content:
                    summary = {"count": len(content["entries"]), "data_type": "entries"}
                else:
                    summary = content

                trimmed.append(
                    ToolMessage(
                        content=json.dumps(summary), tool_call_id=msg.tool_call_id, name=msg.name
                    )
                )
            except Exception:
                trimmed.append(msg)
        else:
            trimmed.append(msg)

    return trimmed


class AgentState(TypedDict):
    """State tracked throughout the agentic workflow."""

    messages: Annotated[list, reduce_messages]  # Conversation history (auto-trims large content)
    flood_readings: list[dict[str, Any]]  # Raw flood data
    hydrology_readings: list[dict[str, Any]]  # Raw hydrology data
    all_readings: list[Reading]  # Processed Reading objects
    anomalies: list[Reading]  # Detected anomalous readings
    clusters: list[list[Reading]]  # Spatial clusters of anomalies
    current_cluster_index: int  # Which cluster we're processing
    permits: list[dict[str, Any]]  # Nearby environmental permits
    incident: Incident | None  # Final generated incident
    incidents: list[Incident]  # All generated incidents (one per cluster)
    next_action: str  # Tracking for routing


def _get_llm() -> ChatOpenAI:
    """Get configured LLM for agent."""
    return ChatOpenAI(
        model=settings.openai_model,
        temperature=0,  # Deterministic for consistency
    )


def _get_tools() -> list:
    """Get MCP tools available to agent."""
    return [
        get_flood_readings,
        get_hydrology_readings,
        search_public_registers,
    ]


def agent_start(state: AgentState) -> AgentState:
    """Initialize agent with mission and system prompt."""
    system_msg = SystemMessage(
        content="""You are an environmental monitoring agent for the UK Environment Agency.

Your mission: Detect and investigate potential environmental incidents by analyzing 
flood and hydrology sensor data, identifying anomalies, and gathering regulatory context.

Available tools:
- get_flood_readings: Fetch latest flood monitoring data (water levels)
- get_hydrology_readings: Fetch latest hydrology data (flow, groundwater)
- search_public_registers: Search for environmental permits near a location

Workflow:
1. FIRST: Call get_flood_readings with parameter='level'
2. WAIT for results before making next decision
3. NEXT: Call get_hydrology_readings with parameter='waterLevel'
4. WAIT for anomaly detection to complete automatically
5. IF anomalies found: Optionally search for nearby permits
6. System will automatically generate final incident report

CRITICAL RULES:
- Call only ONE tool per turn
- Never call the same tool multiple times
- Wait for feedback before deciding next action
- After data collection, the system handles analysis automatically

Be systematic and patient."""
    )

    mission_msg = HumanMessage(
        content="Begin environmental monitoring cycle. Start by fetching flood readings."
    )

    return {
        **state,
        "messages": [system_msg, mission_msg],
        "flood_readings": [],
        "hydrology_readings": [],
        "all_readings": [],
        "anomalies": [],
        "permits": [],
        "incident": None,
        "next_action": "agent",
    }


def agent_node(state: AgentState) -> AgentState:
    """LLM agent decides which tools to call based on current state."""
    llm = _get_llm()
    tools = _get_tools()

    # Bind tools to LLM so it knows what's available
    llm_with_tools = llm.bind_tools(tools)

    # LLM decides next action based on conversation history
    print("\n🤖 Agent thinking...")
    response = llm_with_tools.invoke(state["messages"])

    # Log the agent's decision
    if isinstance(response, AIMessage) and response.tool_calls:
        tool_names = [tc["name"] for tc in response.tool_calls]
        print(f"   → Calling tools: {', '.join(tool_names)}")
    elif isinstance(response, AIMessage):
        print(f"   → Response: {response.content[:100]}...")

    return {
        **state,
        "messages": [response],
    }


def route_after_agent(
    state: AgentState,
) -> Literal["tools", "detect_anomalies", "generate_incident", "end"]:
    """Route based on agent's decision."""
    last_message = state["messages"][-1]

    # If agent wants to call tools
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        print("   📍 Routing to: tools")
        return "tools"

    # If we have readings but haven't analyzed them yet
    if (state["flood_readings"] or state["hydrology_readings"]) and not state["all_readings"]:
        print("   📍 Routing to: detect_anomalies")
        return "detect_anomalies"

    # If we have anomalies, generate incident
    if state["anomalies"]:
        print("   📍 Routing to: generate_incident")
        return "generate_incident"

    # Default: end
    print("   📍 Routing to: end")
    return "end"


def process_tool_results(state: AgentState) -> AgentState:
    """Provide summary of tool execution to agent."""
    print("\n📦 Processing tool results...")

    # Data is already extracted by tool_node_with_extraction
    flood_count = len(state.get("flood_readings", []))
    hydro_count = len(state.get("hydrology_readings", []))
    permit_count = len(state.get("permits", []))
    has_anomalies = len(state.get("anomalies", [])) > 0

    tool_results = []
    if flood_count > 0:
        tool_results.append(f"✓ Retrieved {flood_count} flood readings")
    if hydro_count > 0:
        tool_results.append(f"✓ Retrieved {hydro_count} hydrology readings")
    if permit_count > 0:
        tool_results.append(f"✓ Found {permit_count} environmental permits")

    # Add a summary message for the agent to continue
    if tool_results:
        for result in tool_results:
            print(f"   {result}")

        # If we have anomalies, tell agent to wrap up
        if has_anomalies:
            summary_msg = HumanMessage(
                content="Tool execution complete. Proceed to generate final incident report."
            )
        else:
            summary_msg = HumanMessage(
                content="Tool execution complete:\n"
                + "\n".join(tool_results)
                + f"\n\nReady to analyze {flood_count + hydro_count} readings for anomalies."
            )
        return {
            **state,
            "messages": [summary_msg],
        }

    return state


def detect_anomalies_node(state: AgentState) -> AgentState:
    """Process readings and detect anomalies."""
    print("\n🔬 Detecting anomalies...")

    flood_readings = state["flood_readings"]
    hydrology_readings = state["hydrology_readings"]

    # Convert to Reading objects
    all_readings: list[Reading] = []

    from datetime import datetime

    for item in flood_readings:
        # Parse timestamp if it's a string
        ts = item["timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))

        all_readings.append(
            Reading(
                station_id=item["station_id"],
                value=item["value"],
                timestamp=ts,
                source="flood",
                easting=item.get("easting"),
                northing=item.get("northing"),
                lat=item.get("lat"),
                lon=item.get("lon"),
            )
        )

    for item in hydrology_readings:
        # Parse timestamp if it's a string
        ts = item["timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))

        all_readings.append(
            Reading(
                station_id=item["station_id"],
                value=item["value"],
                timestamp=ts,
                source="hydrology",
                easting=item.get("easting"),
                northing=item.get("northing"),
                lat=item.get("lat"),
                lon=item.get("lon"),
            )
        )

    # Detect anomalies
    anomalies = detect_threshold_anomalies(all_readings, threshold=settings.anomaly_threshold)

    print(f"   → Found {len(anomalies)} anomalies out of {len(all_readings)} readings")

    # Filter to recent anomalies (last 24 hours)
    recent_anomalies = filter_recent_readings(anomalies, time_window_hours=24)
    print(f"   → {len(recent_anomalies)} anomalies in last 24 hours")

    # Cluster anomalies spatially
    clusters = cluster_anomalies_spatially(
        recent_anomalies,
        max_distance_km=10.0,  # 10km radius
        min_cluster_size=2,  # At least 2 readings per cluster
    )
    print(f"   → Grouped into {len(clusters)} spatial clusters")

    # Create summary message for agent
    if clusters:
        threshold = settings.anomaly_threshold
        anomaly_summary = (
            f"Analysis complete. Found {len(recent_anomalies)} recent anomalous readings "
            f"above threshold {threshold}, grouped into {len(clusters)} spatial clusters.\n\n"
        )

        # Show top cluster
        top_cluster = clusters[0]
        lat, lon = get_cluster_center(top_cluster)
        anomaly_summary += (
            f"Largest cluster: {len(top_cluster)} anomalies near ({lat:.4f}, {lon:.4f})\n"
        )
        anomaly_summary += "Top 3 stations in this cluster:\n"
        for i, reading in enumerate(
            sorted(top_cluster, key=lambda r: r.value, reverse=True)[:3], 1
        ):
            anomaly_summary += (
                f"{i}. Station {reading.station_id}: {reading.value} @ {reading.timestamp}\n"
            )

        anomaly_summary += (
            "\nEach cluster represents a localized environmental incident. "
            "You should investigate nearby environmental permits for each cluster."
        )
    else:
        threshold = settings.anomaly_threshold
        anomaly_summary = (
            f"Analysis complete. Found {len(anomalies)} anomalies but no spatial clusters "
            f"formed (need at least 2 nearby readings within 10km). All readings are dispersed."
        )

    return {
        **state,
        "all_readings": all_readings,
        "anomalies": recent_anomalies,
        "clusters": clusters,
        "current_cluster_index": 0,
        "incidents": [],
        "messages": state["messages"] + [HumanMessage(content=anomaly_summary)],
    }


async def generate_incident_node(state: AgentState) -> AgentState:
    """Generate localized incidents for each spatial cluster."""
    print("\n📝 Generating localized incident reports...")

    clusters = state.get("clusters", [])
    if not clusters:
        print("   ⚠️  No clusters to process")
        return {
            **state,
            "next_action": "end",
        }

    incident_repo = IncidentRepository()
    vector_repo = IncidentVectorRepository()
    incidents = []

    # Import the public registers client for per-cluster permit search
    from defra_agent.tools.public_registers_client import PublicRegistersClient

    registers_client = PublicRegistersClient()

    for i, cluster in enumerate(clusters, 1):
        print(f"\n   🎯 Processing cluster {i}/{len(clusters)}: {len(cluster)} anomalies")

        # Get cluster center for permit search
        center_lat, center_lon = get_cluster_center(cluster)
        print(f"      Cluster center: {center_lat:.4f}, {center_lon:.4f}")

        # Search for permits near this cluster
        # Need to convert lat/lon to British National Grid (easting/northing)
        # For now, use the first reading's coordinates if available
        cluster_easting = None
        cluster_northing = None
        for reading in cluster:
            if reading.easting and reading.northing:
                cluster_easting = reading.easting
                cluster_northing = reading.northing
                break

        cluster_permits = []
        if cluster_easting and cluster_northing:
            try:
                # Search for permits within 1km of cluster center
                permit_results = await registers_client.search_by_coordinates(
                    easting=cluster_easting,
                    northing=cluster_northing,
                    dist_km=1.0,
                )
                cluster_permits = permit_results[:10]  # Limit to 10
                print(f"      Found {len(cluster_permits)} nearby permits")
            except Exception as e:
                print(f"      ⚠️  Error searching permits: {e}")

        # Generate cluster-specific alert summary (data-driven, source-aware)
        # Get station details
        station_list = [r.station_id for r in cluster]
        values = [r.value for r in cluster]
        max_value = max(values)
        avg_value = sum(values) / len(values)

        # Get sources and determine context
        sources = list(set(r.source for r in cluster if r.source))
        is_flood = "flood" in sources
        is_hydrology = "hydrology" in sources

        # Build context-aware summary based on source
        station_names = station_list[0]
        if len(station_list) > 1:
            station_names += f", {station_list[1]}"

        if is_flood and not is_hydrology:
            # Flood context - river levels, flood risk
            content = (
                f"Elevated river levels at {len(cluster)} stations "
                f"({station_names}). "
                f"Peak: {max_value:.2f}m, Average: {avg_value:.2f}m. "
                f"Flood risk threshold: {settings.anomaly_threshold}m. "
            )
        elif is_hydrology and not is_flood:
            # Hydrology context - groundwater, flow, potential contamination
            content = (
                f"Anomalous hydrology readings at {len(cluster)} stations "
                f"({station_names}). "
                f"Peak: {max_value:.2f}, Average: {avg_value:.2f} "
                f"(threshold: {settings.anomaly_threshold}). "
            )
        else:
            # Mixed or unknown
            source_text = "/".join(sources) if sources else "monitoring"
            content = (
                f"{len(cluster)} {source_text} stations showing elevated readings "
                f"near {station_names}. "
                f"Peak: {max_value:.2f}, Average: {avg_value:.2f} "
                f"(threshold: {settings.anomaly_threshold}). "
            )

        # Analyze permits based on source context
        if cluster_permits:
            permit_types = set()
            permit_labels = []

            for p in cluster_permits:
                reg_label = p.get("register_label", "")

                # Categorize permits
                if "flood" in reg_label.lower():
                    permit_types.add("flood risk activities")
                    permit_labels.append(reg_label)
                elif "waste" in reg_label.lower():
                    permit_types.add("waste operations")
                    permit_labels.append(reg_label)
                elif "discharge" in reg_label.lower():
                    permit_types.add("discharge consents")
                    permit_labels.append(reg_label)
                elif "abstraction" in reg_label.lower():
                    permit_types.add("water abstraction")
                    permit_labels.append(reg_label)
                elif "installation" in reg_label.lower():
                    permit_types.add("industrial installations")
                    permit_labels.append(reg_label)

            if permit_types:
                types_str = ", ".join(sorted(permit_types))
                content += f"{len(cluster_permits)} {types_str} within 1km."
            else:
                # Get most common register type
                if permit_labels:
                    most_common = max(set(permit_labels), key=permit_labels.count)
                    content += f"{len(cluster_permits)} permits ({most_common[:40]}...) within 1km."
                else:
                    content += f"{len(cluster_permits)} permits within 1km."
        else:
            content += "No nearby permits identified."

        # Determine priority based on cluster's max value
        if max_value > settings.anomaly_threshold * 2:
            priority = AlertPriority.HIGH
        elif max_value > settings.anomaly_threshold * 1.5:
            priority = AlertPriority.MEDIUM
        else:
            priority = AlertPriority.LOW

        # Create source-aware suggested actions
        actions = []

        if is_flood:
            actions.append(f"Monitor river levels at {', '.join(station_list[:2])}")
            if max_value > settings.anomaly_threshold * 1.5:
                actions.append(f"Assess flood risk: {max_value:.2f}m exceeds safe levels")
            else:
                actions.append("Investigate cause of elevated water levels")

            if cluster_permits:
                if any("flood" in p.get("register_label", "").lower() for p in cluster_permits):
                    actions.append(f"Review {len(cluster_permits)} flood risk activity exemptions")
                else:
                    actions.append(f"Check if {len(cluster_permits)} nearby permits affecting flow")

        elif is_hydrology:
            actions.append(f"Monitor groundwater/flow at {', '.join(station_list[:2])}")
            actions.append(f"Investigate anomaly: peak {max_value:.2f}")

            if cluster_permits:
                if any("waste" in p.get("register_label", "").lower() for p in cluster_permits):
                    actions.append(
                        f"Check {len(cluster_permits)} waste permits " "for contamination risk"
                    )
                elif any(
                    "discharge" in p.get("register_label", "").lower() for p in cluster_permits
                ):
                    actions.append(
                        f"Review {len(cluster_permits)} discharge consents " "for compliance"
                    )
                else:
                    actions.append(
                        f"Investigate {len(cluster_permits)} nearby " "permitted activities"
                    )

        else:
            # Fallback generic actions
            actions.append(f"Monitor {', '.join(station_list[:2])} for continued elevation")
            actions.append(f"Investigate cause of {max_value:.2f} reading (peak value)")
            if cluster_permits:
                actions.append(
                    f"Contact operators of {len(cluster_permits)} nearby permits "
                    "for compliance check"
                )
            else:
                actions.append("Investigate non-permitted sources in the area")

        alert = Alert(
            summary=content[:500],
            priority=priority,
            suggested_actions=actions,
        )

        # Convert permits to Permit objects
        permit_objects: list[Permit] = []
        for p in cluster_permits:
            distance = p.get("distance")
            if distance:
                try:
                    distance = float(distance)
                except (ValueError, TypeError):
                    distance = None

            permit_objects.append(
                Permit(
                    permit_id=p.get("registrationNumber", p.get("@id", "unknown")),
                    operator_name=p.get("holder.name", "Unknown"),
                    register_label=p.get("register.label"),
                    registration_type=p.get("registrationType.label"),
                    site_address=p.get("site.siteAddress.address", ""),
                    site_postcode=p.get("site.siteAddress.postcode"),
                    distance_km=distance,
                )
            )

        # Create incident for this cluster
        incident = incident_repo.create_incident(
            readings=cluster[:20],  # Top 20 from this cluster
            alerts=[alert],
            permits=permit_objects,
        )
        vector_repo.store_incident(incident)
        incidents.append(incident)

        print(f"      ✅ Incident {incident.id} created ({priority.value} priority)")

    # Create final summary message
    final_msg = AIMessage(
        content=f"""✅ Localized incident analysis complete.

Generated {len(incidents)} incidents from {len(clusters)} spatial clusters:
"""
        + "\n".join(
            [
                f"- Incident {inc.id}: {inc.alerts[0].priority.value} priority, "
                f"{len(inc.readings)} readings, {len(inc.permits or [])} permits"
                for inc in incidents
            ]
        )
        + "\n\nEnvironmental monitoring cycle complete. All incidents stored in database."
    )

    return {
        **state,
        "incidents": incidents,
        "incident": incidents[0] if incidents else None,  # For backwards compatibility
        "messages": state["messages"] + [final_msg],
        "next_action": "end",
    }


def build_graph() -> Any:
    """Build the agentic environmental monitoring graph."""
    # Create tool node with custom wrapper to extract data
    tools = _get_tools()
    base_tool_node = ToolNode(tools)

    async def tool_node_with_extraction(state: AgentState) -> dict:
        """Execute tools and immediately extract data before messages are reduced."""
        # Run tools normally (async)
        result = await base_tool_node.ainvoke(state)

        # Extract data from the ToolMessages BEFORE they get trimmed
        flood_readings = state.get("flood_readings", [])
        hydrology_readings = state.get("hydrology_readings", [])
        permits = state.get("permits", [])

        import json

        for msg in result.get("messages", []):
            if isinstance(msg, ToolMessage):
                try:
                    if isinstance(msg.content, str):
                        content = json.loads(msg.content)
                    else:
                        content = msg.content

                    if msg.name == "get_flood_readings" and "readings" in content:
                        flood_readings = content["readings"]
                    elif msg.name == "get_hydrology_readings" and "readings" in content:
                        hydrology_readings = content["readings"]
                    elif msg.name == "search_public_registers" and "entries" in content:
                        permits = content["entries"]
                except Exception as e:
                    print(f"⚠️  Error extracting from {msg.name}: {e}")

        # Return both messages and extracted data
        return {
            **result,
            "flood_readings": flood_readings,
            "hydrology_readings": hydrology_readings,
            "permits": permits,
        }

    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("start", agent_start)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node_with_extraction)  # Use async wrapper that extracts data
    graph.add_node("process_tools", process_tool_results)
    graph.add_node("detect_anomalies", detect_anomalies_node)
    graph.add_node("generate_incident", generate_incident_node)

    # Add edges
    graph.add_edge(START, "start")
    graph.add_edge("start", "agent")

    # Agent decides: call tools, analyze data, generate incident, or end
    graph.add_conditional_edges(
        "agent",
        route_after_agent,
        {
            "tools": "tools",
            "detect_anomalies": "detect_anomalies",
            "generate_incident": "generate_incident",
            "end": END,
        },
    )

    # After tools execute, process results and return to agent
    graph.add_edge("tools", "process_tools")
    graph.add_edge("process_tools", "agent")

    # After detecting anomalies, return to agent for next decision
    graph.add_edge("detect_anomalies", "agent")

    # After generating incident, end
    graph.add_edge("generate_incident", END)

    # Compile with higher recursion limit to allow for permit searches
    return graph.compile()
