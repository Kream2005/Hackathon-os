# Incident & On-Call Management Platform

> A production-grade incident management and on-call platform built with true microservices architecture, database-per-service isolation, Docker Compose orchestration, and a full 8-stage CI/CD pipeline.

**Hackathon DevOps & Cloud 2026 — ENSA Khouribga**

---

## Table of Contents

- [Architecture](#architecture)
- [Services Overview](#services-overview)
- [Quick Start](#quick-start)
- [Environment Configuration](#environment-configuration)
- [Verify Deployment](#verify-deployment)
- [End-to-End Flow](#end-to-end-flow)
- [API Reference](#api-reference)
- [Database Schema](#database-schema)
- [Monitoring & Observability](#monitoring--observability)
- [CI/CD Pipeline](#cicd-pipeline)
- [Running Tests](#running-tests)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Team](#team)

---

## Architecture

```
                        ┌──────────────────┐
                        │     Web UI       │ :3001
                        │  React + Nginx   │
                        └────────┬─────────┘
                                 │ /api/* reverse proxy
                        ┌────────┴─────────┐
                        │   API Gateway    │ :8080
                        │ Auth · Rate-Limit│
                        │  Retry · Proxy   │
                        └────────┬─────────┘
              ┌──────────────────┼──────────────────┐
              │                  │                   │
              ▼                  ▼                   ▼
   ┌─────────────────┐ ┌────────────────┐ ┌─────────────────┐
   │ Alert Ingestion │ │   Incident     │ │  On-Call &       │
   │   :8001         │ │   Management   │ │  Escalation      │
   │                 │ │   :8002        │ │   :8003          │
   └────────┬────────┘ └───────┬────────┘ └────────┬────────┘
            │                  │                    │
            │                  ▼                    │
            │          ┌────────────────┐           │
            │          │  Notification  │           │
            │          │   Service      │           │
            │          │   :8004        │           │
            │          └───────┬────────┘           │
            │                  │                    │
            ▼                  ▼                    │
   ┌──────────────┐  ┌──────────────┐              │
   │   alert-db   │  │ incident-db  │              │
   │  PostgreSQL  │  │  PostgreSQL  │  (in-memory) │
   └──────────────┘  └──────────────┘              │
                     ┌──────────────┐              │
                     │notification-db│              │
                     │  PostgreSQL  │──────────────┘
                     └──────────────┘

   ┌──────────────┐      ┌──────────────┐
   │  Prometheus  │─────▶│   Grafana    │
   │   :9090      │      │   :3000      │
   └──────────────┘      └──────────────┘
```

**Key architectural decisions:**

- **Database-per-service** — 3 separate PostgreSQL 15 containers with physical data isolation (no cross-DB queries possible)
- **API Gateway pattern** — single entry point with authentication, rate limiting (120 RPM/IP), and automatic retry with exponential backoff
- **Event-driven correlation** — incoming alerts are fingerprinted and auto-correlated into existing incidents within a configurable time window
- **Zero hardcoded credentials** — all secrets loaded from `.env` at runtime

---

## Services Overview

| Service | Port | Database | Description |
|---|---|---|---|
| **Alert Ingestion** | 8001 | `alert-db` (PostgreSQL) | Receives alerts, fingerprint dedup, correlation into incidents |
| **Incident Management** | 8002 | `incident-db` (PostgreSQL) | Full incident lifecycle, status state machine, MTTA/MTTR |
| **On-Call Service** | 8003 | In-memory | Schedules, rotations, overrides, escalation chains |
| **Notification Service** | 8004 | `notification-db` (PostgreSQL) | Multi-channel delivery (mock, email, slack, webhook) |
| **API Gateway** | 8080 | — | Auth, rate-limiting, reverse proxy, retry logic |
| **Web UI** | 3001 | — | React dashboard served by Nginx |
| **Prometheus** | 9090 | — | Metrics collection (scrapes all 5 services) |
| **Grafana** | 3000 | — | 3 pre-provisioned dashboards |

**Total: 11 containers** (5 application services + 3 databases + Prometheus + Grafana + Web UI)

---

## Quick Start

### Prerequisites

- **Docker** (with Docker Compose v2)
- **Git**

### 1. Clone the repository

```bash
git clone <repo-url>
cd incident-platform
```

### 2. Create the environment file

```bash
cp .env.example .env
```

Then edit `.env` and replace all `<CHANGE_ME>` placeholders. Example working values:

```env
POSTGRES_USER=hackathon
POSTGRES_PASSWORD=hackathon2026
API_KEYS=incident-platform-key-2026,dev-key-local
LOGIN_API_KEY=incident-platform-key-2026
AUTH_USERS=admin:admin,operator:operator
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin
```

### 3. Build and start everything

```bash
docker compose up -d --build
```

This builds 6 images and starts all 11 containers. Wait ~60 seconds for databases to initialize and health checks to pass.

### 4. Verify all services are healthy

```bash
docker compose ps
```

All 11 containers should show `(healthy)`.

### 5. Access the platform

| Service | URL | Credentials |
|---|---|---|
| **Web UI** | http://localhost:3001 | Login with credentials from `AUTH_USERS` in `.env` |
| **API Gateway** | http://localhost:8080 | `X-API-Key` header (value from `API_KEYS` in `.env`) |
| **Grafana** | http://localhost:3000 | Credentials from `GRAFANA_ADMIN_USER`/`GRAFANA_ADMIN_PASSWORD` in `.env` |
| **Prometheus** | http://localhost:9090 | No auth |

---

## Environment Configuration

All configuration is driven by the `.env` file. The `.env` file is **never committed** (listed in `.gitignore`).

| Variable | Description | Used By |
|---|---|---|
| `POSTGRES_USER` | PostgreSQL username (shared by all 3 DB containers) | alert-db, incident-db, notification-db |
| `POSTGRES_PASSWORD` | PostgreSQL password | alert-db, incident-db, notification-db |
| `API_KEYS` | Comma-separated API keys for gateway auth | api-gateway |
| `LOGIN_API_KEY` | Key returned to browser on successful login | api-gateway |
| `AUTH_USERS` | `user:pass` pairs, comma-separated | api-gateway |
| `GRAFANA_ADMIN_USER` | Grafana admin username | grafana |
| `GRAFANA_ADMIN_PASSWORD` | Grafana admin password | grafana |
| `RATE_LIMIT_RPM` | API rate limit (requests/min/IP), default `120` | api-gateway |
| `RETRY_MAX_ATTEMPTS` | Retry attempts for inter-service calls, default `2` | api-gateway |

Database URLs are **composed automatically** in `docker-compose.yml` from `POSTGRES_USER` and `POSTGRES_PASSWORD` — you do not need to set them manually.

---

## Verify Deployment

```bash
# Health checks
curl http://localhost:8001/health   # Alert Ingestion
curl http://localhost:8002/health   # Incident Management
curl http://localhost:8003/health   # On-Call Service
curl http://localhost:8004/health   # Notification Service
curl http://localhost:8080/health   # API Gateway

# Database isolation proof (each DB has only its own tables)
docker compose exec alert-db psql -U hackathon -d alert_db -c "\dt"
docker compose exec incident-db psql -U hackathon -d incident_db -c "\dt"
docker compose exec notification-db psql -U hackathon -d notification_db -c "\dt"
```

---

## End-to-End Flow

```
1. Alert received        POST /api/v1/alerts
                              │
2. Fingerprint + dedup        │  alert-ingestion computes SHA-256 fingerprint
                              │
3. Correlation                │  Same service + severity within 5min window?
                              │        ├─ YES → attach to existing incident
                              │        └─ NO  → create new incident
                              │
4. Auto-assignment            │  incident-management → oncall-service
                              │  Looks up the current primary on-call engineer
                              │
5. Notification               │  notification-service sends alert to assignee
                              │
6. Acknowledge/Resolve        │  Engineer uses Web UI or API
                              │  MTTA = acknowledged_at - created_at
                              │  MTTR = resolved_at - created_at
                              │
7. Metrics                    │  All steps emit Prometheus counters/histograms
                              └─ Grafana dashboards show real-time data
```

### Try it yourself

```bash
# 1. Send an alert (auto-creates an incident)
curl -s -X POST http://localhost:8001/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "service": "payment-api",
    "severity": "critical",
    "message": "HTTP 5xx error rate > 10%"
  }' | python3 -m json.tool

# 2. Send a duplicate (auto-correlates into the same incident)
curl -s -X POST http://localhost:8001/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "service": "payment-api",
    "severity": "critical",
    "message": "Connection pool exhausted"
  }' | python3 -m json.tool

# 3. List incidents (via API Gateway with auth)
curl -s http://localhost:8080/api/v1/incidents \
  -H "X-API-Key: <your-api-key>" | python3 -m json.tool

# 4. Acknowledge an incident
curl -s -X PATCH http://localhost:8002/api/v1/incidents/<incident-id> \
  -H "Content-Type: application/json" \
  -d '{"status": "acknowledged"}'

# 5. Resolve with a note
curl -s -X PATCH http://localhost:8002/api/v1/incidents/<incident-id> \
  -H "Content-Type: application/json" \
  -d '{"status": "resolved", "notes": "Root cause: connection pool leak in v2.3.1"}'
```

---

## API Reference

### Alert Ingestion Service (:8001)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/alerts` | Ingest a new alert |
| `GET` | `/api/v1/alerts` | List alerts (paginated, filterable) |
| `GET` | `/api/v1/alerts/{id}` | Get alert by UUID |
| `GET` | `/health` | Liveness probe |
| `GET` | `/health/ready` | Readiness probe (DB connectivity) |
| `GET` | `/metrics` | Prometheus metrics |

**POST /api/v1/alerts** request body:
```json
{
  "service": "frontend-api",
  "severity": "high",
  "message": "HTTP 5xx error rate > 10%",
  "labels": {"env": "production", "region": "us-east-1"},
  "timestamp": "2026-02-10T15:30:00Z"
}
```
Severities: `critical`, `high`, `medium`, `low`

### Incident Management Service (:8002)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/incidents` | Create incident |
| `GET` | `/api/v1/incidents` | List incidents (paginated) |
| `GET` | `/api/v1/incidents/{id}` | Full incident detail (alerts, notes, timeline) |
| `PATCH` | `/api/v1/incidents/{id}` | Update status / assign / add note |
| `GET` | `/api/v1/incidents/{id}/metrics` | MTTA & MTTR for one incident |
| `GET` | `/api/v1/incidents/stats/summary` | Aggregate stats across all incidents |
| `GET` | `/health` | Liveness probe |
| `GET` | `/health/ready` | Readiness probe |
| `GET` | `/metrics` | Prometheus metrics |

**Status State Machine:**
```
open ──► acknowledged ──► in_progress ──► resolved
  │           │                              ▲
  │           └──────────────────────────────┘
  └──────────────────────────────────────────┘
```
Illegal transitions (e.g. `resolved → open`) return **HTTP 409 Conflict**.

### On-Call & Escalation Service (:8003)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/schedules` | Create on-call schedule |
| `GET` | `/api/v1/schedules` | List all schedules |
| `GET` | `/api/v1/schedules/{team}` | Get team schedule |
| `PATCH` | `/api/v1/schedules/{team}` | Update team schedule |
| `DELETE` | `/api/v1/schedules/{team}` | Delete team schedule |
| `GET` | `/api/v1/oncall/current?team={team}` | Current on-call engineer |
| `POST` | `/api/v1/oncall/override` | Set temporary override |
| `DELETE` | `/api/v1/oncall/override/{team}` | Remove override |
| `GET` | `/api/v1/oncall/overrides` | List active overrides |
| `POST` | `/api/v1/escalate` | Trigger escalation |
| `GET` | `/api/v1/escalations` | Escalation history |
| `GET` | `/api/v1/oncall/history` | Audit log |
| `GET` | `/api/v1/teams` | All teams overview |
| `GET` | `/api/v1/oncall/stats` | Operational statistics |
| `GET` | `/health` | Health check |
| `GET` | `/metrics` | Prometheus metrics |

### Notification Service (:8004)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/notify` | Send notification |
| `GET` | `/api/v1/notifications` | List all notifications |
| `GET` | `/health` | Health check |
| `GET` | `/health/ready` | Readiness probe |
| `GET` | `/metrics` | Prometheus metrics |

Channels: `mock`, `email`, `slack`, `webhook`

### API Gateway (:8080)

All backend endpoints are accessible through the gateway at `/api/v1/*`. The gateway adds:

- **Authentication** — `X-API-Key` header required (keys from `API_KEYS` env var)
- **Login** — `POST /api/v1/auth/login` with `{"username":"...","password":"..."}` returns an API key
- **Rate limiting** — sliding window, 120 req/min per IP (configurable)
- **Automatic retry** — failed upstream calls retried with exponential backoff
- **Health aggregation** — `GET /api/services/health` returns all backend statuses

---

## Database Schema

Each service owns its database exclusively — no cross-service queries.

### alert-db (alert_db)

| Table | Description |
|---|---|
| `alerts` | Raw alert signals with fingerprint-based deduplication |

Key columns: `id`, `service`, `severity`, `message`, `fingerprint` (SHA-256), `incident_id`, `labels` (JSONB)

### incident-db (incident_db)

| Table | Description |
|---|---|
| `incidents` | Core incident records with status state machine |
| `incident_notes` | Timestamped notes attached to incidents |
| `incident_timeline` | Immutable audit log of every event |

Key columns: `status`, `assigned_to`, `acknowledged_at`, `resolved_at`, `mtta_seconds`, `mttr_seconds`

Includes an `updated_at` trigger that auto-updates on every row change.

### notification-db (notification_db)

| Table | Description |
|---|---|
| `notifications` | Delivery log with channel, recipient, status |

Key columns: `incident_id`, `channel`, `recipient`, `status` (sent/failed), `metadata` (JSONB)

All databases use `pgcrypto` for UUID generation and include performance indexes on common query patterns.

---

## Monitoring & Observability

### Prometheus Metrics

| Metric | Type | Service |
|---|---|---|
| `alerts_received_total{severity}` | Counter | Alert Ingestion |
| `alerts_correlated_total{result}` | Counter | Alert Ingestion |
| `alert_processing_seconds` | Histogram | Alert Ingestion |
| `incidents_created_total{severity}` | Counter | Incident Management |
| `incidents_total{status}` | Gauge | Incident Management |
| `incident_mtta_seconds` | Histogram | Incident Management |
| `incident_mttr_seconds` | Histogram | Incident Management |
| `oncall_escalations_total{team}` | Counter | On-Call Service |
| `oncall_notifications_sent_total{channel}` | Counter | On-Call Service |
| `oncall_active_schedules` | Gauge | On-Call Service |
| `oncall_lookups_total{team}` | Counter | On-Call Service |
| `notifications_sent_total{channel,status}` | Counter | Notification Service |
| `notification_processing_seconds` | Histogram | Notification Service |

Prometheus scrapes all 5 application services every 10–15 seconds.

### Grafana Dashboards (pre-provisioned)

1. **Incident Overview** — Open incidents, MTTA/MTTR gauges, alerts over time, top noisy services
2. **SRE Performance** — MTTA/MTTR trends, escalation totals, notification volumes, incident breakdown by severity
3. **System Health** — Service uptime (up/down), request rates, active schedules, on-call lookups by team

Dashboards are auto-provisioned via `monitoring/grafana-provisioning/` — no manual setup needed.

---

## CI/CD Pipeline

Run the full 8-stage pipeline:

```bash
bash ci/pipeline.sh
```

| Stage | Script | Description |
|---|---|---|
| 1 | `quality.sh` | Code quality — Python linting (pyflakes, syntax checks) |
| 2 | `security.sh` | Secret scanning (gitleaks), dependency audit |
| 3 | `test.sh` | Unit tests + coverage (≥60% threshold) across 5 services |
| 4 | `build.sh` | Docker image builds for all services |
| 5 | `scan.sh` | Container image vulnerability scanning |
| 6 | `deploy.sh` | `docker compose up -d` with health-check gate + auto-rollback |
| 7 | `verify.sh` | Post-deploy verification: health, DB connectivity, E2E smoke tests |
| 8 | `integration-test.sh` | Full E2E integration tests (19 checks) including Grafana/Prometheus |

Additional scripts:
- `deploy-local.sh` — Interactive local deployment with smoke tests
- `ci/rollback.sh` — Automatic rollback to previous image tags on failure
- `run-pipeline.sh` — Shortcut to run the full pipeline

---

## Running Tests

### All tests (254 total)

```bash
# Via CI pipeline (includes coverage enforcement)
bash ci/test.sh

# Or individually via Docker
docker compose exec alert-ingestion python -m pytest test_main.py -v       # 29 tests
docker compose exec incident-management python -m pytest test_main.py -v   # 36 tests
docker compose exec notification-service python -m pytest test_main.py -v  # 61 tests
docker compose exec oncall-service python -m pytest test_main.py -v        # 101 tests
docker compose exec api-gateway python -m pytest test_main.py -v           # 27 tests
```

### Locally (requires Python 3.11+)

```bash
pip install pytest pytest-cov httpx fastapi uvicorn prometheus-client pydantic sqlalchemy anyio
source .env   # Load credentials
cd services/alert-ingestion && pytest test_main.py -v
```

Coverage threshold: **60%** (enforced by CI).

---

## Project Structure

```
incident-platform/
├── .env.example                 # Environment template (copy to .env)
├── .gitignore                   # Ignores .env, __pycache__, node_modules, etc.
├── .gitleaks.toml               # Secret scanning configuration
├── docker-compose.yml           # 11 containers orchestration
├── deploy-local.sh              # Interactive local CD script
├── run-pipeline.sh              # Pipeline shortcut
│
├── ci/                          # CI/CD pipeline (8 stages)
│   ├── pipeline.sh              # Main orchestrator
│   ├── quality.sh               # Stage 1: Linting
│   ├── security.sh              # Stage 2: Secret scan
│   ├── test.sh                  # Stage 3: Tests + coverage
│   ├── build.sh                 # Stage 4: Docker builds
│   ├── scan.sh                  # Stage 5: Image vulnerability scan
│   ├── deploy.sh                # Stage 6: Deploy with rollback
│   ├── verify.sh                # Stage 7: Post-deploy verification
│   ├── integration-test.sh      # Stage 8: E2E integration tests
│   ├── rollback.sh              # Automatic rollback
│   └── setup-hooks.sh           # Git hooks setup
│
├── database/                    # Database-per-service init scripts
│   ├── alert-db/init.sql        # alerts table + indexes
│   ├── incident-db/init.sql     # incidents, notes, timeline + triggers
│   └── notification-db/init.sql # notifications table + indexes
│
├── monitoring/
│   ├── prometheus.yml           # Scrape config (7 targets)
│   ├── grafana-dashboards/      # 3 JSON dashboard definitions
│   └── grafana-provisioning/    # Auto-provisioning for datasources + dashboards
│
└── services/
    ├── alert-ingestion/         # Python FastAPI — 508 LOC, 29 tests
    ├── incident-management/     # Python FastAPI — 778 LOC, 36 tests
    ├── oncall-service/          # Python FastAPI — 1099 LOC, 101 tests
    ├── notification-service/    # Python FastAPI — 556 LOC, 61 tests
    ├── api-gateway/             # Python FastAPI — 378 LOC, 27 tests
    └── web-ui/                  # React + Vite + TypeScript + Tailwind + Nginx
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.11, FastAPI, Pydantic v2, SQLAlchemy, httpx |
| **Frontend** | React 18, Vite 6, TypeScript, Tailwind CSS, Recharts, Lucide React |
| **Databases** | 3× PostgreSQL 15 Alpine (with pgcrypto, physical isolation) |
| **Web Server** | Nginx Alpine (serves React build, proxies `/api/` → API Gateway) |
| **Monitoring** | Prometheus + Grafana (3 dashboards, 7 scrape targets) |
| **Orchestration** | Docker Compose (11 containers, bridge network, 5 named volumes) |
| **CI/CD** | 8-stage shell pipeline with auto-rollback |
| **Security** | Gitleaks secret scanning, API key auth, rate limiting, `.env`-driven config |
| **Testing** | pytest + pytest-cov (254 unit tests, ≥60% coverage per service) |

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Containers not starting | Run `docker compose logs <service>` to check errors |
| `AUTH_USERS` empty error | Ensure `.env` exists with `AUTH_USERS=admin:admin` |
| Database connection refused | Wait 60s for DBs to initialize; check `docker compose ps` for healthy |
| Grafana panels show "No data" | Trigger some alerts/escalations; wait 15s for Prometheus scrape |
| Port already in use | Stop conflicting services or change ports in `.env` |
| CI fails at Stage 3 | Ensure `.env` exists in project root — tests load credentials from it |

### Clean restart (fresh databases)

```bash
docker compose down -v          # Stop + remove all volumes
docker compose up -d --build    # Rebuild from scratch
```

---

## Team

| Role | Scope |
|---|---|
| **Person 1** | Backend Services (Alert Ingestion, Incident Management, Database) |
| **Person 2** | DevOps & Infrastructure (On-Call Service, CI/CD, Monitoring) |
| **Person 3** | Frontend & Integration (Web UI, Notification Service, API Gateway) |
