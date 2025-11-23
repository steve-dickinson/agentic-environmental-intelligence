import uuid
from typing import Any

import psycopg2
from langchain_openai import OpenAIEmbeddings
from pgvector.psycopg2 import register_vector
from pydantic import SecretStr

from defra_agent.config import settings
from defra_agent.domain.models import Incident


class SimilarIncident:
    """Represents a similar incident found via vector similarity search."""

    def __init__(
        self,
        incident_id: str,
        summary: str,
        similarity: float,
    ) -> None:
        self.incident_id = incident_id
        self.summary = summary
        self.similarity = similarity

    def __repr__(self) -> str:
        return f"SimilarIncident(id={self.incident_id}, similarity={self.similarity:.3f})"


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
        """Store incident alert summaries as embeddings in pgvector.
        
        Skips if incident already has embeddings to avoid duplicates.

        Args:
            incident: Incident with alerts to embed
        """
        if not incident.alerts:
            return

        conn = self._get_connection()
        cur = conn.cursor()
        
        # Check if this incident already has embeddings
        cur.execute(
            "SELECT COUNT(*) FROM incident_embeddings WHERE run_id = %s",
            (incident.id,)
        )
        existing_count = cur.fetchone()[0]
        
        if existing_count > 0:
            # Already indexed, skip
            cur.close()
            conn.close()
            return

        texts = [alert.summary for alert in incident.alerts]
        vectors = self._embeddings.embed_documents(texts)

        for summary, embedding in zip(texts, vectors, strict=True):
            cur.execute(
                """
                INSERT INTO incident_embeddings (id, run_id, summary, embedding)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (str(uuid.uuid4()), incident.id, summary, embedding),
            )

        conn.commit()
        cur.close()
        conn.close()

    def find_similar_incidents(
        self,
        query_text: str,
        limit: int = 5,
        similarity_threshold: float = 0.7,
    ) -> list[SimilarIncident]:
        """Find similar historical incidents using vector similarity search.

        Uses cosine similarity (1 - cosine distance) to find semantically similar
        incident summaries.

        Args:
            query_text: Text to search for (e.g., current incident summary)
            limit: Maximum number of results to return
            similarity_threshold: Minimum similarity score (0-1) to include

        Returns:
            List of SimilarIncident objects, sorted by similarity (highest first)

        Example:
            >>> repo = IncidentVectorRepository()
            >>> similar = repo.find_similar_incidents(
            ...     "Elevated river levels in Somerset Levels",
            ...     limit=3,
            ...     similarity_threshold=0.75
            ... )
            >>> for incident in similar:
            ...     print(f"{incident.similarity:.2f}: {incident.summary[:50]}")
            0.89: Elevated river levels at 2 stations in Somerset...
            0.76: Flood risk detected in Gloucestershire area...
        """
        # Generate embedding for query text
        query_vector = self._embeddings.embed_query(query_text)

        conn = self._get_connection()
        cur = conn.cursor()

        # Use pgvector's cosine distance operator (<=>)
        # cosine similarity = 1 - cosine distance
        cur.execute(
            """
            SELECT 
                run_id,
                summary,
                1 - (embedding <=> %s::vector) as similarity
            FROM incident_embeddings
            WHERE 1 - (embedding <=> %s::vector) >= %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (query_vector, query_vector, similarity_threshold, query_vector, limit),
        )

        results = []
        for row in cur.fetchall():
            incident_id, summary, similarity = row
            results.append(
                SimilarIncident(
                    incident_id=incident_id,
                    summary=summary,
                    similarity=float(similarity),
                )
            )

        cur.close()
        conn.close()

        return results

    def find_similar_to_incident(
        self,
        incident: Incident,
        limit: int = 5,
        similarity_threshold: float = 0.7,
    ) -> list[SimilarIncident]:
        """Find incidents similar to a given incident.

        Convenience method that uses the incident's first alert summary as the query.

        Args:
            incident: Incident to find similar matches for
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score

        Returns:
            List of similar incidents (excluding the query incident itself)
        """
        if not incident.alerts:
            return []

        query_text = incident.alerts[0].summary
        similar = self.find_similar_incidents(query_text, limit + 1, similarity_threshold)

        # Filter out the query incident itself
        return [s for s in similar if s.incident_id != incident.id][:limit]
