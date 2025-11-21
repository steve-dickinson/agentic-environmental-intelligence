from __future__ import annotations

from defra_agent.config import settings
from defra_agent.domain.anomaly_detector import detect_threshold_anomalies
from defra_agent.domain.models import Incident, Permit, Reading
from defra_agent.services.summariser import AlertSummariser
from defra_agent.storage.mongo_repo import IncidentRepository
from defra_agent.storage.pgvector_repo import IncidentVectorRepository
from defra_agent.tools.flood_client import FloodClient
from defra_agent.tools.hydrology_client import HydrologyClient
from defra_agent.tools.public_registers_client import PublicRegistersClient


class IncidentService:

    def __init__(
        self,
        flood_client: FloodClient,
        hydrology_client: HydrologyClient,
        public_registers_client: PublicRegistersClient,
        summariser: AlertSummariser,
        incident_repo: IncidentRepository,
        vector_repo: IncidentVectorRepository,
    ) -> None:
        self._flood_client = flood_client
        self._hydrology_client = hydrology_client
        self._public_registers_client = public_registers_client
        self._summariser = summariser
        self._incident_repo = incident_repo
        self._vector_repo = vector_repo

    @staticmethod
    def _choose_anchor_reading(readings: list[Reading]) -> Reading | None:
        candidates = [
            r
            for r in readings
            if r.easting is not None and r.northing is not None
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda r: r.value)

    @staticmethod
    def _filter_readings_for_anchor(
        anomalies: list[Reading],
        anchor: Reading,
    ) -> list[Reading]:
        same_station = [r for r in anomalies if r.station_id == anchor.station_id]
        if same_station:
            return same_station
        return [anchor]

    async def run_detection_cycle(self) -> Incident | None:

        flood_readings = await self._flood_client.get_latest_readings()
        hydrology_readings = await self._hydrology_client.get_latest_readings()

        all_readings: list[Reading] = [*flood_readings, *hydrology_readings]

        anomalies = detect_threshold_anomalies(
            all_readings,
            threshold=settings.anomaly_threshold,
        )
        if not anomalies:
            return None

        anchor = self._choose_anchor_reading(anomalies)
        if anchor is None:
            return None

        local_readings = self._filter_readings_for_anchor(anomalies, anchor)

        permits: list[Permit] = []
        if anchor.easting is not None and anchor.northing is not None:
            permits = await self._public_registers_client.fetch_permits_for_location(
                easting=anchor.easting,
                northing=anchor.northing,
                dist_km=settings.public_registers_dist_km,
            )

        alerts = await self._summariser.summarise(local_readings, permits=permits)

        incident = self._incident_repo.create_incident(
            readings=local_readings,
            alerts=alerts,
            permits=permits,
        )
        self._vector_repo.store_incident(incident)
        return incident

