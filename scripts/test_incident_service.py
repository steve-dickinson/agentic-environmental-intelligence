import asyncio
import sys
from pathlib import Path

src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from defra_agent.services.incident_service import IncidentService  # noqa: E402
from defra_agent.services.summariser import AlertSummariser  # noqa: E402
from defra_agent.storage.mongo_repo import IncidentRepository  # noqa: E402
from defra_agent.storage.pgvector_repo import IncidentVectorRepository  # noqa: E402
from defra_agent.tools.flood_client import FloodClient  # noqa: E402
from defra_agent.tools.hydrology_client import HydrologyClient  # noqa: E402


async def main() -> None:
    service = IncidentService(
        flood_client=FloodClient(),
        hydrology_client=HydrologyClient(),
        summariser=AlertSummariser(),
        incident_repo=IncidentRepository(),
        vector_repo=IncidentVectorRepository(),
    )
    incident = await service.run_detection_cycle()
    if incident is None:
        print("No incident created (no anomalies).")
    else:
        print("Incident created:", incident.id)
        print("Alerts:", len(incident.alerts))


if __name__ == "__main__":
    asyncio.run(main())
