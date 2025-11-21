import asyncio

from defra_agent.agent.graph import build_graph


async def run_once_async() -> None:
    """Execute a single agent run."""
    graph = build_graph()
    await graph.ainvoke({})


def run_once() -> None:
    """Entry point wrapper for the script command."""
    asyncio.run(run_once_async())


if __name__ == "__main__":
    run_once()
