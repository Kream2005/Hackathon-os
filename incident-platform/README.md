# 🚨 Incident Platform — Mini PagerDuty Clone

A complete incident management platform built with microservices architecture, featuring alert ingestion, incident management, on-call scheduling, and real-time monitoring.

## 📋 Table of Contents

- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [Services](#-services)
- [API Endpoints](#-api-endpoints)
- [CI/CD Pipeline](#-cicd-pipeline)
- [Monitoring & Dashboards](#-monitoring--dashboards)
- [Security](#-security)
- [Development](#-development)

---

## 🏗️ Architecture

```
                    ┌──────────────────┐
                    │     Web UI       │
                    │   :8080          │
                    └──────┬───────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
    ┌─────────▼──┐  ┌──────▼─────┐  ┌──▼──────────┐
    │   Alert    │  │  Incident  │  │  On-Call     │
    │ Ingestion  │  │ Management │  │  Service     │
    │  :8001     │  │  :8002     │  │  :8003       │
    └─────┬──────┘  └──────┬─────┘  └──────────────┘
          │                │
          │         ┌──────▼─────┐
          │         │Notification│
          │         │  Service   │
          │         │  :8004     │
          │         └────────────┘
          │
    ┌─────▼──────┐
    │ PostgreSQL │
    │  :5432     │
    └────────────┘

    ┌────────────┐    ┌────────────┐
    │ Prometheus │───▶│  Grafana   │
    │  :9090     │    │  :3000     │
    └────────────┘    └────────────┘
```

**Tech Stack:**
- **Language:** Python 3.11 + FastAPI
- **Database:** PostgreSQL 15
- **Monitoring:** Prometheus + Grafana
- **Containers:** Docker with multi-stage builds
- **Orchestration:** Docker Compose

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Git

### Launch

```bash
# 1. Clone the repository
git clone <repo-url>
cd incident-platform

# 2. Configure environment
cp .env.example .env
# Edit .env with your values

# 3. Start everything (one command!)
docker compose up -d

# 4. Verify
docker compose ps
```

### Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| Web UI | http://localhost:8080 | — |
| Alert Ingestion API | http://localhost:8001/docs | — |
| Incident Management API | http://localhost:8002/docs | — |
| On-Call Service API | http://localhost:8003/docs | — |
| Notification Service API | http://localhost:8004/docs | — |
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3000 | admin / admin |

---

## 🔧 Services

### Alert Ingestion (Port 8001)
Receives alerts from external monitoring systems, correlates them, and creates incidents.

### Incident Management (Port 8002)
Manages the full incident lifecycle: creation → acknowledgment → resolution. Calculates MTTA and MTTR metrics.

### On-Call Service (Port 8003)
Manages on-call schedules and rotations. Determines who is on-call at any given time. Supports:
- **Weekly / Daily / Biweekly** rotations
- **Manual overrides** for one-off changes
- **Escalation** to secondary on-call

### Notification Service (Port 8004)
Simulates sending notifications via console logging (email, Slack, SMS simulation).

### Web UI (Port 8080)
Dashboard providing an overview of all services and their health status.

---

## 📡 API Endpoints

### Alert Ingestion (:8001)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |
| POST | `/api/v1/alerts` | Receive a new alert |
| GET | `/api/v1/alerts` | List all alerts |

### Incident Management (:8002)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |
| POST | `/api/v1/incidents` | Create incident |
| GET | `/api/v1/incidents` | List incidents |
| PATCH | `/api/v1/incidents/{id}/acknowledge` | Acknowledge incident |
| PATCH | `/api/v1/incidents/{id}/resolve` | Resolve incident |
| GET | `/api/v1/incidents/stats` | Incident statistics |

### On-Call Service (:8003)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |
| POST | `/api/v1/schedules` | Create on-call schedule |
| GET | `/api/v1/schedules` | List all schedules |
| GET | `/api/v1/schedules/{team}` | Get team schedule |
| DELETE | `/api/v1/schedules/{team}` | Delete schedule |
| GET | `/api/v1/oncall/current?team=X` | Get current on-call |
| POST | `/api/v1/oncall/override` | Set manual override |
| DELETE | `/api/v1/oncall/override/{team}` | Remove override |
| POST | `/api/v1/escalate` | Trigger escalation |
| GET | `/api/v1/escalations` | List escalation history |
| GET | `/api/v1/teams` | List all teams |

### Notification Service (:8004)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |
| POST | `/api/v1/notify` | Send notification |
| GET | `/api/v1/notifications` | List notifications |

---

## 🔄 CI/CD Pipeline

The pipeline runs with a single command and executes **6 stages** sequentially:

```bash
./run-pipeline.sh
# or
cd ci && bash pipeline.sh
```

### Pipeline Stages

| Stage | Script | Description |
|-------|--------|-------------|
| 1 | `ci/quality.sh` | **Code Quality**: Ruff/Flake8 linting + syntax check |
| 2 | `ci/security.sh` | **Security Scan**: Secret detection, Dockerfile audit, .gitignore check |
| 3 | `ci/test.sh` | **Tests & Coverage**: pytest with ≥60% coverage requirement |
| 4 | `ci/build.sh` | **Build**: Docker images with Git SHA tagging |
| 5 | `ci/deploy.sh` | **Deploy**: `docker compose up -d` |
| 6 | `ci/verify.sh` | **Verification**: Health checks + smoke test (end-to-end) |

The pipeline outputs **colorized results** with timing for each stage and a final summary.

---

## 📊 Monitoring & Dashboards

### Prometheus
- Scrapes all 5 services every 10-15 seconds
- Access targets: http://localhost:9090/targets
- All services expose `/metrics` in Prometheus text format

### Grafana Dashboards (auto-provisioned)

**Dashboard 1 — Incident Overview:**
- Open incidents counter
- MTTA / MTTR gauges
- Alerts received over time (rate graph)
- Incidents by severity (bar gauge)
- Incidents by status (pie chart)
- Service request rates

**Dashboard 2 — SRE Performance:**
- MTTA / MTTR trends over time (with P95)
- Incident volume by service
- Request latency distribution
- Escalations & notifications counters
- On-call lookups by team
- Service uptime (UP/DOWN timeline)

---

## 🔒 Security

| Measure | Implementation |
|---------|---------------|
| **No hardcoded secrets** | All sensitive values in `.env` (not committed) |
| **Non-root containers** | All Dockerfiles use `USER appuser` |
| **Multi-stage builds** | Smaller images, no build tools in production |
| **Secret scanning** | Gitleaks config + CI pipeline check |
| **CORS configured** | All services accept cross-origin requests |
| **.gitignore** | `.env`, `__pycache__`, `node_modules`, coverage reports |
| **Docker healthchecks** | Every container has `HEALTHCHECK` |

---

## 🧪 Development

### Run Tests Locally

```bash
cd services/oncall-service
pip install -r requirements.txt
pytest test_main.py --cov=main --cov-report=term-missing -v
```

### Run a Single Service

```bash
cd services/oncall-service
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8003 --reload
```

### Rebuild After Changes

```bash
docker compose build oncall-service
docker compose up -d oncall-service
```

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f oncall-service
```

### Clean Restart

```bash
docker compose down -v
docker compose up -d --build
```

---

## 👥 Team

| Role | Responsibilities |
|------|-----------------|
| **Person 1** — Backend | Alert Ingestion + Incident Management + Database |
| **Person 2** — DevOps | On-Call Service + Docker + CI/CD + Monitoring + Security |
| **Person 3** — Frontend | Web UI + Notifications + Demo |

---

## 📄 License

Hackathon Project — 2026
