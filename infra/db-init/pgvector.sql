CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS incident_embeddings (
    id UUID PRIMARY KEY,
    run_id TEXT,
    summary TEXT,
    embedding vector(1536)
);
