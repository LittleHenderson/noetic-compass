-- 001_create_assessments.sql
-- Creates the assessments table for persistent assessment storage.

CREATE TABLE IF NOT EXISTS assessments (
    id            UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    api_key       VARCHAR(255)    NOT NULL,
    timestamp     TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    text          TEXT            NOT NULL,
    response      JSONB           NOT NULL,
    created_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assessments_api_key_ts
    ON assessments (api_key, timestamp DESC);
