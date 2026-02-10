"""
Incident Management Service — Unit Tests
==========================================
Run:  pytest test_main.py -v --cov=main --cov-report=term-missing
Target: ≥ 80 % line coverage
"""
import json
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# ── Mock DB before import ────────────────────────────────────────────────
_mock_engine = MagicMock()
_mock_conn = MagicMock()
_mock_engine.connect.return_value.__enter__ = MagicMock(return_value=_mock_conn)
_mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
_mock_engine.begin.return_value.__enter__ = MagicMock(return_value=_mock_conn)
_mock_engine.begin.return_value.__exit__ = MagicMock(return_value=False)

with patch("sqlalchemy.create_engine", return_value=_mock_engine):
    from main import app, ALLOWED_TRANSITIONS

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset():
    _mock_conn.reset_mock()
    _mock_conn.execute.side_effect = None
    yield


# ── Helpers ──────────────────────────────────────────────────────────────
NOW = datetime.now(timezone.utc)


def _incident_row(
    iid=None, title="Test incident", service="api-gateway", severity="high",
    status="open", assigned_to="Alice", alert_count=1,
    created_at=None, updated_at=None, acknowledged_at=None, resolved_at=None,
    mtta=None, mttr=None,
):
    """Build a mock incident row tuple matching INCIDENT_COLS order."""
    return (
        iid or uuid.uuid4(),
        title, service, severity, status, assigned_to, alert_count,
        created_at or NOW, updated_at or NOW,
        acknowledged_at, resolved_at, mtta, mttr,
    )


