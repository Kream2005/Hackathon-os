# Comprehensive Project Analysis — DevOps Incident & On-Call Platform

> **Purpose of this document:** A deep-dive into every concept, every line of architecture,
> what was built, what's missing, how to score higher, and how to start thinking like a
> DevOps / automation engineer.

---

## Table of Contents

1. [The Big Picture — What Is This Project?](#1-the-big-picture)
2. [Core DevOps Concepts Explained](#2-core-devops-concepts-explained)
   - 2.1 Microservices & Service-Oriented Architecture (SOA)
   - 2.2 Containerisation (Docker)
   - 2.3 Container Orchestration (Docker Compose)
   - 2.4 CI/CD Pipelines
   - 2.5 Observability: Monitoring, Metrics, Dashboards
   - 2.6 Infrastructure as Code (IaC)
   - 2.7 Security & Credentials Management
   - 2.8 Testing & Code Quality
   - 2.9 SRE Metrics: MTTA & MTTR
3. [Architecture Deep-Dive](#3-architecture-deep-dive)
4. [Component-by-Component Analysis](#4-component-by-component-analysis)
   - 4.1 Database (PostgreSQL)
   - 4.2 Alert Ingestion Service (port 8001)
   - 4.3 Incident Management Service (port 8002)
   - 4.4 On-Call Service (port 8003) — NOT IMPLEMENTED
   - 4.5 Notification Service (port 8004) — NOT IMPLEMENTED
   - 4.6 Web UI (port 8080) — NOT IMPLEMENTED
   - 4.7 Prometheus (port 9090)
   - 4.8 Grafana (port 3000)
   - 4.9 CI/CD Pipeline (run-pipeline.sh) — NOT IMPLEMENTED
5. [Docker & Dockerfile Best Practices Analysis](#5-docker-analysis)
6. [Testing Analysis](#6-testing-analysis)
7. [Monitoring Stack Analysis](#7-monitoring-stack-analysis)
8. [Security Analysis](#8-security-analysis)
9. [Scoring Estimate Against the Rubric](#9-scoring-estimate)
10. [Gap Analysis — What's Missing & Priorities](#10-gap-analysis)
11. [Concrete Improvement Plan](#11-improvement-plan)
12. [Thinking Like a DevOps Engineer](#12-devops-mindset)

---

## 1. The Big Picture

### What is the project?

You're building a **mini PagerDuty clone** — an incident management platform. In real-world
operations (SRE / DevOps), when something breaks in production (a server crashes, response
times spike, error rates climb), monitoring tools fire **alerts**. Those alerts need to be:

1. **Ingested** — received and stored centrally
2. **Correlated** — "these 50 alerts about the same server are really 1 incident"
3. **Assigned** — "who's on-call right now? Route it to them"
4. **Managed** — acknowledge, investigate, resolve, document
5. **Measured** — "how fast did we respond? How fast did we fix it?"
6. **Visualised** — dashboards showing the health of the operation in real time

### Why does this matter?

Every major tech company (Google, Amazon, Netflix, Meta) runs platforms like this
in production. The hackathon is testing whether you can:

- Design systems as **independent services** (microservices)
- Package them in **containers** (Docker)
- Wire them together with **orchestration** (Docker Compose)
- Automate quality checks with **CI/CD pipelines**
- Instrument everything with **metrics and dashboards**
- Keep it **secure** (no leaked passwords)

**This is the daily job of a DevOps / SRE / Platform engineer.**

---

## 2. Core DevOps Concepts Explained

### 2.1 Microservices & Service-Oriented Architecture (SOA)

**What it is:**
Instead of one monolithic application, you split functionality into small, independent
services that communicate over the network (usually HTTP/REST or message queues).

**In this project:**
```
┌──────────────┐    HTTP POST     ┌────────────────────┐
│    Alert      │ ───────────────►│   Incident          │
│  Ingestion    │                 │   Management        │
│  (port 8001)  │                 │   (port 8002)       │
└──────────────┘                 └────────────────────┘
                                          │
                            HTTP GET      │     HTTP POST
                       ┌──────────────────┘──────────────────┐
                       ▼                                     ▼
              ┌──────────────┐                    ┌──────────────────┐
              │   On-Call     │                    │   Notification    │
              │   Service     │                    │   Service         │
              │  (port 8003)  │                    │   (port 8004)     │
              └──────────────┘                    └──────────────────┘
```

**Why microservices?**
- **Independent deployment** — you can update one service without restarting others
- **Independent scaling** — if alert ingestion gets 1000 req/s, scale just that
- **Fault isolation** — if notification service crashes, incidents still work
- **Team ownership** — different people/teams own different services

**What you did well:**
- Alert Ingestion and Incident Management are truly independent services
- They communicate via HTTP (`httpx.Client`)
- Each has its own Dockerfile, requirements.txt, and health endpoints
- Alert Ingestion has a **fallback** — if Incident Management is down, it creates
  the incident locally in the shared DB (resilience!)

**What could be better:**
- On-Call and Notification services are empty — need at least stub endpoints
- Services share a single PostgreSQL database. In real microservices, each service
  would ideally own its own database (the "database per service" pattern). For a
  hackathon, shared DB is acceptable, but know the trade-off.

---

### 2.2 Containerisation (Docker)

**What it is:**
Docker packages your application + all its dependencies into an isolated, reproducible
unit called a **container**. Think of it as a lightweight virtual machine that contains
only what your app needs to run.

**Key Docker concepts:**

| Concept        | What it means                                                      |
|----------------|--------------------------------------------------------------------|
| **Image**      | A read-only template (like a snapshot). Built from a Dockerfile.   |
| **Container**  | A running instance of an image.                                    |
| **Dockerfile** | Instructions to build an image (install deps, copy code, run).     |
| **Layer**      | Each Dockerfile instruction creates a layer. Layers are cached.    |
| **Registry**   | A place to store/share images (Docker Hub, GHCR).                  |

**Your Dockerfiles (alert-ingestion & incident-management):**
```dockerfile
# ── Build stage ──────────────────────────────────────
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Runtime stage ────────────────────────────────────
FROM python:3.11-slim
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Non-root user for security
RUN useradd -r -s /bin/false appuser
USER appuser

EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

**What's happening here — line by line:**

1. **Multi-stage build** (`FROM ... AS builder` → `FROM ...`): The first stage installs
   Python packages into a temporary location. The second stage copies only the installed
   packages, leaving behind pip cache, build tools, and compile artifacts. This makes
   the final image **smaller and more secure**.

2. **`python:3.11-slim`**: Uses a Debian-based slim image instead of the full image
   (~150MB vs ~900MB). Alpine would be even smaller (~50MB) but can have compatibility
   issues with Python C extensions.

3. **`--no-cache-dir`**: Tells pip not to store downloaded packages, reducing image size.

4. **Non-root USER**: The container runs as `appuser` instead of `root`. If an attacker
   compromises the container, they won't have root access to the host. This is a security
   best practice required by the hackathon.

5. **HEALTHCHECK**: Docker periodically runs `curl http://localhost:8001/health`. If it
   fails 3 times in a row, Docker marks the container as `unhealthy`. This lets Docker
   Compose know if a service is actually working, not just running.

6. **EXPOSE**: Documents which port the container listens on (informational — doesn't
   actually publish the port).

**What you did well:**
- Multi-stage builds ✓
- Non-root user ✓
- HEALTHCHECK instruction ✓
- Slim base image ✓
- `.dockerignore` to exclude unnecessary files ✓

**What could be better:**
- Pin exact image versions: `python:3.11.7-slim` instead of `python:3.11-slim`
  (reproducibility — builds should produce identical results every time)
- Add `--no-install-recommends` to any apt commands
- Web UI Dockerfile is empty (0 bytes)

---

### 2.3 Container Orchestration (Docker Compose)

**What it is:**
Docker Compose lets you define and run **multi-container applications** with a single
YAML file. Instead of starting 7 containers manually, you run `docker compose up -d`.

**Your `docker-compose.yml` defines:**

| Service              | Image/Build        | Port  | Depends On   | Health Check |
|----------------------|--------------------|-------|--------------|--------------|
| database             | postgres:15-alpine | 5432  | —            | pg_isready   |
| alert-ingestion      | ./services/alert-ingestion | 8001 | database (healthy) | curl /health |
| incident-management  | ./services/incident-management | 8002 | database (healthy) | curl /health |
| oncall-service       | ./services/oncall-service | 8003 | database (healthy) | curl /health |
| notification-service | ./services/notification-service | 8004 | — | curl /health |
| web-ui               | ./services/web-ui  | 8080  | alert-ingestion, incident-management, oncall-service | curl /health |
| prometheus           | prom/prometheus    | 9090  | —            | —            |
| grafana              | grafana/grafana    | 3000  | prometheus   | —            |

**Key Compose concepts used:**

1. **`depends_on` with `condition: service_healthy`**: This ensures the database is
   fully ready (not just started) before services that need it attempt to connect.
   Without this, services would crash on startup because the DB isn't accepting
   connections yet.

2. **Named volumes** (`db-data`, `prometheus-data`, `grafana-data`): Data persists
   across container restarts. If you `docker compose down` and `up` again, your
   incidents and dashboard configs survive.

3. **Custom bridge network** (`incident-platform`): All services are on the same
   Docker network. They can reach each other by service name (e.g.,
   `http://incident-management:8002`). This is Docker's built-in DNS resolution.

4. **`restart: unless-stopped`**: If a service crashes, Docker automatically restarts
   it. This provides basic self-healing without a full orchestrator like Kubernetes.

5. **Environment variables** from `.env`: Secrets like database passwords are not
   hardcoded in the compose file — they're referenced from a `.env` file that's in
   `.gitignore`.

**What you did well:**
- All services defined with ports, networks, health checks ✓
- Dependency ordering with health conditions ✓
- Named volumes for persistence ✓
- Environment variable externalization ✓
- Bridge network for inter-service communication ✓

**What could be better:**
- Add `deploy.resources.limits` for CPU/memory per service (resource management)
- Add `logging` driver configuration (centralized logging)
- The `web-ui`, `oncall-service`, and `notification-service` builds will fail because
  their Dockerfiles/code are empty

---

### 2.4 CI/CD Pipelines

**What CI/CD means:**

- **CI (Continuous Integration)**: Every code push triggers automatic testing, linting,
  and security checks. The goal is to catch bugs early, before they reach production.

- **CD (Continuous Delivery/Deployment)**: After CI passes, automatically build container
  images and deploy them. The goal is to go from "code committed" to "running in production"
  with zero manual steps.

**The hackathon requires a pipeline with at least 4 stages:**

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌─────────┐    ┌──────────────┐
│ Code Quality │───►│   Security   │───►│    Build     │───►│ Deploy  │───►│   Verify     │
│  & Testing   │    │  Scanning    │    │   Images     │    │         │    │  (Post-Deploy)│
└─────────────┘    └──────────────┘    └──────────────┘    └─────────┘    └──────────────┘
```

1. **Code Quality & Testing**: Run linters (flake8, pylint), formatters (black), and
   unit tests with coverage. Fail the pipeline if coverage < 60%.

2. **Security Scanning**: Run tools like `gitleaks` or `trufflehog` to detect
   accidentally committed secrets (API keys, passwords). Fail if secrets found.

3. **Build Container Images**: `docker compose build`. Tag images with the git commit
   SHA for traceability (`myservice:abc123f`).

4. **Deploy**: `docker compose down && docker compose up -d`. Bring up the fresh stack.

5. **Post-Deployment Verification**: Hit every service's `/health` endpoint. If any
   fails, the pipeline fails and you know the deploy is broken.

**Current state:** `run-pipeline.sh` is **EMPTY** (0 bytes). This is a critical gap
worth up to 30 points.

**What a working pipeline would look like:**
```bash
#!/bin/bash
set -euo pipefail  # Exit on error, undefined vars, pipe failures

echo "═══ STAGE 1: Code Quality & Testing ═══"
cd services/alert-ingestion
pip install -r requirements.txt
flake8 main.py --max-line-length=120
pytest test_main.py -v --cov=main --cov-report=term --cov-fail-under=60
cd ../incident-management
pip install -r requirements.txt
flake8 main.py --max-line-length=120
pytest test_main.py -v --cov=main --cov-report=term --cov-fail-under=60
cd ../..

echo "═══ STAGE 2: Security Scanning ═══"
gitleaks detect --source=. --verbose
# Or: trufflehog filesystem --directory=.

echo "═══ STAGE 3: Build Container Images ═══"
COMMIT_SHA=$(git rev-parse --short HEAD)
docker compose build
# docker tag incident-platform-alert-ingestion:latest alert-ingestion:$COMMIT_SHA

echo "═══ STAGE 4: Deploy ═══"
docker compose down --remove-orphans || true
docker compose up -d

echo "═══ STAGE 5: Post-Deployment Verification ═══"
sleep 15
for port in 8001 8002 8003 8004 8080; do
    curl -sf http://localhost:$port/health || { echo "Service on port $port FAILED"; exit 1; }
done
echo "All services healthy! Pipeline PASSED ✅"
```

---

### 2.5 Observability: Monitoring, Metrics, Dashboards

**The Three Pillars of Observability:**

| Pillar      | What it captures                        | Tool in this project   |
|-------------|-----------------------------------------|------------------------|
| **Metrics** | Numeric time-series data (counters, gauges, histograms) | Prometheus |
| **Logs**    | Structured event records                | Structured JSON logging in services |
| **Traces**  | Request flow across services            | Not implemented (would use Jaeger/Zipkin) |

**How Prometheus works:**
```
Your Service             Prometheus             Grafana
┌──────────┐   scrape    ┌───────────┐   query   ┌─────────┐
│ /metrics  │◄───────────│  Collects  │◄──────────│  Shows   │
│ endpoint  │  (every    │  & stores  │  (PromQL) │  graphs  │
│           │   15s)     │  time-series│          │          │
└──────────┘            └───────────┘           └─────────┘
```

1. Each service exposes `GET /metrics` returning text in Prometheus format
2. Prometheus **pulls** (scrapes) those endpoints every 15 seconds
3. Data is stored as time-series in Prometheus's TSDB
4. Grafana connects to Prometheus and runs PromQL queries to build dashboards

**Metric types explained:**

| Type          | Use case                           | Example in project                  |
|---------------|------------------------------------|-------------------------------------|
| **Counter**   | Monotonically increasing value     | `alerts_received_total` — always goes up |
| **Gauge**     | Value that can go up or down       | `incidents_total{status="open"}` — goes up when created, down when resolved |
| **Histogram** | Distribution of values in buckets  | `incident_mtta_seconds` — "how many incidents had MTTA between 0-30s, 30-60s, 60-120s…" |

**Your metrics:**

| Metric                                    | Type      | Service              | What it measures                    |
|-------------------------------------------|-----------|----------------------|-------------------------------------|
| `alerts_received_total{severity}`         | Counter   | Alert Ingestion      | Total alerts received, by severity  |
| `alerts_correlated_total{result}`         | Counter   | Alert Ingestion      | How alerts were handled (new vs existing) |
| `alert_processing_seconds`               | Histogram | Alert Ingestion      | End-to-end processing latency       |
| `incidents_created_total{severity}`       | Counter   | Incident Management  | Incidents created, by severity      |
| `incidents_total{status}`                 | Gauge     | Incident Management  | Current count per status            |
| `incident_mtta_seconds`                   | Histogram | Incident Management  | Time-to-acknowledge distribution    |
| `incident_mttr_seconds`                   | Histogram | Incident Management  | Time-to-resolve distribution        |

**What you did well:**
- Both services expose `/metrics` in Prometheus format ✓
- Proper metric types (counters for totals, gauges for current state, histograms for latency) ✓
- Custom histogram buckets tuned to SRE use cases ✓
- Gauge bookkeeping (inc/dec) on status transitions ✓
- Two Grafana dashboards with 15 panels total ✓

**What could be better:**
- On-Call and Notification services have no metrics (they're empty)
- Add `up` monitoring in Grafana to show which services are alive
- Add alerting rules in Prometheus (`alert: ServiceDown, expr: up == 0`)

---

### 2.6 Infrastructure as Code (IaC)

**What it is:**
Instead of configuring servers manually (clicking around in UIs), you define your entire
infrastructure in **code files** that can be versioned, reviewed, and reproduced.

**In this project, IaC manifests itself as:**

| File                                  | What it defines                                    |
|---------------------------------------|----------------------------------------------------|
| `docker-compose.yml`                  | All 7 services, networks, volumes, health checks   |
| `database/init.sql`                   | Database schema — tables, indexes, triggers         |
| `monitoring/prometheus.yml`           | What to scrape and how often                        |
| `monitoring/grafana-provisioning/`    | Grafana datasources and dashboard locations         |
| `monitoring/grafana-dashboards/*.json`| Complete dashboard definitions as JSON              |
| `.env`                                | Environment-specific configuration                  |

**Why this matters:**
- Anyone can clone the repo and run `docker compose up -d` to get the exact same
  environment. No "it works on my machine" problems.
- Changes to infrastructure go through code review like any other code change.
- You can version control your dashboards, schemas, and configs.

**The DevOps principle:** "If it's not in code, it doesn't exist."

---

### 2.7 Security & Credentials Management

**The hackathon requires:**
1. No hardcoded passwords in code
2. Credentials scanning (gitleaks / trufflehog)
3. `.env` file in `.gitignore`
4. Non-root container users

**What you did:**
- ✅ Database credentials in `.env` file, referenced via `${POSTGRES_USER}` in compose
- ✅ Non-root user in Dockerfiles (`useradd -r -s /bin/false appuser`)
- ✅ `.dockerignore` excludes unnecessary files
- ❌ `.env` should be in `.gitignore` (check if it is!)
- ❌ No credentials scanning tool configured (no gitleaks, no trufflehog)
- ❌ No `.gitleaks.toml` configuration
- ❌ No pre-commit hooks

**Why this matters in the real world:**
Accidentally committing an AWS key to GitHub can cost thousands of dollars in minutes
(crypto miners scan public repos). Credential scanning catches this before it's pushed.

---

### 2.8 Testing & Code Quality

**Types of testing:**

| Type              | What it tests                          | Tool used        |
|-------------------|----------------------------------------|------------------|
| **Unit tests**    | Individual functions in isolation      | pytest           |
| **Integration tests** | Services working together          | curl / httpx     |
| **End-to-end tests** | Full user workflow (alert → resolve)| Manual / script  |

**Your test coverage:**

| Service              | Tests | Coverage | Required |
|----------------------|-------|----------|----------|
| Alert Ingestion      | 32    | 90%      | ≥ 60%   |
| Incident Management  | 33    | 91%      | ≥ 60%   |
| On-Call Service      | 0     | 0%       | ≥ 60%   |
| Notification Service | 0     | 0%       | ≥ 60%   |

**Testing approach used:**
Both test files use `unittest.mock.patch` to replace the SQLAlchemy engine with a mock.
This means tests run **without a database** — they're pure unit tests that verify:
- Request validation (bad severity, missing fields → 422)
- Business logic (correlation, state machine transitions)
- Database queries (correct SQL, correct parameters)
- Error handling (DB failures → 500)
- Edge cases (empty results, malformed UUIDs)

**What you did well:**
- 90%+ coverage far exceeds the 60% requirement ✓
- Tests cover happy paths AND error paths ✓
- Mock-based testing (fast, no external dependencies) ✓
- Tests run with `pytest -v --cov=main` ✓

**What could be better:**
- Add integration tests that test services end-to-end with a real database
- Add the on-call and notification service tests
- Add a test stage to the CI/CD pipeline that fails on < 60% coverage

---

### 2.9 SRE Metrics: MTTA & MTTR

**These are the golden signals of incident response:**

**MTTA (Mean Time To Acknowledge):**
- How long from "incident created" to "someone says I'm looking at it"
- Formula: `acknowledged_at - created_at` (in seconds)
- Measures: team responsiveness
- Good: < 5 minutes. Bad: > 30 minutes.

**MTTR (Mean Time To Resolve):**
- How long from "incident created" to "it's fixed"
- Formula: `resolved_at - created_at` (in seconds)
- Measures: team effectiveness
- Good: < 1 hour (for critical). Bad: > 4 hours.

**How it's implemented in your code:**

```python
# When status changes to 'acknowledged' or 'in_progress':
mtta = (now - created_at).total_seconds()
# Stored in DB: UPDATE incidents SET mtta_seconds = :mtta, acknowledged_at = :now

# When status changes to 'resolved':
mttr = (now - created_at).total_seconds()
# Stored in DB: UPDATE incidents SET mttr_seconds = :mttr, resolved_at = :now
```

**Smart detail:** If an incident goes directly from `open` → `resolved` (fast-track),
the code sets `mtta_seconds = mttr_seconds` because acknowledgment happened implicitly
at resolve time.

---

## 3. Architecture Deep-Dive

### End-to-End Data Flow

```
External Monitoring System
         │
         │ POST /api/v1/alerts
         │ {"service":"api","severity":"high","message":"5xx spike"}
         ▼
┌─────────────────────┐
│   ALERT INGESTION   │───── Compute SHA-256 fingerprint
│     (port 8001)     │───── Check: open incident for same service+severity in last 5 min?
│                     │
│  If YES ─────────────────► Attach alert to existing incident (DB write)
│  If NO  ─────────────────► POST to Incident Management to create new incident
│                     │       └─► If unreachable: create incident locally (fallback)
│                     │───── Store alert row in DB
│                     │───── Increment Prometheus counters
└─────────────────────┘

         │ POST /api/v1/incidents
         ▼
┌─────────────────────┐
│ INCIDENT MANAGEMENT │───── Create incident in DB
│     (port 8002)     │───── GET oncall-service → assign on-call engineer
│                     │───── POST notification-service → notify assignee
│                     │───── Record 'created' in timeline
│                     │
│  PATCH with status  │───── Enforce state machine (open→ack→in_progress→resolved)
│                     │───── Calculate MTTA on acknowledge
│                     │───── Calculate MTTR on resolve
│                     │───── Record every event in timeline
└─────────────────────┘

┌─────────────────────┐      ┌─────────────────────┐
│     ON-CALL         │      │   NOTIFICATION      │
│   (port 8003)       │      │   (port 8004)       │
│                     │      │                     │
│ NOT IMPLEMENTED     │      │ NOT IMPLEMENTED     │
└─────────────────────┘      └─────────────────────┘

┌─────────────────────┐
│   PostgreSQL        │◄──── Shared database
│   (port 5432)       │      Tables: incidents, alerts, incident_notes, incident_timeline
└─────────────────────┘

┌─────────────────────┐      ┌─────────────────────┐
│    PROMETHEUS       │      │     GRAFANA         │
│   (port 9090)       │─────►│   (port 3000)       │
│ Scrapes /metrics    │      │ Visualises metrics  │
│ every 15 seconds    │      │ 2 dashboards        │
└─────────────────────┘      └─────────────────────┘
```

### Database Entity-Relationship Model

```
┌──────────────┐       ┌──────────────┐
│   incidents  │◄──1:N─│    alerts     │
│              │       │              │
│ id (PK)      │       │ id (PK)      │
│ title        │       │ service      │
│ service      │       │ severity     │
│ severity     │       │ message      │
│ status       │       │ labels (JSON)│
│ assigned_to  │       │ fingerprint  │
│ alert_count  │       │ incident_id  │──FK──►
│ created_at   │       │ timestamp    │
│ updated_at   │       │ created_at   │
│ acknowledged_at│     └──────────────┘
│ resolved_at  │
│ mtta_seconds │       ┌──────────────────┐
│ mttr_seconds │◄──1:N─│ incident_notes   │
└──────────────┘       │ id, incident_id  │
       ▲               │ author, content  │
       │               │ created_at       │
       │ 1:N           └──────────────────┘
       │
┌──────────────────┐
│incident_timeline │
│ id, incident_id  │
│ event_type       │
│ actor            │
│ detail (JSON)    │
│ created_at       │
└──────────────────┘
```

**Design decisions worth understanding:**

1. **`alert_count` is denormalised**: Instead of running `SELECT COUNT(*) FROM alerts
   WHERE incident_id = X` every time (slow JOIN), the count is stored directly on the
   incident and updated atomically. This is a common performance optimisation.

2. **`incident_timeline` is append-only**: Events are never updated or deleted. This
   creates an immutable audit trail — critical for post-incident reviews.

3. **CHECK constraints**: The database enforces valid severities and statuses at the
   schema level. Even if the application had a bug, the DB wouldn't accept invalid data.

4. **Indexes on hot paths**: `idx_incidents_correlation` is a partial index
   (`WHERE status != 'resolved'`) — it only indexes non-resolved incidents, making
   correlation lookups extremely fast.

5. **`fn_set_updated_at()` trigger**: Every `UPDATE incidents` automatically refreshes
   `updated_at`. Application code doesn't need to remember to do this.

---

## 4. Component-by-Component Analysis

### 4.1 Database (PostgreSQL 15)

**Status: ✅ FULLY IMPLEMENTED**

| Aspect              | Implementation                                          |
|---------------------|---------------------------------------------------------|
| Image               | `postgres:15-alpine` (lightweight)                      |
| Schema              | 4 tables, 11+ indexes, 1 trigger, CHECK constraints    |
| Extensions          | `pgcrypto` for `gen_random_uuid()`                      |
| Initialisation      | `init.sql` mounted to `/docker-entrypoint-initdb.d/`    |
| Health check        | `pg_isready` (proper native check)                      |
| Persistence         | Named volume `db-data`                                  |

**Strengths:**
- Comprehensive schema with proper foreign keys, constraints, and table comments
- Partial indexes for performance-critical queries
- Trigger for automatic timestamp management
- pgcrypto for server-side UUID generation

---

### 4.2 Alert Ingestion Service (Port 8001)

**Status: ✅ FULLY IMPLEMENTED — 519 lines, 32 tests, 90% coverage**

**Endpoints:**
| Method | Path                   | Purpose                        |
|--------|------------------------|--------------------------------|
| POST   | `/api/v1/alerts`       | Ingest alert, correlate        |
| GET    | `/api/v1/alerts/{id}`  | Get single alert               |
| GET    | `/api/v1/alerts`       | List alerts (paginated)        |
| GET    | `/health`              | Liveness probe                 |
| GET    | `/health/ready`        | Readiness probe (DB check)     |
| GET    | `/metrics`             | Prometheus metrics              |

**Key implementation details:**

1. **Fingerprint deduplication**: SHA-256 hash of `service|severity|first_100_chars_of_message`.
   This creates a unique identifier for each distinct alert type, enabling dedup.

2. **Correlation algorithm**: Queries for open incidents matching the same `service`
   and `severity` within the last N minutes (configurable via `CORRELATION_WINDOW_MINUTES`).
   If found → attach alert to existing incident. If not → create new.

3. **Remote-first incident creation**: Tries to create the incident via HTTP to the
   Incident Management service. If that's down, falls back to local DB insert.
   This is a **resilience pattern** — graceful degradation.

4. **Structured JSON logging**: Every log line is a JSON object with timestamp, level,
   service name, message, and optional request_id. This makes logs searchable in
   production log aggregators (ELK, Loki, Datadog).

5. **Request ID middleware**: Every request gets a unique UUID (or uses the one from
   the `X-Request-ID` header). This enables **distributed tracing** — you can follow
   a single request across multiple services.

6. **Connection pool**: SQLAlchemy engine with `pool_size=10, max_overflow=5,
   pool_recycle=300`. This means up to 15 concurrent DB connections, recycled every
   5 minutes to prevent stale connection issues.

---

### 4.3 Incident Management Service (Port 8002)

**Status: ✅ FULLY IMPLEMENTED — 636 lines, 33 tests, 91% coverage**

**Endpoints:**
| Method | Path                                | Purpose                          |
|--------|-------------------------------------|----------------------------------|
| POST   | `/api/v1/incidents`                 | Create incident                  |
| GET    | `/api/v1/incidents`                 | List incidents (paginated)       |
| GET    | `/api/v1/incidents/{id}`            | Full detail + alerts + timeline  |
| PATCH  | `/api/v1/incidents/{id}`            | Update status / assign / note    |
| GET    | `/api/v1/incidents/{id}/metrics`    | MTTA & MTTR for one incident     |
| GET    | `/api/v1/incidents/stats/summary`   | Aggregate stats                  |
| GET    | `/health`, `/health/ready`          | Health probes                    |
| GET    | `/metrics`                          | Prometheus metrics                |

**Key implementation details:**

1. **Status state machine**: Enforces valid transitions with `ALLOWED_TRANSITIONS` dict.
   ```
   open → acknowledged, in_progress, resolved
   acknowledged → in_progress, resolved
   in_progress → resolved
   resolved → (nothing — terminal state)
   ```
   Illegal transitions return `HTTP 409 Conflict` with a clear error message.

2. **MTTA calculation**: Triggered on first transition to `acknowledged` or `in_progress`.
   Records `acknowledged_at` timestamp and computes `mtta_seconds = now - created_at`.

3. **MTTR calculation**: Triggered on transition to `resolved`. Records `resolved_at`
   and computes `mttr_seconds = now - created_at`. Special case: if going from `open`
   directly to `resolved`, `mtta = mttr` (auto-acknowledge).

4. **Prometheus gauge management**: On every status change, the old status gauge is
   decremented and the new status gauge is incremented. This keeps the gauges accurate.

5. **On-call integration**: On incident creation, calls the on-call service to look up
   who's currently on-call for the affected team/service. Falls back gracefully if the
   on-call service is down.

6. **Notification fire-and-forget**: After assignment, fires a notification to the
   notification service. Uses `try/except` to prevent notification failures from breaking
   incident creation.

7. **Rich incident detail**: GET single incident returns the incident + all linked alerts +
   all notes + the complete timeline. This is the data a frontend dashboard would display.

---

### 4.4 On-Call Service (Port 8003)

**Status: ❌ NOT IMPLEMENTED — `main.py` is 0 bytes**

**What it should do:**
- Manage rotation schedules (which engineers rotate on-call duties)
- Determine who is currently on-call based on the current week
- Handle escalations when the primary on-call doesn't respond
- Formula: `member_index = week_of_year % number_of_primary_members`

**Impact of being missing:**
- The incident management service calls this on incident creation
- Currently gets a `ConnectError` and falls back to `assigned_to = None`
- Loses points in "Platform Functionality" and "Architecture & Design"

---

### 4.5 Notification Service (Port 8004)

**Status: ❌ NOT IMPLEMENTED — `main.py` is 0 bytes**

**What it should do:**
- Accept `POST /api/v1/notify` requests
- Log the notification (mocking is acceptable for the hackathon)
- Expose notification metrics

**Impact of being missing:**
- Incident creation silently swallows the error (fire-and-forget pattern)
- Loses points, but less critical since mock notifications are acceptable

---

### 4.6 Web UI (Port 8080)

**Status: ❌ NOT IMPLEMENTED — Dockerfile is 0 bytes**

**What it should be:**
- A web dashboard showing open incidents, allowing acknowledge/resolve
- Could be as simple as static HTML + JavaScript served by Nginx
- Pages: Dashboard, Incident Detail, On-Call Schedule, SRE Metrics

**Impact of being missing:**
- Judges can't visually interact with the platform
- Must use curl/API calls instead — worse demo experience

---

### 4.7 Prometheus (Port 9090)

**Status: ✅ PARTIALLY WORKING**

- Successfully scrapes alert-ingestion and incident-management
- `oncall-service` and `web-ui` targets show as DOWN (services not implemented)
- Scrape interval: 15 seconds

---

### 4.8 Grafana (Port 3000)

**Status: ✅ WORKING — 2 dashboards provisioned**

**Dashboard 1 — Incident Overview (8 panels):**
- Total Alerts Received (stat)
- Total Incidents Created (stat)
- Open Incidents (stat, red background)
- Resolved Incidents (stat, green background)
- Alerts by Severity over time (time series)
- Incidents by Status over time (time series)
- Alert Correlation Outcomes (bar chart)
- Alert Processing Latency p50/p95/p99 (time series)

**Dashboard 2 — SRE Performance (7 panels):**
- Current MTTA p50 (stat, yellow thresholds)
- Current MTTR p50 (stat, orange thresholds)
- Incidents by Severity (stat)
- MTTA Distribution over time
- MTTR Distribution over time
- Incident Status Breakdown (bar chart)
- Incident Creation Rate by Severity (time series)

---

### 4.9 CI/CD Pipeline

**Status: ❌ NOT IMPLEMENTED — `run-pipeline.sh` is 0 bytes**

This is one of the highest-value missing components (part of the 30-point DevOps category).

---

## 5. Docker & Dockerfile Best Practices Analysis

### What you nailed:

| Best Practice                  | Status | Notes                                      |
|-------------------------------|--------|--------------------------------------------|
| Multi-stage builds            | ✅     | Builder + runtime stages                   |
| Slim/small base images        | ✅     | `python:3.11-slim`                         |
| Non-root user                 | ✅     | `appuser` with no shell                    |
| HEALTHCHECK instruction       | ✅     | curl-based with intervals                  |
| .dockerignore                 | ✅     | Excludes __pycache__, .git, venv           |
| No COPY of secrets            | ✅     | Secrets via environment variables           |
| Single CMD instruction        | ✅     | `uvicorn main:app` — clear entrypoint      |
| WORKDIR set                   | ✅     | `/app` — not running from root             |

### What could improve:

| Improvement                           | Why                                              |
|---------------------------------------|--------------------------------------------------|
| Pin exact image tags                  | `python:3.11.7-slim-bookworm` for reproducibility |
| Add `LABEL` instructions             | `maintainer`, `version`, `description` metadata   |
| Use `COPY --chown=appuser:appuser`   | Avoid separate chown step                         |
| Add `--no-cache` to apt-get          | Smaller image                                     |
| Scan images with `trivy`             | Find CVEs in base images                          |

---

## 6. Testing Analysis

### Test Architecture (Both Services)

```python
# Tests use unittest.mock to replace the database engine:
@patch("main.engine")
def test_create_alert_success(self, mock_engine):
    mock_conn = MagicMock()
    mock_engine.begin.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.execute.return_value.fetchone.return_value = None  # No existing incident
    # ... test the endpoint
```

This approach:
- **Fast** — no database needed, tests run in milliseconds
- **Isolated** — each test is independent, no shared state
- **Deterministic** — no network or DB flakiness

### Coverage Breakdown

**Alert Ingestion (32 tests, 90%):**
- ✅ Alert creation with correlation
- ✅ Attach to existing incident
- ✅ Remote incident creation
- ✅ Local fallback when remote is down
- ✅ Validation errors (bad severity, missing fields)
- ✅ Fingerprint computation
- ✅ Pagination with filters
- ✅ Health and readiness endpoints
- ✅ 404 for missing alerts
- ✅ Database error handling

**Incident Management (33 tests, 91%):**
- ✅ Incident creation with on-call lookup
- ✅ List with pagination and filters
- ✅ Full detail retrieval (alerts + notes + timeline)
- ✅ Status transitions (all valid paths)
- ✅ Illegal transitions → 409
- ✅ MTTA and MTTR calculation
- ✅ Note addition with timeline entries
- ✅ Reassignment
- ✅ Summary statistics
- ✅ Per-incident metrics endpoint

### The Bug That Was Fixed

Two tests (`test_acknowledge_from_open`, `test_resolve_from_open_fast_track`) were
failing because the mock `side_effect` arrays had too many `None` entries. The
`update_incident` function makes exactly 4 `conn.execute` calls during a status update:

1. `SELECT` current incident state
2. `INSERT` timeline event
3. `UPDATE` incident with new status
4. `SELECT` updated incident

The mocks had 5-6 entries, pushing the final `fetchone` mock out of position, causing
`AttributeError: 'NoneType' object has no attribute 'fetchone'`. Fix: reduce side_effect
arrays to exactly 4 entries.

---

## 7. Monitoring Stack Analysis

### Prometheus Configuration

```yaml
global:
  scrape_interval: 15s  # How often Prometheus pulls metrics

scrape_configs:
  - job_name: 'alert-ingestion'
    static_configs:
      - targets: ['alert-ingestion:8001']
  - job_name: 'incident-management'
    static_configs:
      - targets: ['incident-management:8002']
  - job_name: 'oncall-service'
    static_configs:
      - targets: ['oncall-service:8003']    # Currently DOWN
  - job_name: 'web-ui'
    static_configs:
      - targets: ['web-ui:8080']            # Currently DOWN
```

### Grafana Provisioning

The Grafana setup uses **provisioning** — dashboards and datasources are defined in
files, not created manually in the UI:

```
monitoring/
├── grafana-provisioning/
│   ├── dashboards/
│   │   └── dashboards.yml        # Tells Grafana where to find dashboard JSONs
│   └── datasources/
│       └── datasources.yml       # Connects Grafana to Prometheus
└── grafana-dashboards/
    ├── incident-overview.json    # Dashboard 1: 8 panels
    └── sre-performance.json      # Dashboard 2: 7 panels
```

This is IaC for dashboards — they're version-controlled and reproducible.

### PromQL Queries in Dashboards

Some example queries used in the dashboards:

| What it shows                      | PromQL                                               |
|------------------------------------|------------------------------------------------------|
| Total alerts received              | `sum(alerts_received_total)`                         |
| Alerts by severity over time       | `rate(alerts_received_total[5m])`                    |
| Processing latency p50             | `histogram_quantile(0.50, rate(alert_processing_seconds_bucket[5m]))` |
| Open incidents right now           | `incidents_total{status="open"}`                     |
| MTTA p50                           | `histogram_quantile(0.50, rate(incident_mtta_seconds_bucket[5m]))` |

---

## 8. Security Analysis

### What's in place:

| Security measure                    | Status | Notes                              |
|------------------------------------|--------|------------------------------------|
| Credentials in .env (not code)     | ✅     | `${POSTGRES_PASSWORD}` referenced  |
| Non-root Docker user               | ✅     | `appuser` with restricted shell    |
| CORS middleware                     | ⚠️     | `allow_origins=["*"]` is too open  |
| Input validation                   | ✅     | Pydantic field validators          |
| SQL injection prevention           | ✅     | Parameterised queries with `:param`|
| UUID validation                    | ✅     | Rejects malformed IDs              |

### What's missing:

| Security measure                    | Status | Fix                                       |
|------------------------------------|--------|-------------------------------------------|
| Credential scanning (gitleaks)     | ❌     | Install gitleaks, add to pipeline          |
| .gitleaks.toml config             | ❌     | Create configuration file                  |
| Rate limiting                      | ❌     | Add slowapi or nginx rate limiting         |
| API authentication                 | ❌     | API keys or JWT tokens                     |
| HTTPS/TLS                         | ❌     | Not expected for hackathon, but worth noting |
| Image vulnerability scanning       | ❌     | `trivy image <image_name>`                 |
| CORS restriction                   | ⚠️     | Change `*` to specific frontend origin     |

---

## 9. Scoring Estimate Against the Rubric

### Rubric Breakdown (100 points total)

| Category                         | Max | Estimated | Reasoning                                    |
|----------------------------------|-----|-----------|----------------------------------------------|
| **Platform Functionality (30)**  |     |           |                                              |
| - Alert ingestion & correlation  | ~8  | 7-8       | Fully working, smart correlation              |
| - Incident lifecycle & MTTA/MTTR | ~8  | 7-8       | Full state machine, auto-calculation          |
| - On-call & scheduling          | ~7  | 0-1       | Empty — no implementation                     |
| - Notification                   | ~3  | 0         | Empty                                         |
| - Web UI & end-to-end flow      | ~4  | 0         | Empty                                         |
| **Subtotal**                     | 30  | **14-17** |                                              |
|                                  |     |           |                                              |
| **DevOps Implementation (30)**   |     |           |                                              |
| - Docker quality (multi-stage, non-root, healthcheck) | ~8  | 7-8 | Excellent Dockerfiles |
| - docker-compose.yml             | ~7  | 6-7       | Complete but 3 services won't start          |
| - CI/CD pipeline (4+ stages)    | ~10 | 0-1       | Empty run-pipeline.sh                         |
| - IaC approach                   | ~5  | 4         | Good use of provisioning files                |
| **Subtotal**                     | 30  | **17-20** |                                              |
|                                  |     |           |                                              |
| **Monitoring & SRE (20)**        |     |           |                                              |
| - Prometheus integration         | ~8  | 6         | 2 of 4 services scraped                      |
| - Grafana dashboards             | ~8  | 7         | 2 provisioned dashboards, 15 panels          |
| - SRE metrics (MTTA/MTTR)       | ~4  | 4         | Fully implemented with histograms            |
| **Subtotal**                     | 20  | **17**    |                                              |
|                                  |     |           |                                              |
| **Architecture & Design (15)**   |     |           |                                              |
| - Clean API design               | ~5  | 5         | RESTful, versioned, documented               |
| - Service separation             | ~5  | 3-4       | 2 real services, 3 empty                     |
| - Code quality                   | ~5  | 4         | Good structure, logging, error handling      |
| **Subtotal**                     | 15  | **12-13** |                                              |
|                                  |     |           |                                              |
| **Security & Quality (5)**       |     |           |                                              |
| - Credential scanning            | ~2  | 0         | Not implemented                               |
| - Test coverage ≥60%             | ~2  | 1         | 2 services pass, 2 have 0%                   |
| - Code quality gates             | ~1  | 0         | No linter in pipeline                         |
| **Subtotal**                     | 5   | **1**     |                                              |

### **Estimated Total: ~61-68 / 100**

### The fastest ways to gain points:

| Action                                      | Time needed | Points gained |
|---------------------------------------------|-------------|---------------|
| Implement `run-pipeline.sh` (5 stages)     | 1-2 hours   | +8-10         |
| Stub On-Call Service (health + basic API)  | 1-2 hours   | +5-7          |
| Stub Notification Service (health + mock)  | 30 min      | +2-3          |
| Add gitleaks to pipeline                   | 30 min      | +1-2          |
| Stub Web UI (Nginx serving static HTML)    | 1-2 hours   | +3-4          |

**Implementing just the pipeline and stubs could push you to 80-85/100.**

---

## 10. Gap Analysis — What's Missing & Priorities

### Priority 1: CRITICAL (highest point value)

| Gap                      | Files affected              | Points at risk |
|--------------------------|-----------------------------|----------------|
| CI/CD Pipeline           | `run-pipeline.sh`           | ~10 points     |
| On-Call Service          | `services/oncall-service/main.py` | ~7 points |

### Priority 2: HIGH

| Gap                      | Files affected              | Points at risk |
|--------------------------|-----------------------------|----------------|
| Notification Service     | `services/notification-service/main.py` | ~3 points |
| Web UI                  | `services/web-ui/`          | ~4 points      |
| Credentials scanning     | `.gitleaks.toml`, pipeline  | ~2 points      |

### Priority 3: NICE-TO-HAVE

| Gap                      | Notes                              |
|--------------------------|---------------------------------------|
| Integration tests        | Real DB tests in pipeline             |
| Rate limiting            | Prevent abuse                         |
| API authentication      | JWT or API key                        |
| Distributed tracing     | Jaeger integration                    |
| Log aggregation          | Loki or ELK stack                     |
| Resource limits          | CPU/memory limits in compose          |
| Image scanning           | `trivy` in pipeline                   |

---

## 11. Concrete Improvement Plan

### Phase 1: CI/CD Pipeline (Highest ROI — ~10 points)

Create `run-pipeline.sh` with 5 stages:

```bash
#!/bin/bash
set -euo pipefail

echo "═══════════════════════════════════════"
echo "  STAGE 1: Code Quality & Testing"
echo "═══════════════════════════════════════"
pip install flake8 pytest pytest-cov

for service in alert-ingestion incident-management; do
    echo "Testing $service..."
    cd services/$service
    flake8 main.py --max-line-length=120 --ignore=E501,W503
    pytest test_main.py -v --cov=main --cov-fail-under=60
    cd ../..
done

echo "═══════════════════════════════════════"
echo "  STAGE 2: Security Scanning"
echo "═══════════════════════════════════════"
if command -v gitleaks &> /dev/null; then
    gitleaks detect --source=. --verbose
else
    echo "WARNING: gitleaks not installed, skipping"
fi

echo "═══════════════════════════════════════"
echo "  STAGE 3: Build Container Images"
echo "═══════════════════════════════════════"
docker compose build --parallel

echo "═══════════════════════════════════════"
echo "  STAGE 4: Deploy"
echo "═══════════════════════════════════════"
docker compose down --remove-orphans 2>/dev/null || true
docker compose up -d

echo "═══════════════════════════════════════"
echo "  STAGE 5: Post-Deployment Verification"
echo "═══════════════════════════════════════"
echo "Waiting for services to initialize..."
sleep 20

FAILED=0
for endpoint in "8001/health" "8002/health"; do
    if curl -sf "http://localhost:$endpoint" > /dev/null; then
        echo "✓ localhost:$endpoint"
    else
        echo "✗ localhost:$endpoint FAILED"
        FAILED=1
    fi
done

if [ $FAILED -eq 0 ]; then
    echo "═══════════════════════════════════════"
    echo "  PIPELINE PASSED ✅"
    echo "═══════════════════════════════════════"
else
    echo "  PIPELINE FAILED ❌"
    exit 1
fi
```

### Phase 2: Stub On-Call Service (~7 points)

A minimal implementation that fulfills the API contract:

```python
from fastapi import FastAPI
from datetime import datetime

app = FastAPI(title="On-Call Service")

SCHEDULES = {}  # In-memory store

@app.post("/api/v1/schedules")
def create_schedule(body: dict):
    team = body["team"]
    SCHEDULES[team] = body
    return {"status": "created", "team": team}

@app.get("/api/v1/schedules")
def list_schedules():
    return list(SCHEDULES.values())

@app.get("/api/v1/oncall/current")
def get_current_oncall(team: str = "default"):
    schedule = SCHEDULES.get(team)
    if not schedule:
        return {"team": team, "primary": {"name": "Default Engineer", "email": "engineer@example.com"}}
    primaries = [m for m in schedule.get("members", []) if m.get("role") == "primary"]
    week = datetime.now().isocalendar()[1]
    idx = week % len(primaries) if primaries else 0
    return {"team": team, "primary": primaries[idx] if primaries else None}

@app.get("/health")
def health():
    return {"status": "ok", "service": "oncall-service"}

@app.get("/metrics")
def metrics():
    return "# No metrics yet\n"
```

### Phase 3: Stub Notification Service (~3 points)

```python
from fastapi import FastAPI
import logging

app = FastAPI(title="Notification Service")
logger = logging.getLogger("notification-service")

@app.post("/api/v1/notify")
def notify(body: dict):
    logger.info(f"NOTIFICATION: [{body.get('channel')}] to {body.get('recipient')}: {body.get('message')}")
    return {"status": "sent", "channel": body.get("channel", "mock")}

@app.get("/health")
def health():
    return {"status": "ok", "service": "notification-service"}

@app.get("/metrics")
def metrics():
    return "# No metrics yet\n"
```

---

## 12. Thinking Like a DevOps / Automation Engineer

### The Core Mindset Shift

A DevOps engineer doesn't think "how do I write code?" — they think:

1. **"How do I make this repeatable?"**
   - Don't configure anything by hand. Put it in a file (YAML, JSON, SQL, Dockerfile).
   - If you had to set up this project on a brand new laptop, could you do it with
     one command? (`docker compose up -d`)

2. **"How do I know if it's broken?"**
   - Every service needs health endpoints
   - Every operation needs metrics
   - Every dashboard needs to answer: "Is everything OK right now?"

3. **"How do I prevent bad code from reaching production?"**
   - CI pipeline: lint → test → security scan → build → deploy → verify
   - If any stage fails, **the pipeline stops**. Bad code never gets deployed.

4. **"How do I recover when things go wrong?"**
   - `restart: unless-stopped` — containers self-heal
   - Fallback patterns — when service B is down, service A still works
   - Immutable timeline — "What happened and when?"

5. **"How do I scale without being there?"**
   - Automation > manual process, always
   - If you're doing the same task twice, automate it

### The Automation Pyramid

```
        ┌─────────────┐
        │   Incidents  │  ◄── You investigate these
        │   (Manual)   │
        ├─────────────┤
        │   Alerts     │  ◄── Prometheus detects these
        │ (Automated)  │
        ├─────────────────┤
        │   Monitoring     │  ◄── Dashboards show these
        │   metrics        │
        ├─────────────────────┤
        │   Health checks       │  ◄── Compose/K8s checks these
        ├───────────────────────────┤
        │   CI/CD Pipeline              │  ◄── Prevents bad deploys
        ├───────────────────────────────────┤
        │   Infrastructure as Code              │  ◄── Reproducible environments
        └───────────────────────────────────────┘
```

The more you automate at the bottom, the less firefighting at the top.

### Key DevOps Principles Applied in This Project

| Principle                    | How it's applied                                           |
|------------------------------|------------------------------------------------------------|
| **Everything as Code**       | Compose, SQL schema, Prometheus config, Grafana dashboards  |
| **Automate Everything**      | One command to deploy: `docker compose up -d`              |
| **Measure Everything**       | Prometheus metrics on every service, MTTA/MTTR tracking     |
| **Fail Fast**                | Validation at API boundary, health checks, state machine    |
| **Graceful Degradation**     | Alert service works even if incident service is down        |
| **Immutable Audit Trail**    | `incident_timeline` table records every event               |
| **Separation of Concerns**   | Each service does one thing well                            |
| **12-Factor App**            | Config in env vars, stateless processes, port binding       |

### The 12-Factor App Checklist (Industry Standard)

| Factor                    | Status | Implementation                              |
|---------------------------|--------|---------------------------------------------|
| 1. Codebase               | ✅     | One repo tracked in Git                     |
| 2. Dependencies            | ✅     | Explicitly declared in requirements.txt     |
| 3. Config                  | ✅     | Environment variables via .env              |
| 4. Backing services        | ✅     | PostgreSQL as attached resource              |
| 5. Build, release, run     | ⚠️     | Docker build exists, CI/CD missing          |
| 6. Processes               | ✅     | Stateless services (state in DB)            |
| 7. Port binding            | ✅     | Each service binds its own port             |
| 8. Concurrency             | ✅     | Horizontal scaling via Compose replicas     |
| 9. Disposability           | ✅     | Fast startup, graceful shutdown (lifespan)  |
| 10. Dev/prod parity        | ✅     | Same Docker images in dev and "prod"        |
| 11. Logs                   | ✅     | Structured JSON to stdout                   |
| 12. Admin processes        | ⚠️     | DB migrations via init.sql (manual)         |

### What to Study Next

If you want to grow from here into a DevOps career:

1. **Kubernetes**: Docker Compose, but for production. Handles scaling, rolling deploys,
   service discovery, secrets management at scale. (This project is Compose-only, but
   the concepts transfer directly.)

2. **Terraform / Pulumi**: IaC for cloud infrastructure (AWS, GCP, Azure). Instead of
   clicking in the AWS console, you write code that creates VPCs, load balancers, databases.

3. **GitHub Actions / GitLab CI**: Real CI/CD platforms. Your `run-pipeline.sh` is a
   simplified version of what GitHub Actions does with YAML workflows.

4. **Prometheus Alerting Rules**: Instead of just visualising metrics, configure
   Prometheus to fire alerts when things go wrong (e.g., `alert: HighErrorRate`).

5. **Service Mesh (Istio/Linkerd)**: Advanced networking between microservices — mTLS,
   traffic splitting, circuit breaking.

6. **Chaos Engineering**: Intentionally breaking things to test resilience (Netflix's
   Chaos Monkey concept).

---

## Summary

### What was built well:
- Two production-quality microservices with comprehensive APIs
- Robust database schema with performance optimizations
- Proper containerization following Docker best practices
- Working monitoring stack with Prometheus + Grafana + provisioned dashboards
- 90%+ test coverage on core services
- Graceful degradation and fallback patterns
- Structured logging and request tracing
- Status state machine with MTTA/MTTR calculation

### What needs work:
- 3 of 5 services are empty (on-call, notification, web UI)
- CI/CD pipeline is empty (single highest-impact gap)
- No credentials scanning
- No code quality gates in automation

### The bottom line:
The **core is solid** — the two implemented services are genuinely well-built with
proper error handling, metrics, logging, testing, and resilience patterns. The gap is
in **breadth, not depth**. Filling in the stubs (even minimal implementations) and
creating the CI/CD pipeline would dramatically improve the score from ~65 to ~85+.

---

*Document generated for project analysis. Last updated: 2025.*
