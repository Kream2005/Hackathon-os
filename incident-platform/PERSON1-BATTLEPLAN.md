# PERSON 1 BATTLE PLAN: From 0 to 100

## CURRENT STATE AUDIT

### DONE (Infrastructure/Skeleton)
| File | Status |
|------|--------|
| `docker-compose.yml` | COMPLETE - all 7 services defined, healthchecks, networks, volumes |
| `database/init.sql` | COMPLETE - alerts, incidents, incident_notes tables with indexes |
| `.env` | COMPLETE - all env vars defined |
| `.gitignore` | COMPLETE |
| `monitoring/prometheus.yml` | COMPLETE - scrapes all 4 services |
| `monitoring/grafana-provisioning/` | COMPLETE - datasource + dashboard provider |
| `services/alert-ingestion/Dockerfile` | COMPLETE - multi-stage, non-root, healthcheck |
| `services/alert-ingestion/requirements.txt` | COMPLETE |
| `services/incident-management/Dockerfile` | COMPLETE - multi-stage, non-root, healthcheck |
| `services/incident-management/requirements.txt` | COMPLETE |

### NOT DONE (All Code is EMPTY)
| File | Status | Priority |
|------|--------|----------|
| `services/alert-ingestion/main.py` | **EMPTY** | CRITICAL |
| `services/incident-management/main.py` | **EMPTY** | CRITICAL |
| `services/oncall-service/main.py` | **EMPTY** | HIGH (Person 2's job but you need it working) |
| `services/oncall-service/Dockerfile` | **EMPTY** | HIGH |
| `services/oncall-service/requirements.txt` | **EMPTY** | HIGH |
| `services/notification-service/main.py` | **EMPTY** | MEDIUM |
| `services/notification-service/Dockerfile` | **EMPTY** | MEDIUM |
| `services/notification-service/requirements.txt` | **EMPTY** | MEDIUM |
| `services/web-ui/Dockerfile` | **EMPTY** | HIGH (Person 3's job) |
| `services/web-ui/` (no frontend code) | **MISSING** | HIGH (Person 3's job) |
| `monitoring/grafana-dashboards/incident-overview.json` | **EMPTY** | HIGH |
| `monitoring/grafana-dashboards/sre-performance.json` | **EMPTY** | HIGH |
| `run-pipeline.sh` | **EMPTY** | HIGH (Person 2's job) |
| `README.md` | **EMPTY** | HIGH (Person 3's job) |

---

## YOUR TASK AS PERSON 1 - DETAILED STEP-BY-STEP

You own: **Alert Ingestion Service**, **Incident Management Service**, **Database**
This is worth **most of the 30 Platform Functionality points** + contributes to Architecture (15 pts).

---

## PHASE 1: Alert Ingestion Service (services/alert-ingestion/main.py)
**Time estimate: 60-90 minutes | Priority: CRITICAL**

### What to build:
A FastAPI application on port 8001 with these endpoints:

#### Endpoint 1: `GET /health`
```python
# Returns: {"status": "ok", "service": "alert-ingestion"}
# HTTP 200
```

#### Endpoint 2: `GET /metrics`
```python
# Returns Prometheus-format text metrics:
# alerts_received_total{severity="critical"} 5
# alerts_received_total{severity="high"} 12
# alerts_correlated_total{result="new_incident"} 8
# alerts_correlated_total{result="existing_incident"} 4
```

#### Endpoint 3: `POST /api/v1/alerts`
This is the CORE endpoint. Here's the exact logic:

```
1. Receive JSON body: {service, severity, message, labels (optional), timestamp (optional)}
2. VALIDATE:
   - service: required, string
   - severity: required, must be one of: critical, high, medium, low
   - message: required, string
   - If validation fails: return 422 with error details
3. CORRELATE:
   - Query DB: SELECT * FROM incidents WHERE service = {alert.service} 
     AND severity = {alert.severity} AND status != 'resolved' 
     AND created_at > NOW() - INTERVAL '5 minutes'
   - If found: attach alert to EXISTING incident (set alert.incident_id = existing incident id)
   - If NOT found: create NEW incident via Incident Management Service 
     (POST http://incident-management:8002/api/v1/incidents)
4. Store alert in DB
5. Update Prometheus counters
6. Return response with alert_id, incident_id, status, action
```

**Request body example:**
```json
{
  "service": "frontend-api",
  "severity": "high",
  "message": "HTTP 5xx error rate > 10%",
  "labels": {"environment": "production", "region": "us-east-1"},
  "timestamp": "2026-02-09T15:30:00Z"
}
```

**Response example:**
```json
{
  "alert_id": "uuid-here",
  "incident_id": "uuid-here",
  "status": "correlated",
  "action": "new_incident"  // or "attached_to_existing_incident"
}
```

#### Endpoint 4: `GET /api/v1/alerts/{alert_id}`
```
- Query DB for alert by ID
- Return alert data + linked incident_id
- 404 if not found
```

### Technical implementation details:
- Use **SQLAlchemy** for DB access (async with asyncpg, or sync with psycopg2)
- Use **prometheus_client** library for metrics (Counter, generate_latest)
- Use **httpx** for calling incident-management service
- Use **pydantic** BaseModel for request/response validation
- Database URL from env var: `DATABASE_URL`
- Incident management URL from env var: `INCIDENT_MANAGEMENT_URL`

### Prometheus metrics to expose:
```python
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

alerts_received = Counter('alerts_received_total', 'Total alerts received', ['severity'])
alerts_correlated = Counter('alerts_correlated_total', 'Alert correlation results', ['result'])
```

### Files to create/edit:
1. `services/alert-ingestion/main.py` - THE MAIN FILE
2. (optional) `services/alert-ingestion/.dockerignore` - add `__pycache__`, `*.pyc`, `.pytest_cache`, `venv`

---

## PHASE 2: Incident Management Service (services/incident-management/main.py)
**Time estimate: 90-120 minutes | Priority: CRITICAL**

### What to build:
A FastAPI application on port 8002 with these endpoints:

#### Endpoint 1: `GET /health`
```python
# Returns: {"status": "ok", "service": "incident-management"}
```

#### Endpoint 2: `GET /metrics`
```python
# Prometheus format:
# incidents_total{status="open"} 5
# incidents_total{status="acknowledged"} 3
# incidents_total{status="resolved"} 10
# incident_mtta_seconds_bucket{le="60"} 2
# incident_mttr_seconds_bucket{le="300"} 5
# (histogram format)
```

#### Endpoint 3: `POST /api/v1/incidents`
```
1. Receive: {title, service, severity, assigned_to (optional)}
2. Store in incidents table with status='open', created_at=NOW()
3. Try to call On-Call Service: GET http://oncall-service:8003/api/v1/oncall/current?team={service}
   - If succeeds: set assigned_to = on-call engineer name
   - If fails (service not ready): leave assigned_to as null (DON'T crash!)
4. Try to call Notification Service: POST http://notification-service:8004/api/v1/notify
   - If fails: log warning but DON'T crash
5. Return the created incident with 201 status
```

#### Endpoint 4: `GET /api/v1/incidents`
```
- List all incidents
- Support query params: ?status=open&severity=high&service=frontend-api
- Return array of incidents
- Order by created_at DESC
```

#### Endpoint 5: `GET /api/v1/incidents/{incident_id}`
```
- Get single incident by UUID
- Include: linked alerts (query alerts table WHERE incident_id = this)
- Include: notes (query incident_notes table)
- Include: computed MTTA and MTTR
- 404 if not found
```

#### Endpoint 6: `PATCH /api/v1/incidents/{incident_id}`
This is CRITICAL for the demo flow. Handles status transitions and notes.

```
Request body (all optional):
{
  "status": "acknowledged",  // open -> acknowledged -> in_progress -> resolved
  "notes": "Looking into this issue"
}

Logic:
1. If status changed to "acknowledged":
   - Set acknowledged_at = NOW()
   - Calculate mtta_seconds = (acknowledged_at - created_at).total_seconds()
2. If status changed to "resolved":
   - Set resolved_at = NOW()
   - Calculate mttr_seconds = (resolved_at - created_at).total_seconds()
   - Record in histogram metric
3. If notes provided:
   - Insert into incident_notes table
4. Update the incident row
5. Return updated incident
```

#### Endpoint 7: `GET /api/v1/incidents/{incident_id}/metrics`
```
- Return MTTA and MTTR for this specific incident
- Just a convenience endpoint
```

### Prometheus metrics to expose:
```python
from prometheus_client import Counter, Gauge, Histogram

incidents_total = Gauge('incidents_total', 'Total incidents by status', ['status'])
incident_mtta = Histogram('incident_mtta_seconds', 'Time to acknowledge', 
                          buckets=[30, 60, 120, 300, 600, 1800, 3600])
incident_mttr = Histogram('incident_mttr_seconds', 'Time to resolve',
                          buckets=[60, 300, 600, 1800, 3600, 7200, 14400])
```

### Technical details:
- Same stack: FastAPI + SQLAlchemy + prometheus_client + httpx
- Env vars: `DATABASE_URL`, `ONCALL_SERVICE_URL`, `NOTIFICATION_SERVICE_URL`
- IMPORTANT: When calling other services (oncall, notification), wrap in try/except so your service doesn't crash if they're not ready yet

### Files to create/edit:
1. `services/incident-management/main.py`
2. (optional) `services/incident-management/.dockerignore`

---

## PHASE 3: Quick Integration Test
**Time estimate: 15-20 minutes**

Before moving forward, test your two services work:

```bash
# Start just database + your two services
docker compose up -d database
# Wait 10 seconds for DB to be ready
docker compose up -d alert-ingestion incident-management

# Test health
curl http://localhost:8001/health
curl http://localhost:8002/health

# Test metrics
curl http://localhost:8001/metrics
curl http://localhost:8002/metrics

# Create incident manually
curl -X POST http://localhost:8002/api/v1/incidents \
  -H "Content-Type: application/json" \
  -d '{"title":"Test incident","service":"api","severity":"high"}'

# List incidents
curl http://localhost:8002/api/v1/incidents

# Send test alert (triggers correlation + auto-incident creation)
curl -X POST http://localhost:8001/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '{"service":"frontend-api","severity":"high","message":"Test alert","labels":{"env":"prod"}}'

# Acknowledge an incident (replace UUID)
curl -X PATCH http://localhost:8002/api/v1/incidents/{INCIDENT_UUID} \
  -H "Content-Type: application/json" \
  -d '{"status":"acknowledged"}'

# Resolve it
curl -X PATCH http://localhost:8002/api/v1/incidents/{INCIDENT_UUID} \
  -H "Content-Type: application/json" \
  -d '{"status":"resolved"}'

# Check metrics again (should show MTTA/MTTR)
curl http://localhost:8002/metrics
```

If these all work, your Person 1 core deliverables are 80% done.

---

## PHASE 4: Write Unit Tests (for 60% coverage requirement)
**Time estimate: 30-45 minutes | Priority: HIGH**

You need >=60% test coverage. Create test files:

### `services/alert-ingestion/test_main.py`
Test these:
1. `POST /api/v1/alerts` with valid payload -> 200/201
2. `POST /api/v1/alerts` with missing fields -> 422
3. `POST /api/v1/alerts` with invalid severity -> 422
4. `GET /api/v1/alerts/{id}` with valid ID -> 200
5. `GET /api/v1/alerts/{id}` with bad ID -> 404
6. `GET /health` -> 200
7. `GET /metrics` -> 200 with prometheus content type
8. Correlation logic: send 2 alerts with same service+severity within 5 min -> same incident

Use `from fastapi.testclient import TestClient` and mock the DB with SQLite or mock objects.

### `services/incident-management/test_main.py`
Test these:
1. `POST /api/v1/incidents` -> 201
2. `GET /api/v1/incidents` -> 200 with list
3. `GET /api/v1/incidents/{id}` -> 200 with detail
4. `PATCH /api/v1/incidents/{id}` acknowledge -> updates MTTA
5. `PATCH /api/v1/incidents/{id}` resolve -> updates MTTR
6. `GET /health` -> 200
7. `GET /metrics` -> 200

Run with: `pytest --cov=main --cov-report=term-missing test_main.py`
Target: 60%+ coverage.

---

## PHASE 5: Help Teammates / Fill Gaps
**Time estimate: variable**

If Person 2 & 3 are behind, you may need to fill in their services too. Here's what each needs:

### On-Call Service (Person 2's job, port 8003):
Quick stub if needed:
- `POST /api/v1/schedules` - store schedule in-memory or DB
- `GET /api/v1/schedules` - list schedules
- `GET /api/v1/oncall/current?team=X` - calculate who's on call using week_of_year % len(members)
- `POST /api/v1/escalate` - log escalation
- `GET /health`, `GET /metrics`

### Notification Service (Person 2/3's job, port 8004):
Super simple mock:
- `POST /api/v1/notify` - accepts {incident_id, channel, recipient, message}, logs to console
- `GET /health`, `GET /metrics`

### Web UI (Person 3's job, port 8080):
Minimum viable: Nginx serving static HTML that calls your APIs via JavaScript fetch().

---

## .dockerignore FILES (create for each service)

```
__pycache__
*.pyc
*.pyo
.pytest_cache
venv
.venv
.git
.env
*.md
```

---

## EXECUTION ORDER (PRIORITY SEQUENCE)

```
STEP 1: [60-90 min] Write alert-ingestion/main.py
STEP 2: [90-120 min] Write incident-management/main.py  
STEP 3: [15-20 min] Docker compose up, test with curl, fix bugs
STEP 4: [30-45 min] Write unit tests for both services
STEP 5: [15 min] Create .dockerignore files
STEP 6: [ONLY IF NEEDED] Help fill in oncall-service, notification-service stubs
STEP 7: [15 min] Final end-to-end test of full flow
```

**Total estimated time for Person 1 tasks: 3.5 - 5 hours**

---

## COMMON PITFALLS TO AVOID

1. **Don't use localhost in service-to-service calls** - Use Docker service names: `http://incident-management:8002`, NOT `http://localhost:8002`
2. **Don't crash if oncall/notification services aren't ready** - Wrap external calls in try/except
3. **Don't forget CORS** - The Web UI running in a browser at localhost:8080 needs CORS headers to call your APIs at localhost:8001/8002. Add `CORSMiddleware` to FastAPI.
4. **Don't hardcode database credentials** - Already using env vars from .env, keep it that way
5. **UUID generation** - Let PostgreSQL generate UUIDs with `gen_random_uuid()`, don't generate in Python
6. **Timestamp handling** - Always use UTC. Use `datetime.utcnow()` or `datetime.now(timezone.utc)`
7. **Don't forget to expose metrics at /metrics** - Judges CHECK this. Use `prometheus_client.generate_latest()`

---

## KEY CODE PATTERNS YOU'LL USE

### FastAPI + SQLAlchemy pattern:
```python
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
app = FastAPI(title="Service Name")

@app.get("/health")
def health():
    return {"status": "ok"}
```

### Prometheus metrics pattern:
```python
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

### Calling another service pattern:
```python
import httpx

ONCALL_URL = os.getenv("ONCALL_SERVICE_URL", "http://oncall-service:8003")

async def get_oncall(team: str):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{ONCALL_URL}/api/v1/oncall/current", params={"team": team})
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass  # Service not available, continue
    return None
```

---

## WHAT JUDGES WILL TEST (your services specifically)

1. `curl http://localhost:8001/health` -> must return 200
2. `curl http://localhost:8002/health` -> must return 200
3. `curl http://localhost:8001/metrics` -> must return Prometheus format
4. `curl http://localhost:8002/metrics` -> must return Prometheus format
5. Send alert -> incident gets created automatically
6. Acknowledge incident -> MTTA calculated
7. Resolve incident -> MTTR calculated
8. Send duplicate alert (same service+severity within 5 min) -> correlated to existing incident
9. `docker compose up -d` -> your services start and pass healthchecks
10. Grafana shows your metrics on dashboards

---

**GO BUILD IT. START WITH PHASE 1 (alert-ingestion/main.py). Then Phase 2. Then test. Ship it.**
