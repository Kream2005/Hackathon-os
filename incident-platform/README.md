# Incident & On-Call Management Platform

A production-ready incident management and on-call platform built with microservices architecture, Docker Compose orchestration, and full DevOps automation.

## Architecture

```
                    ┌──────────────┐
                    │   Web UI     │ :3001
                    │ (React+Nginx)│
                    └──────┬───────┘
                           │ /api/* proxy
                    ┌──────┴───────┐
                    │ API Gateway  │ :8080
                    │  (FastAPI)   │
                    └──────┬───────┘
         ┌─────────────────┼─────────────────┐
         │                 │                  │
         ▼                 ▼                  ▼
┌─────────────────┐ ┌──────────────┐ ┌──────────────────┐
│ Alert Ingestion │ │  Incident    │ │  On-Call &        │
│   Service       │ │  Management  │ │  Escalation       │
│   :8001         │ │  :8002       │ │  :8003            │
└────────┬────────┘ └──────┬───────┘ └──────────────────┘
         │                 │                  │
         │                 ▼                  │
         │         ┌──────────────┐           │
         │         │ Notification │           │
         │         │  Service     │           │
         │         │  :8004       │           │
         │         └──────────────┘           │
         │                                    │
         ▼                                    ▼
┌─────────────────────────────────────────────────────┐
│                PostgreSQL :5432                       │
└─────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────┐     ┌──────────────┐
│  Prometheus  │────▶│   Grafana    │
│  :9090       │     │   :3000      │
└──────────────┘     └──────────────┘
```

### Services

| Service              | Port | Tech               | Description                    |
| -------------------- | ---- | ------------------ | ------------------------------ |
| Alert Ingestion      | 8001 | Python FastAPI     | Receives & correlates alerts   |
| Incident Management  | 8002 | Python FastAPI     | Incident lifecycle & MTTA/MTTR |
| On-Call Service      | 8003 | Python FastAPI     | Schedules & escalation         |
| Notification Service | 8004 | Python FastAPI     | Mock notification delivery     |
| API Gateway          | 8080 | Python FastAPI     | Auth, rate-limiting, proxy     |
| Web UI               | 3001 | React + Vite + Nginx | Dashboard & incident mgmt    |
| PostgreSQL           | 5432 | postgres:15-alpine | Persistent data store          |
| Prometheus           | 9090 | prom/prometheus    | Metrics collection             |
| Grafana              | 3000 | grafana/grafana    | Metrics dashboards             |

## Quick Start

```bash
# Clone
git clone <repo-url>
cd incident-platform

# Start everything (single command)
docker compose up -d --build

# Wait ~30 seconds for all services to initialize
```

## Verify

```bash
curl http://localhost:8001/health   # Alert Ingestion
curl http://localhost:8002/health   # Incident Management
curl http://localhost:8003/health   # On-Call Service
curl http://localhost:8004/health   # Notification Service
curl http://localhost:8080/health   # Web UI
```

## Send Test Alert

```bash
curl -X POST http://localhost:8001/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "service": "frontend-api",
    "severity": "high",
    "message": "HTTP 5xx error rate > 10%",
    "labels": {"env": "production"}
  }'
```

## Access

| Service        | URL                      | Credentials   |
| -------------- | ------------------------ | ------------- |
| **Web UI**     | http://localhost:3001     | admin / admin |
| **API Gateway**| http://localhost:8080     | API key header|
| **Grafana**    | http://localhost:3000     | admin / admin |
| **Prometheus** | http://localhost:9090     | -             |

## CI/CD Pipeline

```bash
chmod +x run-pipeline.sh
./run-pipeline.sh
```

**8 stages:** Code Quality → Security Scan → Tests & Coverage → Build Images → Image Vulnerability Scan → Deploy → Post-Deploy Verification → Integration Tests (E2E)

## API Documentation

### Alert Ingestion Service (port 8001)

| Method | Endpoint              | Description                        |
| ------ | --------------------- | ---------------------------------- |
| POST   | `/api/v1/alerts`      | Ingest a new alert                 |
| GET    | `/api/v1/alerts`      | List alerts (paginated, filterable)|
| GET    | `/api/v1/alerts/{id}` | Get alert by UUID                  |
| GET    | `/health`             | Liveness probe                     |
| GET    | `/health/ready`       | Readiness probe (DB connectivity)  |
| GET    | `/metrics`            | Prometheus-format metrics          |

**POST /api/v1/alerts** request body:
```json
{
  "service": "frontend-api",
  "severity": "high",
  "message": "HTTP 5xx error rate > 10%",
  "labels": {"env": "production"},
  "timestamp": "2026-02-09T15:30:00Z"
}
```
Severities: `critical`, `high`, `medium`, `low`

### Incident Management Service (port 8002)

