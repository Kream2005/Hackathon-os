-- ==========================================================
-- Incident Management Service — Dedicated Database
-- Owned exclusively by the incident-management microservice.
-- ==========================================================
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS incidents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           VARCHAR(500)  NOT NULL,
    service         VARCHAR(255)  NOT NULL,
    severity        VARCHAR(20)   NOT NULL
                        CHECK (severity IN ('critical','high','medium','low')),
    status          VARCHAR(20)   NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open','acknowledged','in_progress','resolved')),
    assigned_to     VARCHAR(255),
    alert_count     INTEGER       NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ,
    resolved_at     TIMESTAMPTZ,
    mtta_seconds    DOUBLE PRECISION,
    mttr_seconds    DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS incident_notes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID          NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    author      VARCHAR(255)  NOT NULL DEFAULT 'system',
    content     TEXT          NOT NULL,
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS incident_timeline (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID          NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    event_type  VARCHAR(50)   NOT NULL
                    CHECK (event_type IN (
                        'created','acknowledged','in_progress','resolved',
                        'reopened','assigned','escalated','note_added','alert_correlated'
                    )),
    actor       VARCHAR(255)  NOT NULL DEFAULT 'system',
    detail      JSONB         DEFAULT '{}',
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE incidents IS 'Core incident records — owned by incident-management service';
COMMENT ON TABLE incident_notes IS 'Timestamped notes attached to incidents';
COMMENT ON TABLE incident_timeline IS 'Immutable audit log of every incident event';

CREATE INDEX IF NOT EXISTS idx_incidents_status          ON incidents (status);
CREATE INDEX IF NOT EXISTS idx_incidents_service         ON incidents (service);
CREATE INDEX IF NOT EXISTS idx_incidents_severity        ON incidents (severity);
CREATE INDEX IF NOT EXISTS idx_incidents_created_at      ON incidents (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_incidents_status_severity ON incidents (status, severity);
CREATE INDEX IF NOT EXISTS idx_incidents_correlation
    ON incidents (service, severity, created_at DESC)
    WHERE status != 'resolved';
CREATE INDEX IF NOT EXISTS idx_incident_notes_incident   ON incident_notes (incident_id, created_at);
CREATE INDEX IF NOT EXISTS idx_timeline_incident         ON incident_timeline (incident_id, created_at);

CREATE OR REPLACE FUNCTION fn_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_incidents_updated_at ON incidents;
CREATE TRIGGER trg_incidents_updated_at
    BEFORE UPDATE ON incidents
    FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();
