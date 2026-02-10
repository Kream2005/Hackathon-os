-- ============================================================
-- INCIDENT PLATFORM — DATABASE SCHEMA
-- Designed for a multi-service incident management platform.
-- Tables: incidents (core), alerts, incident_notes,
--         incident_timeline (audit trail for every state change)
-- ============================================================

-- Enable the pgcrypto extension (gen_random_uuid)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- -----------------------------------------------------------
-- 1. INCIDENTS  —  the central entity
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS incidents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           VARCHAR(500)  NOT NULL,
    service         VARCHAR(255)  NOT NULL,
    severity        VARCHAR(20)   NOT NULL
                        CHECK (severity IN ('critical','high','medium','low')),
    status          VARCHAR(20)   NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open','acknowledged','in_progress','resolved')),
    assigned_to     VARCHAR(255),
    alert_count     INTEGER       NOT NULL DEFAULT 0,      -- denormalised for fast dashboard reads
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ,
    resolved_at     TIMESTAMPTZ,
    mtta_seconds    DOUBLE PRECISION,                       -- Mean-Time-To-Acknowledge
    mttr_seconds    DOUBLE PRECISION                        -- Mean-Time-To-Resolve
);

COMMENT ON TABLE  incidents              IS 'Core incident records with lifecycle timestamps';
COMMENT ON COLUMN incidents.alert_count  IS 'Denormalised count of correlated alerts';
COMMENT ON COLUMN incidents.mtta_seconds IS 'Seconds between created_at and acknowledged_at';
COMMENT ON COLUMN incidents.mttr_seconds IS 'Seconds between created_at and resolved_at';

-- -----------------------------------------------------------
-- 2. ALERTS  —  raw signals correlated into incidents
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS alerts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service     VARCHAR(255)  NOT NULL,
    severity    VARCHAR(20)   NOT NULL
                    CHECK (severity IN ('critical','high','medium','low')),
    message     TEXT          NOT NULL,
    source      VARCHAR(255)  DEFAULT 'api',               -- origin system (prometheus, grafana, api…)
    labels      JSONB         NOT NULL DEFAULT '{}',
    fingerprint VARCHAR(64),                                -- optional dedup key
    timestamp   TIMESTAMPTZ   NOT NULL,
    incident_id UUID          REFERENCES incidents(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  alerts             IS 'Incoming alert signals from monitoring systems';
COMMENT ON COLUMN alerts.fingerprint IS 'SHA-256 based dedup key (service+severity+message hash)';

-- -----------------------------------------------------------
-- 3. INCIDENT NOTES  —  human / system annotations
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS incident_notes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID          NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    author      VARCHAR(255)  NOT NULL DEFAULT 'system',
    content     TEXT          NOT NULL,
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------
-- 4. INCIDENT TIMELINE  —  immutable audit log of every event
-- -----------------------------------------------------------
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

COMMENT ON TABLE incident_timeline IS 'Immutable event log for every incident state change';

-- -----------------------------------------------------------
-- 5. NOTIFICATIONS  —  persistent notification delivery log
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id VARCHAR(255)  NOT NULL,
    channel     VARCHAR(50)   NOT NULL DEFAULT 'mock'
                    CHECK (channel IN ('mock','email','slack','webhook')),
    recipient   VARCHAR(500)  NOT NULL,
    message     TEXT          NOT NULL,
    severity    VARCHAR(20),
    status      VARCHAR(20)   NOT NULL DEFAULT 'sent'
                    CHECK (status IN ('sent','failed')),
    metadata    JSONB         DEFAULT '{}',
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE notifications IS 'Persistent audit log of every notification delivered by the platform';

-- -----------------------------------------------------------
-- INDEXES  —  covering the hot-path queries
-- -----------------------------------------------------------

-- Alert correlation: find open incident for same service+severity in last 5 min
CREATE INDEX IF NOT EXISTS idx_alerts_correlation
    ON alerts (service, severity, created_at DESC)
    WHERE incident_id IS NOT NULL;

-- Incident listing / dashboard filters
CREATE INDEX IF NOT EXISTS idx_incidents_status          ON incidents (status);
CREATE INDEX IF NOT EXISTS idx_incidents_service         ON incidents (service);
CREATE INDEX IF NOT EXISTS idx_incidents_severity        ON incidents (severity);
CREATE INDEX IF NOT EXISTS idx_incidents_created_at      ON incidents (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_incidents_status_severity  ON incidents (status, severity);

-- Correlation lookup: open incidents for a given service+severity in time window
CREATE INDEX IF NOT EXISTS idx_incidents_correlation
    ON incidents (service, severity, created_at DESC)
    WHERE status != 'resolved';

-- Alert → incident join
CREATE INDEX IF NOT EXISTS idx_alerts_incident_id        ON alerts (incident_id);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at         ON alerts (created_at DESC);

-- Notes & timeline fast lookups
CREATE INDEX IF NOT EXISTS idx_incident_notes_incident   ON incident_notes (incident_id, created_at);
CREATE INDEX IF NOT EXISTS idx_timeline_incident         ON incident_timeline (incident_id, created_at);

-- Notification lookups
CREATE INDEX IF NOT EXISTS idx_notifications_incident    ON notifications (incident_id);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at  ON notifications (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_channel     ON notifications (channel);
CREATE INDEX IF NOT EXISTS idx_notifications_status      ON notifications (status);

-- -----------------------------------------------------------
-- FUNCTION: auto-update updated_at on incidents
-- -----------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_incidents_updated_at
    BEFORE UPDATE ON incidents
    FOR EACH ROW
    EXECUTE FUNCTION fn_set_updated_at();