| Method | Endpoint                           | Description                              |
| ------ | ---------------------------------- | ---------------------------------------- |
| POST   | `/api/v1/incidents`                | Create incident                          |
| GET    | `/api/v1/incidents`                | List incidents (paginated)               |
| GET    | `/api/v1/incidents/{id}`           | Get full incident (alerts, notes, timeline) |
| PATCH  | `/api/v1/incidents/{id}`           | Update status / assign / add note        |
| GET    | `/api/v1/incidents/{id}/metrics`   | MTTA & MTTR for one incident             |
| GET    | `/api/v1/incidents/stats/summary`  | Aggregate stats across all incidents     |
| GET    | `/health`                          | Liveness probe                           |
| GET    | `/health/ready`                    | Readiness probe (DB connectivity)        |
| GET    | `/metrics`                         | Prometheus-format metrics                |

**Status State Machine:**
```
open ──▶ acknowledged ──▶ in_progress ──▶ resolved
  │           │                              ▲
  │           └──────────────────────────────┘
  └──────────────────────────────────────────┘
```
Illegal transitions (e.g. `resolved → open`) return **HTTP 409 Conflict**.

**PATCH /api/v1/incidents/{id}** — Acknowledge/Resolve:
```json
{"status": "acknowledged"}
{"status": "resolved", "notes": "Fixed the root cause"}
```

### On-Call & Escalation Service (port 8003)

| Method | Endpoint                              | Description          |
| ------ | ------------------------------------- | -------------------- |
| POST   | `/api/v1/schedules`                   | Create schedule      |
| GET    | `/api/v1/schedules`                   | List schedules       |
| GET    | `/api/v1/oncall/current?team={team}`  | Current on-call      |
| POST   | `/api/v1/escalate`                    | Trigger escalation   |
| GET    | `/health`                             | Health check         |
| GET    | `/metrics`                            | Prometheus metrics   |

### Notification Service (port 8004)

| Method | Endpoint               | Description          |
| ------ | ---------------------- | -------------------- |
| POST   | `/api/v1/notify`       | Send notification    |
| GET    | `/api/v1/notifications`| List notifications   |
| GET    | `/health`              | Health check         |
| GET    | `/metrics`             | Prometheus metrics   |

## Database Schema

Key tables in `database/init.sql`:

| Table               | Purpose                                          |
| ------------------- | ------------------------------------------------ |
| `alerts`            | Raw alerts with fingerprint-based dedup          |
| `incidents`         | Incident lifecycle with status state machine     |
| `incident_notes`    | Timestamped notes attached to incidents          |
| `incident_timeline` | Immutable audit log of every incident event      |

## Prometheus Metrics

| Metric                                        | Type      | Service             |
| --------------------------------------------- | --------- | ------------------- |
| `alerts_received_total{severity}`             | Counter   | Alert Ingestion     |
| `alerts_correlated_total{result}`             | Counter   | Alert Ingestion     |
| `alert_processing_seconds`                    | Histogram | Alert Ingestion     |
| `incidents_created_total{severity}`           | Counter   | Incident Management |
| `incidents_by_status{status}`                 | Gauge     | Incident Management |
| `incident_mtta_seconds`                       | Histogram | Incident Management |
| `incident_mttr_seconds`                       | Histogram | Incident Management |
| `oncall_notifications_sent_total{channel}`    | Counter   | On-Call Service     |
| `escalations_total{team}`                     | Counter   | On-Call Service     |
| `notifications_sent_total{channel,status}`    | Counter   | Notification Service|

## Grafana Dashboards

1. **Live Incident Overview** — Open incidents, MTTA/MTTR gauges, alerts over time, top noisy services
2. **SRE Performance Metrics** — MTTA/MTTR trends, incident volume, acknowledgment/resolution distributions
3. **System Health Dashboard** — Service availability (up/down), request rates, scrape durations

## End-to-End Flow

1. Alert received via `POST /api/v1/alerts`
2. Alert Ingestion correlates (same service + severity + 5min window = existing incident)
3. If new → creates incident via Incident Management
4. Incident Management looks up on-call engineer via On-Call Service
5. Notification sent via Notification Service
6. Engineer opens Web UI → sees incident → clicks Acknowledge → clicks Resolve
7. MTTA and MTTR automatically calculated
8. All metrics exposed to Prometheus → visualized in Grafana

## Running Tests

```bash
# Alert Ingestion tests (~30 tests)
cd services/alert-ingestion && pip install -r requirements.txt && pytest -v test_main.py

# Incident Management tests (~30 tests)
cd services/incident-management && pip install -r requirements.txt && pytest -v test_main.py
```

## Team

- **Person 1**: Backend Services (Alert Ingestion, Incident Management, Database)
- **Person 2**: DevOps & Infrastructure (On-Call Service, CI/CD, Monitoring)
- **Person 3**: Frontend & Integration (Web UI, Notification Service, Documentation)

## Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, Pydantic v2
- **Database**: PostgreSQL 15 with pgcrypto
- **Frontend**: React 18, Vite 6, TypeScript, Tailwind CSS, Recharts
- **Web Server**: Nginx (Alpine) with reverse proxy
- **Monitoring**: Prometheus + Grafana
- **Orchestration**: Docker Compose
- **CI/CD**: Shell script pipeline (8 stages)
