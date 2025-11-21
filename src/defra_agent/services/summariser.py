from typing import cast

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, SecretStr

from defra_agent.config import settings
from defra_agent.domain.models import Alert, AlertPriority, Permit, Reading


class AlertSchema(BaseModel):  # type: ignore[misc]
    """Schema for a single alert."""

    summary: str = Field(description="Brief summary of the environmental risk")
    priority: str = Field(description="Priority level: high, medium, or low")
    suggested_actions: list[str] = Field(description="List of recommended actions to take")


class AlertsResponse(BaseModel):  # type: ignore[misc]
    """Schema for the complete alerts response."""

    alerts: list[AlertSchema] = Field(description="List of generated alerts")


class AlertSummariser:
    """Turns anomalies into structured alerts using an LLM."""

    def __init__(self, model_name: str | None = None) -> None:
        api_key = SecretStr(settings.openai_api_key) if settings.openai_api_key else None
        llm = ChatOpenAI(
            model=model_name or settings.openai_model,
            temperature=0.1,
            api_key=api_key,
        )

        self._llm = llm.with_structured_output(AlertsResponse)

    async def summarise(self, anomalies: list[Reading], permits: list[Permit] | None = None) -> list[Alert]:
        if not anomalies:
            return []

        anomalies_text = "\n".join(
            f"- Source={a.source or 'unknown'} "
            f"Station={a.station_id} "
            f"Time={a.timestamp.isoformat()} "
            f"Value={a.value}"
            for a in anomalies
        )

        permits_text = ""
        if permits:
            permits_text = "\n\nNearby registered sites:\n" + "\n".join(
                f"- {p.operator_name} ({p.registration_type}) at {p.site_address or 'Unknown'}, "
                f"Distance: {p.distance_km:.2f}km"
                for p in permits
            )

        print("Anomalies text for LLM:", anomalies_text)
        if permits_text:
            print("Permits text:", permits_text)

        prompt = (
            "You are an internal environmental risk analyst.\n"
            "CRITICAL: Base your analysis ONLY on the data provided below. "
            "Do NOT make assumptions or add information not present in the data.\n\n"
            "Analyze these environmental anomalies and generate alerts.\n"
            "Each reading includes: Source (data type), Station ID, Timestamp, and Value.\n\n"
            f"{anomalies_text}\n"
            f"{permits_text}\n\n"
            "For each alert:\n"
            "- Summarize ONLY what is observable from the provided anomaly data\n"
            "- Consider the Source type (e.g., 'flood' for water levels, 'hydrology' for flows)\n"
            "- Assess priority (high, medium, or low) based solely on the values and "
            "patterns shown\n"
            "- Suggest actions that directly relate to the specific stations and "
            "readings provided\n"
            "- Reference specific source types, station IDs, timestamps, and values\n"
            "- Do not speculate about causes or conditions not evident in the data"
        )

        response = cast(AlertsResponse, await self._llm.ainvoke(prompt))

        print("LLM response:", response)

        alerts: list[Alert] = []
        for alert_schema in response.alerts:
            priority_str = alert_schema.priority.lower()

            if priority_str in AlertPriority._value2member_map_:  # noqa: SLF001
                priority = AlertPriority(priority_str)
            else:
                priority = AlertPriority.MEDIUM

            alerts.append(
                Alert(
                    summary=alert_schema.summary,
                    priority=priority,
                    suggested_actions=alert_schema.suggested_actions,
                ),
            )
        return alerts
