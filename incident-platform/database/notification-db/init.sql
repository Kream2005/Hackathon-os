-- ==========================================================
-- Notification Service — Dedicated Database
-- Owned exclusively by the notification-service microservice.
-- ==========================================================
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

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

COMMENT ON TABLE notifications IS 'Notification delivery log — owned by notification-service';

CREATE INDEX IF NOT EXISTS idx_notifications_incident   ON notifications (incident_id);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON notifications (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_channel    ON notifications (channel);
CREATE INDEX IF NOT EXISTS idx_notifications_status     ON notifications (status);
