import uuid
from typing import Any

import psycopg2
from langchain_openai import OpenAIEmbeddings
from pgvector.psycopg2 import register_vector
from pydantic import SecretStr

from defra_agent.config import settings
from defra_agent.domain.models import Incident


class IncidentVectorRepository:
    """Stores incident summaries as vectors for similarity search."""

    def __init__(self) -> None:
        self._dsn = settings.pg_dsn
        api_key = SecretStr(settings.openai_api_key) if settings.openai_api_key else None
        self._embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=api_key,
        )

    def _get_connection(self) -> Any:
        conn = psycopg2.connect(self._dsn)
        register_vector(conn)
        return conn

    def store_incident(self, incident: Incident) -> None:
        if not incident.alerts:
            return

        texts = [alert.summary for alert in incident.alerts]
        vectors = self._embeddings.embed_documents(texts)

        conn = self._get_connection()
        cur = conn.cursor()

        for summary, embedding in zip(texts, vectors, strict=True):
            cur.execute(
                """
                INSERT INTO incident_embeddings (id, run_id, summary, embedding)
                VALUES (%s, %s, %s, %s)
                """,
                (str(uuid.uuid4()), incident.id, summary, embedding),
            )

        conn.commit()
        cur.close()
        conn.close()
