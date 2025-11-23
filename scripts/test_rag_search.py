"""Test script for RAG similarity search functionality.

This script demonstrates:
1. Searching for similar incidents using vector similarity
2. Finding incidents similar to a specific incident
3. Showing similarity scores and summaries
"""

import asyncio

from defra_agent.storage.pgvector_repo import IncidentVectorRepository


async def main():
    """Test RAG similarity search."""
    print("=" * 80)
    print("RAG Similarity Search Test")
    print("=" * 80)

    repo = IncidentVectorRepository()

    # Test 1: Search by query text
    print("\n📝 Test 1: Search for flood-related incidents")
    print("-" * 80)

    query = "Elevated river levels in Somerset Levels with flood risk"
    print(f"Query: {query}\n")

    similar = repo.find_similar_incidents(
        query_text=query,
        limit=5,
        similarity_threshold=0.5,
    )

    if similar:
        print(f"✅ Found {len(similar)} similar incidents:\n")
        for i, incident in enumerate(similar, 1):
            print(f"{i}. Similarity: {incident.similarity:.2%}")
            print(f"   Incident ID: {incident.incident_id}")
            print(f"   Summary: {incident.summary[:150]}...")
            print()
    else:
        print("⚠️  No similar incidents found (database may be empty)")
        print("   Run 'uv run defra-agent-run' to create some incidents first")

    # Test 2: Search for hydrology incidents
    print("\n📝 Test 2: Search for hydrology/groundwater incidents")
    print("-" * 80)

    query2 = "Anomalous groundwater levels requiring investigation"
    print(f"Query: {query2}\n")

    similar2 = repo.find_similar_incidents(
        query_text=query2,
        limit=5,
        similarity_threshold=0.5,
    )

    if similar2:
        print(f"✅ Found {len(similar2)} similar incidents:\n")
        for i, incident in enumerate(similar2, 1):
            print(f"{i}. Similarity: {incident.similarity:.2%}")
            print(f"   Incident ID: {incident.incident_id}")
            print(f"   Summary: {incident.summary[:150]}...")
            print()
    else:
        print("⚠️  No similar hydrology incidents found")

    # Test 3: Different similarity thresholds
    print("\n📝 Test 3: Testing different similarity thresholds")
    print("-" * 80)

    query3 = "River monitoring stations showing elevated readings"
    print(f"Query: {query3}\n")

    for threshold in [0.9, 0.7, 0.5]:
        results = repo.find_similar_incidents(
            query_text=query3,
            limit=10,
            similarity_threshold=threshold,
        )
        print(f"Threshold {threshold:.1%}: {len(results)} results")

    print("\n" + "=" * 80)
    print("✅ RAG Test Complete")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
