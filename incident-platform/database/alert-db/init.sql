-- ==========================================================
-- Alert Ingestion Service — Dedicated Database
-- Owned exclusively by the alert-ingestion microservice.
-- ==========================================================
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS alerts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service     VARCHAR(255)  NOT NULL,
    severity    VARCHAR(20)   NOT NULL
                    CHECK (severity IN ('critical','high','medium','low')),
    message     TEXT          NOT NULL,
    source      VARCHAR(255)  DEFAULT 'api',
    labels      JSONB         NOT NULL DEFAULT '{}',
    fingerprint VARCHAR(64),
    timestamp   TIMESTAMPTZ   NOT NULL,
    incident_id UUID,
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE alerts IS 'Incoming alert signals — owned exclusively by alert-ingestion service';

CREATE INDEX IF NOT EXISTS idx_alerts_correlation
    ON alerts (service, severity, created_at DESC)
    WHERE incident_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_alerts_incident_id ON alerts (incident_id);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at  ON alerts (created_at DESC);
