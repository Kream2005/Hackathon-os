-- ============================================
-- INCIDENT PLATFORM DATABASE SCHEMA
-- ============================================

-- Alerts table
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service VARCHAR(255) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('critical','high','medium','low')),
    message TEXT NOT NULL,
    labels JSONB DEFAULT '{}',
    timestamp TIMESTAMPTZ NOT NULL,
    incident_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Incidents table
CREATE TABLE IF NOT EXISTS incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    service VARCHAR(255) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('critical','high','medium','low')),
    status VARCHAR(20) DEFAULT 'open' CHECK (status IN ('open','acknowledged','in_progress','resolved')),
    assigned_to VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    mtta_seconds FLOAT,
    mttr_seconds FLOAT
);

-- Incident notes table
CREATE TABLE IF NOT EXISTS incident_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID REFERENCES incidents(id) ON DELETE CASCADE,
    author VARCHAR(255),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add foreign key for alerts -> incidents
ALTER TABLE alerts
    ADD CONSTRAINT fk_alerts_incident
    FOREIGN KEY (incident_id) REFERENCES incidents(id) ON DELETE SET NULL;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_alerts_service_severity ON alerts(service, severity);
CREATE INDEX IF NOT EXISTS idx_alerts_incident_id ON alerts(incident_id);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_service ON incidents(service);
CREATE INDEX IF NOT EXISTS idx_incidents_created_at ON incidents(created_at);
CREATE INDEX IF NOT EXISTS idx_incident_notes_incident_id ON incident_notes(incident_id);
