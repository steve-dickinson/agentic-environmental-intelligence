from defra_agent.config import settings
from defra_agent.domain.anomaly_detector import detect_threshold_anomalies
from defra_agent.domain.models import Incident
from defra_agent.services.summariser import AlertSummariser
from defra_agent.storage.mongo_repo import IncidentRepository
from defra_agent.storage.pgvector_repo import IncidentVectorRepository
from defra_agent.tools.flood_client import FloodClient
from defra_agent.tools.hydrology_client import HydrologyClient


class IncidentService:
    """Use-case layer: from sensor data to stored incidents & alerts."""

    def __init__(
        self,
        flood_client: FloodClient,
        hydrology_client: HydrologyClient,
        summariser: AlertSummariser,
        incident_repo: IncidentRepository,
        vector_repo: IncidentVectorRepository,
    ) -> None:
        self._flood_client = flood_client
        self._hydrology_client = hydrology_client
        self._summariser = summariser
        self._incident_repo = incident_repo
        self._vector_repo = vector_repo

    async def run_detection_cycle(self) -> Incident | None:
        flood_readings = await self._flood_client.get_latest_readings()

        hydrology_readings = await self._hydrology_client.get_latest_readings()

        all_readings = [*flood_readings, *hydrology_readings]

        anomalies = detect_threshold_anomalies(
            all_readings,
            threshold=settings.anomaly_threshold,
        )

        if not anomalies:
            return None

        alerts = await self._summariser.summarise(anomalies)
        incident = self._incident_repo.create_incident(readings=anomalies, alerts=alerts)
        self._vector_repo.store_incident(incident)
        return incident
