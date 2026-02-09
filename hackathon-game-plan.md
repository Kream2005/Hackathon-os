# 🚨 DevOps Incident & On-Call Platform Hackathon — Full Breakdown & Team Game Plan

**Date:** February 9-10, 2026
**Duration:** 29 hours
**Team Size:** 3 persons

---

## TABLE OF CONTENTS

1. [What's Required of You](#whats-required-of-you)
2. [Scoring Breakdown](#scoring-breakdown)
3. [Team Split: 3 Persons](#team-split-3-persons)
   - [Person 1: The Backend Engine](#person-1-the-backend-engine)
   - [Person 2: The DevOps & Infra Master](#person-2-the-devops--infra-master)
   - [Person 3: The Frontend & Integration Specialist](#person-3-the-frontend--integration-specialist)
4. [Integration Checkpoints](#integration-checkpoints)
5. [Survival Tips](#survival-tips)

---

## WHAT'S REQUIRED OF YOU

You need to build a **mini PagerDuty clone** that runs **entirely on your laptop** using Docker. Here's what the platform does:

1. **Receives alerts** (like "CPU is high!" or "Server is down!") via an API
2. **Groups those alerts into incidents** (if 5 alerts are about the same thing, they become 1 incident)
3. **Figures out who's on-call** (based on a rotation schedule) and notifies them
4. **Lets engineers acknowledge and resolve incidents** via a web dashboard
5. **Tracks metrics** like how fast you responded (MTTA) and how fast you fixed it (MTTR)
6. **Shows everything on Grafana dashboards**

All of this must be:

- Split into **at least 4 microservices** (each in its own Docker container)
- Orchestrated with a **single `docker-compose.yml`** (one command to run everything)
- Monitored with **Prometheus + Grafana**
- Built/deployed via a **CI/CD pipeline** (at least 4 stages)
- **Secure** (no hardcoded passwords, credentials scanning)
- **Tested** (≥60% test coverage)

---

## SCORING BREAKDOWN

| Category                                                    | Points   | Priority     |
| ----------------------------------------------------------- | -------- | ------------ |
| **Platform Functionality** (services work, end-to-end flow) | **30**   | 🔴 HIGHEST  |
| **DevOps Implementation** (CI/CD, Docker, Compose)          | **30**   | 🔴 HIGHEST  |
| **Monitoring & SRE Metrics** (Prometheus, Grafana)          | **20**   | 🟡 HIGH     |
| **Architecture & Design** (clean SOA, good APIs)            | **15**   | 🟡 HIGH     |
| **Security & Quality** (secrets scanning, test coverage)    | **5**    | 🟢 MEDIUM   |
| **TOTAL**                                                   | **100**  |              |

---

## TEAM SPLIT: 3 PERSONS

Each person works **independently** on their slice and you integrate at defined checkpoints.

---

## 👤 PERSON 1: "The Backend Engine"

### Owns: Alert Ingestion Service + Incident Management Service + Database

**Why this person matters:** They build the **core brain** of the platform. Without them, nothing works.

---

### Tasks (in order):

### Hour 0–1: Setup Foundation

- Create the GitHub repo with this structure:

```
incident-platform/
├── services/
│   ├── alert-ingestion/
│   ├── incident-management/
│   ├── oncall-service/       ← (Person 2 will fill this)
│   └── web-ui/               ← (Person 3 will fill this)
├── monitoring/
│   ├── prometheus.yml
│   └── grafana-dashboards/
├── docker-compose.yml
├── .env
└── README.md
```

- Set up the **PostgreSQL database** container in `docker-compose.yml`
- Create the database schema (tables for `alerts`, `incidents`, `incident_notes`, `incident_alerts`)

---

### Hour 1–5: Alert Ingestion Service (port 8001)

Build the service (Python FastAPI or Node.js Express recommended):

- **`POST /api/v1/alerts`** — Accepts alert JSON, validates it (must have `service`, `severity`, `message`), stores it
- **Correlation logic**: Before creating a new incident, check if there's already an open incident with the **same service + same severity** created within the **last 5 minutes**. If yes → attach alert to that incident. If no → create a new incident.
- **`GET /api/v1/alerts/{alert_id}`** — Return a single alert
- **`GET /health`** — Returns `{"status": "ok"}`
- **`GET /metrics`** — Prometheus format metrics:
  - `alerts_received_total` (counter, label: severity)
  - `alerts_correlated_total` (counter, label: result = `new_incident` or `existing_incident`)

---

### Hour 5–10: Incident Management Service (port 8002)

- **`POST /api/v1/incidents`** — Create incident (called by Alert Ingestion or manually)
- **`GET /api/v1/incidents`** — List incidents (filter by `status`, `severity`, `service`)
- **`GET /api/v1/incidents/{id}`** — Get incident detail with timeline
- **`PATCH /api/v1/incidents/{id}`** — Update status (`open` → `acknowledged` → `in_progress` → `resolved`), add notes
- **On incident creation**: Call Person 2's On-Call service (`GET http://oncall-service:8003/api/v1/oncall/current?team=...`) to get the on-call engineer and assign them
- **MTTA calculation**: `acknowledged_at - created_at`
- **MTTR calculation**: `resolved_at - created_at`
- **`GET /metrics`** — Prometheus format:
  - `incidents_total` (gauge, label: status)
  - `incident_mtta_seconds` (histogram)
  - `incident_mttr_seconds` (histogram)

---

### Hour 10–12: Integration + Testing

- Write **unit tests** (≥60% coverage on these two services)
- Test end-to-end with `curl`: send alert → incident created → acknowledge → resolve
- Make sure both services communicate over the Docker network

---

### Dockerfile Requirements (for each service):

- Multi-stage build
- Alpine or slim base image
- Non-root `USER`
- `HEALTHCHECK` instruction
- `.dockerignore` file
- No hardcoded secrets (use environment variables from `.env`)

---

### Database Schema (suggested):

```sql
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service VARCHAR(255) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('critical','high','medium','low')),
    message TEXT NOT NULL,
    labels JSONB,
    timestamp TIMESTAMPTZ NOT NULL,
    incident_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    service VARCHAR(255) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'open' CHECK (status IN ('open','acknowledged','in_progress','resolved')),
    assigned_to VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    mtta_seconds FLOAT,
    mttr_seconds FLOAT
);

CREATE TABLE incident_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id UUID REFERENCES incidents(id),
    author VARCHAR(255),
    content TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

### Integration Points with Others:

- **Tell Person 2**: "I will call `GET http://oncall-service:8003/api/v1/oncall/current?team={team}` and expect back `{name, email, role}`"
- **Tell Person 3**: "I expose these APIs for you to call from the frontend: list incidents, get incident, update incident, list alerts"

---

---

## 👤 PERSON 2: "The DevOps & Infra Master"

### Owns: On-Call Service + CI/CD Pipeline + Monitoring Stack (Prometheus + Grafana) + Security/Quality Gates

**Why this person matters:** They own **55 out of 100 points** (DevOps=30 + Monitoring=20 + Security=5). The judges will evaluate Docker quality, pipeline stages, dashboards, and security.

---

### Tasks (in order):

### Hour 0–3: On-Call & Escalation Service (port 8003)

Build a lightweight service:

- **`POST /api/v1/schedules`** — Create a rotation schedule:

```json
{
  "team": "platform-engineering",
  "rotation_type": "weekly",
  "members": [
    {"name": "Alice", "email": "alice@example.com", "role": "primary"},
    {"name": "Bob", "email": "bob@example.com", "role": "primary"},
    {"name": "Carol", "email": "carol@example.com", "role": "secondary"}
  ]
}
```

- **`GET /api/v1/schedules`** — List all schedules
- **`GET /api/v1/oncall/current?team=platform-engineering`** — Calculate who's on-call RIGHT NOW based on the rotation. Logic: `member_index = (week_of_year % number_of_primary_members)`. Return:

```json
{
  "team": "platform-engineering",
  "primary": {"name": "Alice", "email": "alice@example.com"},
  "secondary": {"name": "Carol", "email": "carol@example.com"}
}
```

- **`POST /api/v1/escalate`** — Trigger escalation (log it, update metrics)
- **`GET /health`** + **`GET /metrics`**
  - Metrics: `oncall_notifications_sent_total`, `escalations_total{team}`

---

### Hour 3–6: Docker Compose + Monitoring Stack

- Finalize `docker-compose.yml` with ALL services (coordinate with Person 1 & 3)
- Set up **Prometheus** container with this config:

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'alert-ingestion'
    static_configs:
      - targets: ['alert-ingestion:8001']
  - job_name: 'incident-management'
    static_configs:
      - targets: ['incident-management:8002']
  - job_name: 'oncall-service'
    static_configs:
      - targets: ['oncall-service:8003']
  - job_name: 'web-ui'
    static_configs:
      - targets: ['web-ui:8080']
```

- Set up **Grafana** with provisioned dashboards (JSON files):
  - **Dashboard 1 — Live Incident Overview**: Open incidents by severity, MTTA gauge, MTTR gauge, incidents over time, top noisy services
  - **Dashboard 2 — SRE Performance Metrics**: MTTA trend, MTTR trend, incident volume by service, acknowledgment time distribution

---

### Hour 6–10: CI/CD Pipeline (The BIG One)

Create `run-pipeline.sh` (or `Makefile`) with **at least 4 stages**:

```bash
#!/bin/bash
set -e

echo "=============================="
echo "STAGE 1: Code Quality & Testing"
echo "=============================="
# Run linters (e.g., flake8 for Python, eslint for Node)
# Run unit tests with coverage
# FAIL if coverage < 60%

echo "=============================="
echo "STAGE 2: Security Scanning"
echo "=============================="
# Run gitleaks or trufflehog to detect secrets
# FAIL if secrets found

echo "=============================="
echo "STAGE 3: Build Container Images"
echo "=============================="
docker compose build
# Tag images with git commit SHA

echo "=============================="
echo "STAGE 4: Deploy"
echo "=============================="
docker compose down --remove-orphans || true
docker compose up -d

echo "=============================="
echo "STAGE 5: Post-Deployment Verification"
echo "=============================="
# Wait for services to be healthy
sleep 10
for port in 8001 8002 8003 8080; do
  echo "Checking localhost:$port/health..."
  curl -f http://localhost:$port/health || { echo "FAILED"; exit 1; }
done
echo "All services healthy!"

echo "=============================="
echo "PIPELINE PASSED ✅"
echo "=============================="
```

---

### Hour 10–12: Security & Quality Gates

- Install and configure **gitleaks** or **trufflehog** for credential scanning
- Create a `.gitleaks.toml` config file
- Add a **pre-commit hook** that runs the scanner
- Make sure the `.env` file is in `.gitignore`
- Review ALL Dockerfiles: confirm non-root user, no secrets, multi-stage builds
- Write tests for the On-Call service (≥60% coverage)

---

### Hour 12–13: Final Polish

- Verify all Prometheus targets are UP at `http://localhost:9090/targets`
- Verify Grafana dashboards load with real data
- Run the full pipeline end-to-end one final time
- Help Person 3 with any integration issues

---

### Critical Files You Own:

| File                                    | Purpose                          |
| --------------------------------------- | -------------------------------- |
| `docker-compose.yml`                    | The entire infrastructure definition |
| `monitoring/prometheus.yml`             | Prometheus scraping config       |
| `monitoring/grafana-dashboards/*.json`  | Dashboard definitions            |
| `run-pipeline.sh` or `Makefile`         | CI/CD pipeline                   |
| `.gitleaks.toml`                        | Credentials scanning config      |
| `services/oncall-service/`              | On-Call microservice             |

---

---

## 👤 PERSON 3: "The Frontend & Integration Specialist"

### Owns: Web UI / API Gateway + Notification Service (optional) + Documentation + Demo

**Why this person matters:** The judges **see your project through the UI and README**. A broken or ugly UI = bad first impression. A bad README = judges can't even run your project.

---

### Tasks (in order):

### Hour 0–3: Web UI Skeleton (port 8080)

Choose React, Vue, or even plain HTML+JS (fastest). Build these pages:

**Page 1: Dashboard** (`/`)

- Shows count of open/acknowledged/resolved incidents
- Table listing all open incidents (severity, service, assigned to, created time)
- Click on incident → goes to detail page
- Quick metrics: current MTTA average, current MTTR average

**Page 2: Incident Detail** (`/incidents/:id`)

- Shows: title, severity badge, service, status, assigned engineer
- Timeline of events (created, acknowledged, resolved, notes added)
- **"Acknowledge" button** → calls `PATCH /api/v1/incidents/{id}` with `{"status": "acknowledged"}`
- **"Resolve" button** → calls `PATCH /api/v1/incidents/{id}` with `{"status": "resolved"}`
- Add note form

**Page 3: On-Call Schedule** (`/oncall`)

- Shows current on-call engineers per team
- Lists upcoming rotations

**Page 4: SRE Metrics** (`/metrics`)

- Embedded Grafana iframe OR simple charts showing MTTA/MTTR trends

---

### Hour 3–6: Connect Frontend to Backend APIs

- Call Person 1's APIs:
  - `GET http://localhost:8002/api/v1/incidents` → populate dashboard
  - `GET http://localhost:8002/api/v1/incidents/{id}` → incident detail
  - `PATCH http://localhost:8002/api/v1/incidents/{id}` → acknowledge/resolve
- Call Person 2's APIs:
  - `GET http://localhost:8003/api/v1/oncall/current?team=platform-engineering` → on-call page
  - `GET http://localhost:8003/api/v1/schedules` → schedule list
- **Important**: In Docker network, the frontend container talks to backends using **service names** (e.g., `http://incident-management:8002`). But the browser runs on **localhost**. So you need either:
  - An **API gateway/proxy** in your container (nginx reverse proxy), OR
  - Direct browser calls to `localhost:800X` ports (simpler for hackathon)

---

### Hour 6–8: Notification Service — Optional but Easy Points (+bonus)

Port 8004. Very simple:

- **`POST /api/v1/notify`** — Accepts `{incident_id, channel, recipient, message}`, **logs it to console/file** (mocking is fine!)
- **`GET /health`** + **`GET /metrics`** (`notifications_sent_total{channel, status}`)
- This gives you a 5th microservice (bonus points)

---

### Hour 8–10: Dockerize the Frontend

- Create `Dockerfile` for Web UI:
  - Stage 1: Build (e.g., `node:18-alpine` → `npm run build`)
  - Stage 2: Serve (e.g., `nginx:alpine` → copy build output)
- Multi-stage, non-root, healthcheck — same rules
- Add `GET /health` endpoint (nginx can return a static 200)

---

### Hour 10–13: Documentation + Demo Prep (CRITICAL)

**README.md** — This is what judges read FIRST:

```markdown
# 🚨 Incident & On-Call Management Platform

## Architecture
[Insert diagram — even ASCII art is fine]

4 microservices + PostgreSQL + Prometheus + Grafana

| Service              | Port | Tech              |
| -------------------- | ---- | ----------------- |
| Alert Ingestion      | 8001 | Python FastAPI    |
| Incident Management  | 8002 | Python FastAPI    |
| On-Call Service      | 8003 | Node.js Express   |
| Web UI               | 8080 | React + Nginx     |
| PostgreSQL           | 5432 | postgres:15-alpine|
| Prometheus           | 9090 | prom/prometheus   |
| Grafana              | 3000 | grafana/grafana   |

## Quick Start (< 5 commands)
git clone https://github.com/yourteam/incident-platform
cd incident-platform
docker compose up -d
# Wait 30 seconds

## Verify
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8080/health

## Test Alert
curl -X POST http://localhost:8001/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '{"service":"frontend-api","severity":"high","message":"HTTP 5xx errors > 10%","labels":{"env":"prod"}}'

## Access
- **Web UI**: http://localhost:8080
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

## API Documentation
[Document all endpoints]

## Team
- Person 1: Backend Services
- Person 2: DevOps & Infrastructure
- Person 3: Frontend & Integration

## CI/CD Pipeline
Run: `./run-pipeline.sh`
Stages: Quality → Security → Build → Deploy → Verify
```

- Write **API documentation** for all endpoints
- Create **architecture diagram** (use draw.io, excalidraw, or ASCII)
- Run the **demo checklist**:
  - [ ] `docker compose up -d` works
  - [ ] All health checks pass
  - [ ] Web UI loads
  - [ ] Send test alert → incident appears
  - [ ] Acknowledge and resolve incident
  - [ ] Grafana shows metrics
  - [ ] README is accurate
  - [ ] No hardcoded secrets

---

---

## 🤝 INTEGRATION CHECKPOINTS

| Time                     | What                                                                                                                   | Who |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------- | --- |
| **Hour 3** (12:30 PM)   | All 3 agree on API contracts (request/response JSON formats)                                                          | All |
| **Hour 6** (3:30 PM)    | Person 1's backend APIs callable via curl. Person 2's On-Call service responds. Person 3's UI skeleton renders.        | All |
| **Hour 10** (7:30 PM)   | Full end-to-end flow works: alert → incident → UI display → acknowledge → resolve                                     | All |
| **Hour 14** (11:30 PM)  | `docker compose up -d` runs entire stack. Prometheus scrapes all services.                                             | All |
| **Hour 24** (9:30 AM)   | Grafana dashboards show real data. CI/CD pipeline passes.                                                              | All |
| **Hour 27** (12:30 PM)  | README final, demo tested, submission ready                                                                            | All |

---

## ⚡ SURVIVAL TIPS

1. **Don't overthink the tech stack** — Pick what your team knows best. Python FastAPI is the fastest to build with.
2. **Get `docker compose up` working with stub services FIRST** (even if they just return `{"status":"ok"}` on `/health`). Then fill in real logic.
3. **The correlation algorithm doesn't need to be perfect** — A simple "same service + same severity + within 5 min = same incident" query is enough.
4. **Mock notifications** — Don't waste time on real email. A `console.log("Notified Alice about incident X")` is 100% acceptable.
5. **Grafana dashboards can be provisioned from JSON** — Find templates online and adapt them.
6. **Test with `curl` constantly** — Don't wait until the end to see if things work.
7. **Commit often** — The judges may look at git history.
8. **Sleep during 3–8 AM** — Seriously. Tired code = buggy code = failed demo.

---

## QUICK REFERENCE: API CONTRACTS

### Alert Ingestion Service (Person 1) — Port 8001

| Method | Endpoint                  | Purpose              |
| ------ | ------------------------- | -------------------- |
| POST   | `/api/v1/alerts`          | Receive new alert    |
| GET    | `/api/v1/alerts/{id}`     | Get alert by ID      |
| GET    | `/health`                 | Health check         |
| GET    | `/metrics`                | Prometheus metrics   |

### Incident Management Service (Person 1) — Port 8002

| Method | Endpoint                          | Purpose                  |
| ------ | --------------------------------- | ------------------------ |
| POST   | `/api/v1/incidents`               | Create incident          |
| GET    | `/api/v1/incidents`               | List incidents (filters) |
| GET    | `/api/v1/incidents/{id}`          | Get incident detail      |
| PATCH  | `/api/v1/incidents/{id}`          | Update status/add notes  |
| GET    | `/api/v1/incidents/{id}/metrics`  | Get incident MTTA/MTTR   |
| GET    | `/health`                         | Health check             |
| GET    | `/metrics`                        | Prometheus metrics       |

### On-Call & Escalation Service (Person 2) — Port 8003

| Method | Endpoint                              | Purpose                |
| ------ | ------------------------------------- | ---------------------- |
| POST   | `/api/v1/schedules`                   | Create schedule        |
| GET    | `/api/v1/schedules`                   | List schedules         |
| GET    | `/api/v1/oncall/current?team={team}`  | Get current on-call    |
| POST   | `/api/v1/escalate`                    | Trigger escalation     |
| GET    | `/health`                             | Health check           |
| GET    | `/metrics`                            | Prometheus metrics     |

### Notification Service (Person 3, optional) — Port 8004

| Method | Endpoint            | Purpose            |
| ------ | ------------------- | ------------------ |
| POST   | `/api/v1/notify`    | Send notification  |
| GET    | `/health`           | Health check       |
| GET    | `/metrics`          | Prometheus metrics |

### Web UI (Person 3) — Port 8080

| Page               | URL               | Purpose                    |
| ------------------ | ----------------- | -------------------------- |
| Dashboard          | `/`               | Open incidents overview    |
| Incident Detail    | `/incidents/:id`  | View & manage incident     |
| On-Call Schedule   | `/oncall`         | Current on-call display    |
| SRE Metrics        | `/metrics-page`   | MTTA/MTTR charts           |

---

## QUICK REFERENCE: PROMETHEUS METRICS

All services must expose these at `GET /metrics` in Prometheus text format:

| Metric                                                       | Type      | Owner    |
| ------------------------------------------------------------ | --------- | -------- |
| `alerts_received_total{severity="..."}`                      | Counter   | Person 1 |
| `alerts_correlated_total{result="new_incident\|existing"}`   | Counter   | Person 1 |
| `incidents_total{status="open\|ack\|resolved"}`              | Gauge     | Person 1 |
| `incident_mtta_seconds`                                      | Histogram | Person 1 |
| `incident_mttr_seconds`                                      | Histogram | Person 1 |
| `oncall_notifications_sent_total{channel="..."}`             | Counter   | Person 2 |
| `escalations_total{team="..."}`                              | Counter   | Person 2 |
| `notifications_sent_total{channel="...",status="..."}`       | Counter   | Person 3 |

---

**Good luck! Build something amazing! 🚀**