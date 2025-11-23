"""View agent run logs from MongoDB."""

from defra_agent.storage.run_log_repo import RunLogRepository


def main() -> None:
    """Display recent agent run logs and statistics."""
    repo = RunLogRepository()

    print("\n📊 Agent Run Statistics (Last 7 Days)")
    print("=" * 60)

    stats = repo.get_statistics(days=7)
    print(f"Total Runs:              {stats['total_runs']}")
    print(f"Incidents Created:       {stats['total_incidents_created']}")
    print(f"Incidents Duplicate:     {stats['total_incidents_duplicate']}")
    print(f"Duplicate Rate:          {stats['duplicate_rate']}%")
    print(f"Total Clusters:          {stats['total_clusters']}")
    print(f"Total RAG Searches:      {stats['total_rag_searches']}")
    print(f"Avg Duration:            {stats['avg_duration']:.2f}s")

    print("\n\n📋 Recent Runs (Last 10)")
    print("=" * 60)

    recent = repo.get_recent_runs(limit=10)

    if not recent:
        print("No runs found.")
    else:
        for run in recent:
            print(f"\nRun ID: {run['run_id']}")
            print(f"  Time: {run['timestamp']}")
            print(f"  Duration: {run['duration_seconds']:.2f}s")
            print(f"  Readings: {run['readings_fetched']}")
            print(f"  Clusters: {run['clusters_found']}")
            print(
                f"  Incidents: {run['incidents_created']} created, {run['incidents_duplicate']} duplicates"
            )

            if run.get("rag_results"):
                for rag in run["rag_results"]:
                    print(f"  RAG: Found {rag['similar_incidents_found']} similar incidents")
                    if rag.get("avg_similarity"):
                        print(f"       Avg similarity: {rag['avg_similarity']:.2%}")

    repo.close()


if __name__ == "__main__":
    main()
