"""
Alert Ingestion Service — Unit Tests
=====================================
Run:  pytest test_main.py -v --cov=main --cov-report=term-missing
Target: ≥ 80 % line coverage
"""
import json
import uuid
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from fastapi.testclient import TestClient

# ── Mock the SQLAlchemy engine BEFORE importing the app ───────────────────
_mock_engine = MagicMock()
_mock_conn = MagicMock()
# Support both `engine.connect()` and `engine.begin()` as context managers
_mock_engine.connect.return_value.__enter__ = MagicMock(return_value=_mock_conn)
_mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
_mock_engine.begin.return_value.__enter__ = MagicMock(return_value=_mock_conn)
_mock_engine.begin.return_value.__exit__ = MagicMock(return_value=False)

with patch("sqlalchemy.create_engine", return_value=_mock_engine):
    from main import app, _compute_fingerprint

client = TestClient(app)


# ── Fixtures ──────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset mock call history between tests."""
    _mock_conn.reset_mock()
    yield


VALID_ALERT = {
    "service": "frontend-api",
    "severity": "high",
    "message": "HTTP 5xx error rate > 10 %",
    "labels": {"env": "production", "region": "us-east-1"},
}


def _mock_incident_service_success():
    """Return a patch that makes the remote incident-management call succeed."""
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {"id": str(uuid.uuid4())}
    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_resp
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=mock_client_instance)
    ctx.__exit__ = MagicMock(return_value=False)
    return patch("main.httpx.Client", return_value=ctx)