# ═══════════════════════════════════════════════════════════════════════════
# HEALTH & METRICS
# ═══════════════════════════════════════════════════════════════════════════
class TestHealth:
    def test_health_ok(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok", "service": "incident-management"}

    def test_readiness_ok(self):
        r = client.get("/health/ready")
        assert r.status_code == 200
        assert r.json()["database"] == "connected"

    def test_readiness_fails_when_db_down(self):
        _mock_engine.connect.return_value.__enter__.side_effect = Exception("boom")
        r = client.get("/health/ready")
        assert r.status_code == 503
        # reset
        _mock_engine.connect.return_value.__enter__.side_effect = None
        _mock_engine.connect.return_value.__enter__.return_value = _mock_conn

    def test_metrics_endpoint(self):
        r = client.get("/metrics")
        assert r.status_code == 200

    def test_request_id_propagated(self):
        with patch("main._get_oncall", return_value=None):
            r = client.post(
                "/api/v1/incidents",
                json={"title": "T", "service": "svc", "severity": "low"},
                headers={"X-Request-ID": "my-req-42"},
            )
        assert r.headers["X-Request-ID"] == "my-req-42"


# ═══════════════════════════════════════════════════════════════════════════
# POST /api/v1/incidents
# ═══════════════════════════════════════════════════════════════════════════
class TestCreateIncident:
    def test_create_success(self):
        with patch("main._get_oncall", return_value=None):
            r = client.post("/api/v1/incidents", json={
                "title": "CPU overload", "service": "frontend-api", "severity": "high",
            })
        assert r.status_code == 201
        d = r.json()
        assert d["status"] == "open"
        assert d["alert_count"] == 0
        assert "id" in d

    def test_create_with_oncall_lookup(self):
        with patch("main._get_oncall", return_value={"primary": {"name": "Alice"}, "secondary": {"name": "Carol"}}):
            r = client.post("/api/v1/incidents", json={
                "title": "Oncall test", "service": "backend", "severity": "critical",
            })
        assert r.status_code == 201
        assert r.json()["assigned_to"] == "Alice"

    def test_create_with_explicit_assignee(self):
        with patch("main._get_oncall", return_value=None):
            r = client.post("/api/v1/incidents", json={
                "title": "Manual assign", "service": "db", "severity": "medium",
                "assigned_to": "Bob",
            })
        assert r.status_code == 201
        assert r.json()["assigned_to"] == "Bob"

    def test_missing_title_422(self):
        assert client.post("/api/v1/incidents", json={"service": "x", "severity": "low"}).status_code == 422

    def test_missing_service_422(self):
        assert client.post("/api/v1/incidents", json={"title": "T", "severity": "low"}).status_code == 422

    def test_invalid_severity_422(self):
        r = client.post("/api/v1/incidents", json={"title": "T", "service": "s", "severity": "banana"})
        assert r.status_code == 422

    @pytest.mark.parametrize("sev", ["critical", "high", "medium", "low"])
    def test_all_severities(self, sev):
        with patch("main._get_oncall", return_value=None):
            r = client.post("/api/v1/incidents", json={"title": "T", "service": "s", "severity": sev})
        assert r.status_code == 201


# ═══════════════════════════════════════════════════════════════════════════
# GET /api/v1/incidents  — LIST + PAGINATION
# ═══════════════════════════════════════════════════════════════════════════
class TestListIncidents:
    def test_empty(self):
        _mock_conn.execute.side_effect = [
            MagicMock(scalar=MagicMock(return_value=0)),
            MagicMock(fetchall=MagicMock(return_value=[])),
        ]
        r = client.get("/api/v1/incidents")
        assert r.status_code == 200
        assert r.json()["total"] == 0
        assert r.json()["incidents"] == []

    def test_with_filters(self):
        _mock_conn.execute.side_effect = [
            MagicMock(scalar=MagicMock(return_value=0)),
            MagicMock(fetchall=MagicMock(return_value=[])),
        ]
        r = client.get("/api/v1/incidents?status=open&severity=high&service=api&page=2&per_page=10")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# GET /api/v1/incidents/{id}
# ═══════════════════════════════════════════════════════════════════════════
class TestGetIncident:
    def test_not_found(self):
        _mock_conn.execute.return_value.fetchone.return_value = None
        r = client.get(f"/api/v1/incidents/{uuid.uuid4()}")
        assert r.status_code == 404

    def test_invalid_uuid(self):
        r = client.get("/api/v1/incidents/not-a-uuid")
        assert r.status_code == 400

    def test_found_with_children(self):
        iid = uuid.uuid4()
        # First execute → incident row, then notes, timeline (alerts now fetched via HTTP)
        _mock_conn.execute.side_effect = [
            MagicMock(fetchone=MagicMock(return_value=_incident_row(iid=iid))),
            MagicMock(fetchall=MagicMock(return_value=[])),   # notes
            MagicMock(fetchall=MagicMock(return_value=[])),   # timeline
        ]
        with patch("main._fetch_linked_alerts", return_value=[]):
            r = client.get(f"/api/v1/incidents/{iid}")
        assert r.status_code == 200
        d = r.json()
        assert d["id"] == str(iid)
        assert d["alerts"] == []
        assert d["notes"] == []
        assert d["timeline"] == []


# ═══════════════════════════════════════════════════════════════════════════
# PATCH /api/v1/incidents/{id}  — STATE MACHINE
# ═══════════════════════════════════════════════════════════════════════════
class TestUpdateIncident:
    def test_not_found(self):
        _mock_conn.execute.return_value.fetchone.return_value = None
        r = client.patch(f"/api/v1/incidents/{uuid.uuid4()}", json={"status": "acknowledged"})
        assert r.status_code == 404

    def test_invalid_uuid(self):
        r = client.patch("/api/v1/incidents/bad-id", json={"status": "acknowledged"})
        assert r.status_code == 400

    def test_invalid_status_value(self):
        r = client.patch(f"/api/v1/incidents/{uuid.uuid4()}", json={"status": "exploded"})
        assert r.status_code == 422

    def test_acknowledge_from_open(self):
        """open → acknowledged is allowed."""
        iid = uuid.uuid4()
        created = NOW - timedelta(minutes=5)
        row = _incident_row(iid=iid, status="open", created_at=created)
        updated_row = _incident_row(iid=iid, status="acknowledged", created_at=created, acknowledged_at=NOW, mtta=300.0)
        _mock_conn.execute.side_effect = [
            MagicMock(fetchone=MagicMock(return_value=row)),        # SELECT current
            None,                                                   # INSERT timeline
            None,                                                   # UPDATE
            MagicMock(fetchone=MagicMock(return_value=updated_row)), # SELECT updated
        ]
        r = client.patch(f"/api/v1/incidents/{iid}", json={"status": "acknowledged"})
        assert r.status_code == 200

    def test_resolve_from_open_fast_track(self):
        """open → resolved is allowed (fast-track)."""
        iid = uuid.uuid4()
        created = NOW - timedelta(minutes=10)
        row = _incident_row(iid=iid, status="open", created_at=created)
        resolved_row = _incident_row(iid=iid, status="resolved", created_at=created, resolved_at=NOW, mttr=600.0)
        _mock_conn.execute.side_effect = [
            MagicMock(fetchone=MagicMock(return_value=row)),
            None,                                                   # INSERT timeline
            None,                                                   # UPDATE
            MagicMock(fetchone=MagicMock(return_value=resolved_row)), # SELECT updated
        ]
        r = client.patch(f"/api/v1/incidents/{iid}", json={"status": "resolved"})
        assert r.status_code == 200

    def test_illegal_transition_resolved_to_open(self):
        """resolved → open is NOT allowed (terminal state)."""
        iid = uuid.uuid4()
        row = _incident_row(iid=iid, status="resolved")
        _mock_conn.execute.side_effect = [
            MagicMock(fetchone=MagicMock(return_value=row)),
        ]
        r = client.patch(f"/api/v1/incidents/{iid}", json={"status": "open"})
        assert r.status_code == 409
        assert "Cannot transition" in r.json()["detail"]

    def test_illegal_transition_acknowledged_to_open(self):
        iid = uuid.uuid4()
        row = _incident_row(iid=iid, status="acknowledged")
        _mock_conn.execute.side_effect = [
            MagicMock(fetchone=MagicMock(return_value=row)),
        ]
        r = client.patch(f"/api/v1/incidents/{iid}", json={"status": "open"})
        assert r.status_code == 409

    def test_add_note_without_status_change(self):
        iid = uuid.uuid4()
        row = _incident_row(iid=iid, status="open")
        _mock_conn.execute.side_effect = [
            MagicMock(fetchone=MagicMock(return_value=row)),
            None, None,  # note insert, timeline
            MagicMock(fetchone=MagicMock(return_value=row)),
        ]
        r = client.patch(f"/api/v1/incidents/{iid}", json={"notes": "Investigating root cause"})
        assert r.status_code == 200

    def test_reassignment(self):
        iid = uuid.uuid4()
        row = _incident_row(iid=iid, assigned_to="Alice")
        updated = _incident_row(iid=iid, assigned_to="Bob")
        _mock_conn.execute.side_effect = [
            MagicMock(fetchone=MagicMock(return_value=row)),
            None, None,
            MagicMock(fetchone=MagicMock(return_value=updated)),
        ]
        r = client.patch(f"/api/v1/incidents/{iid}", json={"assigned_to": "Bob"})
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# GET /api/v1/incidents/{id}/metrics
# ═══════════════════════════════════════════════════════════════════════════
class TestIncidentMetrics:
    def test_not_found(self):
        _mock_conn.execute.return_value.fetchone.return_value = None
        r = client.get(f"/api/v1/incidents/{uuid.uuid4()}/metrics")
        assert r.status_code == 404

    def test_found(self):
        _mock_conn.execute.return_value.fetchone.return_value = (120.5, 600.0, "resolved", NOW, NOW, NOW)
        r = client.get(f"/api/v1/incidents/{uuid.uuid4()}/metrics")
        assert r.status_code == 200
        d = r.json()
        assert d["mtta_seconds"] == 120.5
        assert d["mttr_seconds"] == 600.0


# ═══════════════════════════════════════════════════════════════════════════
# GET /api/v1/incidents/stats/summary
# ═══════════════════════════════════════════════════════════════════════════
class TestSummaryStats:
    def test_summary(self):
        _mock_conn.execute.return_value.fetchone.return_value = (5, 2, 1, 10, 90.0, 500.0)
        r = client.get("/api/v1/incidents/stats/summary")
        assert r.status_code == 200
        d = r.json()
        assert d["open"] == 5
        assert d["resolved"] == 10
        assert d["avg_mtta_seconds"] == 90.0


# ═══════════════════════════════════════════════════════════════════════════
# STATE MACHINE DEFINITION
# ═══════════════════════════════════════════════════════════════════════════
class TestStateMachine:
    def test_allowed_transitions_structure(self):
        """Verify the state machine has correct allowed transitions."""
        assert "acknowledged" in ALLOWED_TRANSITIONS["open"]
        assert "in_progress" in ALLOWED_TRANSITIONS["open"]
        assert "resolved" in ALLOWED_TRANSITIONS["open"]
        assert "resolved" in ALLOWED_TRANSITIONS["acknowledged"]
        assert "resolved" in ALLOWED_TRANSITIONS["in_progress"]
        assert len(ALLOWED_TRANSITIONS["resolved"]) == 0  # terminal


# ═══════════════════════════════════════════════════════════════════════════
# GET /api/v1/incidents/find-open  — CORRELATION ENDPOINT (DB-per-service)
# ═══════════════════════════════════════════════════════════════════════════
class TestFindOpenIncident:
    def test_found(self):
        iid = uuid.uuid4()
        _mock_conn.execute.return_value.fetchone.return_value = (iid,)
        r = client.get("/api/v1/incidents/find-open", params={
            "service": "backend", "severity": "critical",
        })
        assert r.status_code == 200
        assert r.json()["incident_id"] == str(iid)

    def test_not_found(self):
        _mock_conn.execute.return_value.fetchone.return_value = None
        r = client.get("/api/v1/incidents/find-open", params={
            "service": "backend", "severity": "low",
        })
        assert r.status_code == 200
        assert r.json()["incident_id"] is None

    def test_missing_params(self):
        r = client.get("/api/v1/incidents/find-open")
        assert r.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
# POST /api/v1/incidents/{id}/link-alert  — ALERT LINKING (DB-per-service)
# ═══════════════════════════════════════════════════════════════════════════
class TestLinkAlert:
    def test_success(self):
        iid = uuid.uuid4()
        _mock_conn.execute.side_effect = [
            MagicMock(fetchone=MagicMock(return_value=(1,))),  # SELECT 1 exists
            None,  # UPDATE alert_count
            None,  # INSERT timeline
        ]
        r = client.post(f"/api/v1/incidents/{iid}/link-alert", json={
            "alert_id": str(uuid.uuid4()), "fingerprint": "abc123",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "linked"

    def test_not_found(self):
        iid = uuid.uuid4()
        _mock_conn.execute.side_effect = [
            MagicMock(fetchone=MagicMock(return_value=None)),
        ]
        r = client.post(f"/api/v1/incidents/{iid}/link-alert", json={
            "alert_id": str(uuid.uuid4()),
        })
        assert r.status_code == 404

    def test_invalid_uuid(self):
        r = client.post("/api/v1/incidents/bad-id/link-alert", json={})
        assert r.status_code == 400
