# MCP Tools Integration Guide

## Overview

This project demonstrates **proper MCP (Model Context Protocol) tool integration** with LangGraph agents. MCP tools are designed for **LLM agent tool calling**, not as API client wrappers.

## Architecture

### ✅ Correct Approach: MCP Tools for Agent Tool Calling

```
┌─────────────────────────────────────────────────────────────┐
│                      LangGraph Agent                         │
│                                                              │
│  ┌─────────────┐                                            │
│  │   Agent     │  Calls tools based on LLM decisions        │
│  │   (LLM)     │                                            │
│  └──────┬──────┘                                            │
│         │                                                    │
│         ├─► MCP Tool: get_flood_readings()                  │
│         ├─► MCP Tool: get_hydrology_readings()              │
│         └─► MCP Tool: search_public_registers()             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

The agent **decides when to call tools** based on the task at hand. Tools are **stateless functions** decorated with `@tool` that the LLM can invoke.

### ❌ Incorrect Approach: MCP as API Client Wrapper

```
Don't use MCP to wrap API clients for synchronous workflow:

Service → MCPFloodClient → MCP Server → API  ❌
Service → FloodClient → API                   ✓
```

MCP adds overhead when you know exactly which data to fetch in a deterministic workflow.

## File Structure

```
src/defra_agent/
├── tools/
│   ├── mcp_tools.py           # LangChain @tool decorators for agent
│   ├── flood_client.py        # Direct API client (still used)
│   ├── hydrology_client.py    # Direct API client (still used)
│   └── public_registers_client.py  # Direct API client (still used)
├── agent/
│   ├── graph.py               # Standard detection cycle graph
│   └── mcp_graph.py           # Enhanced graph with MCP tools
└── services/
    └── incident_service.py    # Uses direct clients for deterministic workflow
```

## Implementation

### 1. MCP Tools (`mcp_tools.py`)

Tools are decorated with `@tool` from LangChain:

```python
from langchain_core.tools import tool

@tool
async def get_flood_readings(parameter: str = "level") -> dict[str, Any]:
    """Get latest flood monitoring readings from Environment Agency.
    
    Args:
        parameter: Parameter to filter by (e.g. 'level', 'flow')
        
    Returns:
        Dictionary with readings list and count
    """
    # Fetch and process data
    return {"readings": [...], "count": 100}
```

### 2. Agent Integration (`mcp_graph.py`)

Tools are added to the agent graph via `ToolNode`:

```python
from langgraph.prebuilt import ToolNode
from defra_agent.tools.mcp_tools import (
    get_flood_readings,
    get_hydrology_readings,
    search_public_registers,
)

# Define available tools
mcp_tools = [
    get_flood_readings,
    get_hydrology_readings,
    search_public_registers,
]

# Add to graph
graph.add_node("tools", ToolNode(mcp_tools))
```

### 3. When to Use MCP Tools vs Direct Clients

**Use MCP Tools (@tool) when:**
- Agent needs to **decide** which data to fetch based on context
- LLM should **choose** between different data sources
- Building **conversational** or **interactive** agents
- Want the LLM to **explore** data dynamically

**Use Direct Clients when:**
- Workflow is **deterministic** (always fetch same data)
- Building **batch processing** or **scheduled jobs**
- Need **maximum performance** (no LLM inference overhead)
- Data requirements are **known upfront**

## Current Usage

### Deterministic Detection Cycle (Uses Direct Clients)

```python
# src/defra_agent/services/incident_service.py
async def run_detection_cycle(self):
    # Always fetch both flood and hydrology data
    flood_readings = await self._flood_client.get_latest_readings()
    hydrology_readings = await self._hydrology_client.get_latest_readings()
    
    # Process anomalies...
    # This doesn't need LLM decision-making
```

### Future: Agent-Driven Analysis (Uses MCP Tools)

```python
# Example future use case
async def investigate_incident(incident_id: str):
    """Agent investigates an incident by choosing which tools to call."""
    
    # Agent decides: "I should check flood readings near this location"
    flood_data = await agent.call_tool("get_flood_readings", {...})
    
    # Agent decides: "Now I need permit information"
    permits = await agent.call_tool("search_public_registers", {...})
    
    # LLM synthesizes findings into a report
```

## Testing

### Test MCP Tools as LangChain Tools

```bash
uv run python scripts/test_mcp_tools.py
```

This validates that tools:
- Are properly decorated with `@tool`
- Can be invoked with `.ainvoke()`
- Return expected data structures
- Are ready for LangGraph integration

### Test MCP Server Directly

```bash
uv run python scripts/test_mcp_server.py
```

This tests the standalone MCP server (used if connecting via stdio/HTTP).

## Key Differences: MCP Tools vs MCP Server

| Aspect | MCP Tools (`@tool`) | MCP Server (`FastMCP`) |
|--------|-------------------|----------------------|
| **Use Case** | Agent tool calling | External tool protocol |
| **Integration** | Direct import in Python | stdio/HTTP communication |
| **Overhead** | Minimal | Protocol serialization |
| **Best For** | LangGraph agents | Claude Desktop, other clients |

For LangGraph agents in the same codebase, use `@tool` decorated functions directly. The FastMCP server is for external clients that need the MCP protocol.

## Benefits of This Approach

1. **Flexibility**: Agent can use tools OR direct clients as needed
2. **Performance**: Direct clients for deterministic workflows
3. **Discoverability**: Tools are self-documenting for the LLM
4. **Composability**: Tools can be combined in agent workflows
5. **Future-Proof**: Ready for more complex agent behaviors

## Next Steps

To fully leverage MCP tools in the agent:

1. **Add LLM node** to the graph that can decide which tools to call
2. **Create prompts** that guide the agent on when to use each tool
3. **Add conditional routing** based on agent decisions
4. **Implement memory** so agent remembers what tools it's called
5. **Build conversational interface** for users to interact with tools

Example enhanced graph:
```python
graph.add_node("llm", llm_node_with_tools)
graph.add_conditional_edges(
    "llm",
    route_based_on_llm_decision,
    {
        "use_tools": "tools",
        "finish": END,
    }
)
```

This allows the agent to **intelligently decide** when and how to use MCP tools based on the task at hand.