# ═══════════════════════════════════════════════════════════════════════════
# HEALTH & METRICS
# ═══════════════════════════════════════════════════════════════════════════
class TestHealth:
    def test_health_returns_ok(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok", "service": "alert-ingestion"}

    def test_readiness_succeeds_when_db_up(self):
        r = client.get("/health/ready")
        assert r.status_code == 200
        assert r.json()["database"] == "connected"

    def test_readiness_fails_when_db_down(self):
        _mock_engine.connect.return_value.__enter__.side_effect = Exception("conn refused")
        r = client.get("/health/ready")
        assert r.status_code == 503
        _mock_engine.connect.return_value.__enter__.side_effect = None
        _mock_engine.connect.return_value.__enter__.return_value = _mock_conn


class TestMetrics:
    def test_metrics_returns_prometheus_format(self):
        r = client.get("/metrics")
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert "text/plain" in ct or "text/plain" in str(r.headers)


# ═══════════════════════════════════════════════════════════════════════════
# FINGERPRINT HELPER
# ═══════════════════════════════════════════════════════════════════════════
class TestFingerprint:
    def test_deterministic(self):
        fp1 = _compute_fingerprint("svc", "high", "msg here")
        fp2 = _compute_fingerprint("svc", "high", "msg here")
        assert fp1 == fp2

    def test_case_insensitive(self):
        fp1 = _compute_fingerprint("SVC", "HIGH", "Msg Here")
        fp2 = _compute_fingerprint("svc", "high", "msg here")
        assert fp1 == fp2

    def test_different_inputs_yield_different_fingerprints(self):
        fp1 = _compute_fingerprint("svc-a", "high", "msg")
        fp2 = _compute_fingerprint("svc-b", "high", "msg")
        assert fp1 != fp2

    def test_length(self):
        fp = _compute_fingerprint("x", "low", "y")
        assert len(fp) == 16  # first 16 hex chars of sha256


# ═══════════════════════════════════════════════════════════════════════════
# POST /api/v1/alerts  — CREATION + CORRELATION
# ═══════════════════════════════════════════════════════════════════════════
class TestCreateAlert:
    def test_new_incident_when_no_existing(self):
        """No open incident matching → should call incident-management to create one."""
        _mock_conn.execute.return_value.fetchone.return_value = None
        with _mock_incident_service_success():
            r = client.post("/api/v1/alerts", json=VALID_ALERT)
        assert r.status_code == 201
        data = r.json()
        assert data["action"] == "new_incident"
        assert data["status"] == "accepted"
        assert data["fingerprint"]
        assert data["incident_id"]

    def test_existing_incident_correlation(self):
        """Open incident exists within window → alert attached, no new incident created."""
        existing_id = str(uuid.uuid4())
        _mock_conn.execute.return_value.fetchone.return_value = (existing_id,)
        r = client.post("/api/v1/alerts", json=VALID_ALERT)
        assert r.status_code == 201
        data = r.json()
        assert data["action"] == "existing_incident"
        assert data["incident_id"] == existing_id

    def test_fallback_to_local_creation(self):
        """When incident-management is unreachable, incident created locally."""
        _mock_conn.execute.return_value.fetchone.return_value = None
        with patch("main.httpx.Client", side_effect=Exception("connection refused")):
            r = client.post("/api/v1/alerts", json=VALID_ALERT)
        assert r.status_code == 201
        data = r.json()
        assert data["action"] == "new_incident"
        assert data["incident_id"]  # created locally

    def test_custom_timestamp_accepted(self):
        _mock_conn.execute.return_value.fetchone.return_value = None
        payload = {**VALID_ALERT, "timestamp": "2026-02-09T10:00:00Z"}
        with _mock_incident_service_success():
            r = client.post("/api/v1/alerts", json=payload)
        assert r.status_code == 201

    def test_custom_source_accepted(self):
        _mock_conn.execute.return_value.fetchone.return_value = None
        payload = {**VALID_ALERT, "source": "prometheus"}
        with _mock_incident_service_success():
            r = client.post("/api/v1/alerts", json=payload)
        assert r.status_code == 201

    def test_empty_labels_default(self):
        _mock_conn.execute.return_value.fetchone.return_value = None
        payload = {"service": "svc", "severity": "low", "message": "test"}
        with _mock_incident_service_success():
            r = client.post("/api/v1/alerts", json=payload)
        assert r.status_code == 201

    def test_x_request_id_header_returned(self):
        _mock_conn.execute.return_value.fetchone.return_value = None
        with _mock_incident_service_success():
            r = client.post("/api/v1/alerts", json=VALID_ALERT, headers={"X-Request-ID": "req-123"})
        assert r.headers["X-Request-ID"] == "req-123"

    def test_auto_generated_request_id(self):
        _mock_conn.execute.return_value.fetchone.return_value = None
        with _mock_incident_service_success():
            r = client.post("/api/v1/alerts", json=VALID_ALERT)
        assert "X-Request-ID" in r.headers


# ═══════════════════════════════════════════════════════════════════════════
# VALIDATION — 422 CASES
# ═══════════════════════════════════════════════════════════════════════════
class TestValidation:
    def test_missing_service(self):
        assert client.post("/api/v1/alerts", json={"severity": "high", "message": "x"}).status_code == 422

    def test_missing_severity(self):
        assert client.post("/api/v1/alerts", json={"service": "svc", "message": "x"}).status_code == 422

    def test_missing_message(self):
        assert client.post("/api/v1/alerts", json={"service": "svc", "severity": "high"}).status_code == 422

    def test_invalid_severity(self):
        r = client.post("/api/v1/alerts", json={"service": "svc", "severity": "banana", "message": "x"})
        assert r.status_code == 422

    def test_empty_service(self):
        r = client.post("/api/v1/alerts", json={"service": "", "severity": "high", "message": "x"})
        assert r.status_code == 422

    def test_empty_message(self):
        r = client.post("/api/v1/alerts", json={"service": "svc", "severity": "high", "message": ""})
        assert r.status_code == 422

    @pytest.mark.parametrize("sev", ["critical", "high", "medium", "low"])
    def test_all_valid_severities(self, sev):
        _mock_conn.execute.return_value.fetchone.return_value = None
        with _mock_incident_service_success():
            r = client.post("/api/v1/alerts", json={"service": "svc", "severity": sev, "message": "msg"})
        assert r.status_code == 201

    def test_severity_is_case_insensitive(self):
        _mock_conn.execute.return_value.fetchone.return_value = None
        with _mock_incident_service_success():
            r = client.post("/api/v1/alerts", json={"service": "svc", "severity": "HIGH", "message": "msg"})
        assert r.status_code == 201


# ═══════════════════════════════════════════════════════════════════════════
# GET /api/v1/alerts/{id}
# ═══════════════════════════════════════════════════════════════════════════
class TestGetAlert:
    def test_found(self):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        _mock_conn.execute.return_value.fetchone.return_value = (
            uuid.uuid4(), "svc", "high", "msg", "api", {"env": "prod"}, "fp123", now, uuid.uuid4(), now,
        )
        r = client.get(f"/api/v1/alerts/{uuid.uuid4()}")
        assert r.status_code == 200
        assert r.json()["severity"] == "high"

    def test_not_found(self):
        _mock_conn.execute.return_value.fetchone.return_value = None
        r = client.get(f"/api/v1/alerts/{uuid.uuid4()}")
        assert r.status_code == 404

    def test_invalid_uuid(self):
        r = client.get("/api/v1/alerts/not-a-uuid")
        assert r.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════
# GET /api/v1/alerts  — PAGINATION & FILTERS
# ═══════════════════════════════════════════════════════════════════════════
class TestListAlerts:
    def test_empty_list(self):
        _mock_conn.execute.return_value.fetchall.return_value = []
        _mock_conn.execute.return_value.scalar.return_value = 0
        # scalar() is called for COUNT; fetchall() for rows
        call_results = [MagicMock(scalar=MagicMock(return_value=0)), MagicMock(fetchall=MagicMock(return_value=[]))]
        _mock_conn.execute.side_effect = call_results
        r = client.get("/api/v1/alerts")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 0
        assert data["alerts"] == []
        _mock_conn.execute.side_effect = None  # reset

    def test_with_filters(self):
        result_mock = MagicMock()
        result_mock.scalar.return_value = 0
        result_mock.fetchall.return_value = []
        _mock_conn.execute.return_value = result_mock
        _mock_conn.execute.side_effect = [
            MagicMock(scalar=MagicMock(return_value=0)),
            MagicMock(fetchall=MagicMock(return_value=[])),
        ]
        r = client.get("/api/v1/alerts?service=svc&severity=high&page=1&per_page=10")
        assert r.status_code == 200
        _mock_conn.execute.side_effect = None
