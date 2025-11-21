#!/usr/bin/env python3
"""Visualize the agentic environmental monitoring workflow."""

from defra_agent.agent.graph import build_graph

# Build the graph
graph = build_graph()

# Get the Mermaid diagram
try:
    mermaid_code = graph.get_graph().draw_mermaid()
    print("# Agentic Environmental Monitoring Workflow\n")
    print("```mermaid")
    print(mermaid_code)
    print("```")
    print("\n## Key Features:")
    print("- ✅ LLM-driven decision making (agent node)")
    print(
        "- ✅ MCP tool calling (get_flood_readings, "
        "get_hydrology_readings, search_public_registers)"
    )
    print("- ✅ Conditional routing based on findings")
    print("- ✅ Multi-step reasoning workflow")
    print("- ✅ Autonomous data gathering and analysis")
except Exception as e:
    print(f"Error generating diagram: {e}")
    print("\nGraph nodes:")
    print(graph.get_graph().nodes)
