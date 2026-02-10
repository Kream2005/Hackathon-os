# type: ignore
"""
Tests for the Notification Service (PostgreSQL-backed)
======================================================
Comprehensive unit tests covering all endpoints, channel handlers,
validation, edge cases, and error paths.

Run:  pytest test_main.py -v --cov=main --cov-report=term-missing
"""
import json
import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock

# Mock the engine before importing main to avoid real DB connection
with patch.dict("os.environ", {"DATABASE_URL": "postgresql://test:test@localhost:5432/test"}):
    import main
    from main import (
        app,
        _deliver_mock,
        _deliver_email,
        _deliver_slack,
        _deliver_webhook,
        _store_notification,
        VALID_CHANNELS,
        CHANNEL_HANDLERS,
        NotifyRequest,
    )

from fastapi.testclient import TestClient

client = TestClient(app, raise_server_exceptions=False)


# ── Helpers ───────────────────────────────────────────────────────────────
def _make_payload(**overrides):
    """Build a valid notify payload with optional overrides."""
    base = {
        "incident_id": "d290f1ee-6c54-4b01-90e6-d701748f0851",
        "channel": "mock",
        "recipient": "alice@example.com",
        "message": "[CRITICAL] frontend-api: HTTP 5xx rate > 10%",
    }
    base.update(overrides)
    return base


def _make_db_row(**overrides):
    """Build a fake DB row (mapping) for notification queries."""
    base = {
        "id": str(uuid.uuid4()),
        "incident_id": "d290f1ee-6c54-4b01-90e6-d701748f0851",
        "channel": "mock",
        "recipient": "alice@example.com",
        "message": "Test notification",
        "severity": "critical",
        "status": "sent",
        "metadata": {},
        "created_at": datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
    }
    base.update(overrides)
    return base


def _mock_begin():
    """Create a mock context manager for engine.begin()."""
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    return mock_conn


def _mock_connect():
    """Create a mock context manager for engine.connect()."""
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    return mock_conn


# ══════════════════════════════════════════════════════════════════════════
# HEALTH & OPS ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════
class TestHealthEndpoints:
    def test_health(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "notification-service"

    def test_health_returns_json(self):
        resp = client.get("/health")
        assert resp.headers["content-type"] == "application/json"

    @patch.object(main, "engine")
    def test_readiness_ok(self, mock_eng):
        mc = _mock_connect()
        mc.execute.return_value.scalar.return_value = 42
        mock_eng.connect.return_value = mc
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["notifications_in_db"] == 42

    @patch.object(main, "engine")
    def test_readiness_degraded_on_db_error(self, mock_eng):
        mc = _mock_connect()
        mc.execute.side_effect = Exception("DB down")
        mock_eng.connect.return_value = mc
        resp = client.get("/health/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "degraded"

    def test_metrics_endpoint(self):
        resp = client.get("/metrics")
        assert resp.status_code == 200
        body = resp.text
        assert "python_gc" in body or "notifications" in body or "process_" in body


# ══════════════════════════════════════════════════════════════════════════
# MIDDLEWARE
# ══════════════════════════════════════════════════════════════════════════
class TestMiddleware:
    def test_request_id_auto_generated(self):
        resp = client.get("/health")
        assert "x-request-id" in resp.headers

    def test_request_id_forwarded(self):
        custom_id = "my-custom-req-id"
        resp = client.get("/health", headers={"X-Request-ID": custom_id})
        assert resp.headers["x-request-id"] == custom_id


# ══════════════════════════════════════════════════════════════════════════
# VALIDATION
# ══════════════════════════════════════════════════════════════════════════
class TestValidation:
    def test_missing_incident_id(self):
        resp = client.post("/api/v1/notify", json={
            "channel": "mock", "recipient": "a@b.com", "message": "hi"
        })
        assert resp.status_code == 422

    def test_missing_recipient(self):
        resp = client.post("/api/v1/notify", json={
            "incident_id": "x", "channel": "mock", "message": "hi"
        })
        assert resp.status_code == 422

    def test_missing_message(self):
        resp = client.post("/api/v1/notify", json={
            "incident_id": "x", "channel": "mock", "recipient": "a@b.com"
        })
        assert resp.status_code == 422

    def test_invalid_channel(self):
        resp = client.post("/api/v1/notify", json=_make_payload(channel="fax"))
        assert resp.status_code == 422

    def test_empty_message(self):
        resp = client.post("/api/v1/notify", json=_make_payload(message=""))
        assert resp.status_code == 422

    def test_empty_recipient(self):
        resp = client.post("/api/v1/notify", json=_make_payload(recipient=""))
        assert resp.status_code == 422

    def test_empty_incident_id(self):
        resp = client.post("/api/v1/notify", json=_make_payload(incident_id=""))
        assert resp.status_code == 422

    def test_valid_channels_exist(self):
        assert "mock" in VALID_CHANNELS
        assert "email" in VALID_CHANNELS
        assert "slack" in VALID_CHANNELS
        assert "webhook" in VALID_CHANNELS

    @pytest.mark.parametrize("ch", ["mock", "email", "slack", "webhook"])
    @patch.object(main, "engine")
    def test_all_valid_channels_accepted(self, mock_eng, ch):
        mc = _mock_begin()
        mock_eng.begin.return_value = mc
        resp = client.post("/api/v1/notify", json=_make_payload(channel=ch))
        assert resp.status_code == 200

    @patch.object(main, "engine")
    def test_channel_normalisation_case_insensitive(self, mock_eng):
        mc = _mock_begin()
        mock_eng.begin.return_value = mc
        resp = client.post("/api/v1/notify", json=_make_payload(channel="MOCK"))
        assert resp.status_code == 200
        assert resp.json()["channel"] == "mock"


# ══════════════════════════════════════════════════════════════════════════
# NOTIFY ENDPOINT
# ══════════════════════════════════════════════════════════════════════════
class TestNotifyEndpoint:
    @patch.object(main, "engine")
    def test_successful_mock_notification(self, mock_eng):
        mc = _mock_begin()
        mock_eng.begin.return_value = mc
        resp = client.post("/api/v1/notify", json=_make_payload())
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "sent"
        assert data["channel"] == "mock"
        assert data["incident_id"] == "d290f1ee-6c54-4b01-90e6-d701748f0851"
        assert "id" in data
        assert "created_at" in data

    @patch.object(main, "engine")
    def test_response_contains_all_fields(self, mock_eng):
        mc = _mock_begin()
        mock_eng.begin.return_value = mc
        resp = client.post("/api/v1/notify", json=_make_payload(severity="high"))
        data = resp.json()
        for key in ["id", "incident_id", "channel", "recipient", "message", "severity", "status", "created_at"]:
            assert key in data

    @patch.object(main, "engine")
    def test_severity_preserved(self, mock_eng):
        mc = _mock_begin()
        mock_eng.begin.return_value = mc
        resp = client.post("/api/v1/notify", json=_make_payload(severity="critical"))
        assert resp.json()["severity"] == "critical"

    @patch.object(main, "engine")
    def test_metadata_accepted(self, mock_eng):
        mc = _mock_begin()
        mock_eng.begin.return_value = mc
        meta = {"runbook": "https://wiki.example.com/runbook-1"}
        resp = client.post("/api/v1/notify", json=_make_payload(metadata=meta))
        assert resp.status_code == 200

    @patch.object(main, "engine")
    def test_email_channel(self, mock_eng):
        mc = _mock_begin()
        mock_eng.begin.return_value = mc
        resp = client.post("/api/v1/notify", json=_make_payload(channel="email"))
        assert resp.json()["channel"] == "email"
        assert resp.json()["status"] == "sent"

    @patch.object(main, "engine")
    def test_slack_channel(self, mock_eng):
        mc = _mock_begin()
        mock_eng.begin.return_value = mc
        resp = client.post("/api/v1/notify", json=_make_payload(channel="slack"))
        assert resp.json()["channel"] == "slack"
        assert resp.json()["status"] == "sent"

    @patch.object(main, "engine")
    def test_webhook_no_url(self, mock_eng):
        mc = _mock_begin()
        mock_eng.begin.return_value = mc
        with patch.object(main, "WEBHOOK_URL", ""):
            resp = client.post("/api/v1/notify", json=_make_payload(channel="webhook"))
        assert resp.json()["channel"] == "webhook"
        assert resp.json()["status"] == "sent"


# ══════════════════════════════════════════════════════════════════════════
# GET NOTIFICATION BY ID
# ══════════════════════════════════════════════════════════════════════════
class TestGetNotification:
    @patch.object(main, "engine")
    def test_found(self, mock_eng):
        nid = str(uuid.uuid4())
        row = _make_db_row(id=nid)
        mc = _mock_connect()
        mc.execute.return_value.mappings.return_value.first.return_value = row
        mock_eng.connect.return_value = mc
        resp = client.get(f"/api/v1/notifications/{nid}")
        assert resp.status_code == 200
        assert resp.json()["id"] == nid

    @patch.object(main, "engine")
    def test_not_found(self, mock_eng):
        nid = str(uuid.uuid4())
        mc = _mock_connect()
        mc.execute.return_value.mappings.return_value.first.return_value = None
        mock_eng.connect.return_value = mc
        resp = client.get(f"/api/v1/notifications/{nid}")
        assert resp.status_code == 404

    def test_invalid_uuid(self):
        resp = client.get("/api/v1/notifications/not-a-uuid")
        assert resp.status_code == 400


# ══════════════════════════════════════════════════════════════════════════
# LIST NOTIFICATIONS
# ══════════════════════════════════════════════════════════════════════════
class TestListNotifications:
    @patch.object(main, "engine")
    def test_empty_list(self, mock_eng):
        mc = _mock_connect()
        mc.execute.return_value.scalar.return_value = 0
        mc.execute.return_value.mappings.return_value.all.return_value = []
        mock_eng.connect.return_value = mc
        resp = client.get("/api/v1/notifications")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["notifications"] == []

    @patch.object(main, "engine")
    def test_pagination_defaults(self, mock_eng):
        mc = _mock_connect()
        mc.execute.return_value.scalar.return_value = 0
        mc.execute.return_value.mappings.return_value.all.return_value = []
        mock_eng.connect.return_value = mc
        resp = client.get("/api/v1/notifications")
        data = resp.json()
        assert data["page"] == 1
        assert data["per_page"] == 50

    @patch.object(main, "engine")
    def test_custom_page_and_per_page(self, mock_eng):
        mc = _mock_connect()
        mc.execute.return_value.scalar.return_value = 0
        mc.execute.return_value.mappings.return_value.all.return_value = []
        mock_eng.connect.return_value = mc
        resp = client.get("/api/v1/notifications?page=2&per_page=10")
        data = resp.json()
        assert data["page"] == 2
        assert data["per_page"] == 10

    def test_invalid_page_zero(self):
        resp = client.get("/api/v1/notifications?page=0")
        assert resp.status_code == 422

    def test_invalid_per_page_too_large(self):
        resp = client.get("/api/v1/notifications?per_page=999")
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════
# STATS ENDPOINT
# ══════════════════════════════════════════════════════════════════════════
class TestStats:
    @patch.object(main, "engine")
    def test_stats_summary(self, mock_eng):
        mc = _mock_connect()
        summary_row = {"total": 10, "sent": 8, "failed": 2}
        channel_rows = [{"channel": "mock", "cnt": 5}, {"channel": "email", "cnt": 5}]
        severity_rows = [{"sev": "critical", "cnt": 6}, {"sev": "high", "cnt": 4}]
        mc.execute.return_value.mappings.side_effect = [
            MagicMock(first=MagicMock(return_value=summary_row)),
            MagicMock(all=MagicMock(return_value=channel_rows)),
            MagicMock(all=MagicMock(return_value=severity_rows)),
        ]
        mock_eng.connect.return_value = mc
        resp = client.get("/api/v1/notifications/stats/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 10
        assert data["sent"] == 8
        assert data["failed"] == 2
        assert data["by_channel"]["mock"] == 5
        assert data["by_severity"]["critical"] == 6

    @patch.object(main, "engine")
    def test_stats_empty(self, mock_eng):
        mc = _mock_connect()
        summary_row = {"total": 0, "sent": 0, "failed": 0}
        mc.execute.return_value.mappings.side_effect = [
            MagicMock(first=MagicMock(return_value=summary_row)),
            MagicMock(all=MagicMock(return_value=[])),
            MagicMock(all=MagicMock(return_value=[])),
        ]
        mock_eng.connect.return_value = mc
        resp = client.get("/api/v1/notifications/stats/summary")
        data = resp.json()
        assert data["total"] == 0
        assert data["by_channel"] == {}
        assert data["by_severity"] == {}


# ══════════════════════════════════════════════════════════════════════════
# CHANNEL HANDLERS
# ══════════════════════════════════════════════════════════════════════════
class TestChannelHandlers:
    @pytest.mark.asyncio
    async def test_deliver_mock(self):
        payload = NotifyRequest(**_make_payload())
        result = await _deliver_mock(payload)
        assert result == "sent"

    @pytest.mark.asyncio
    async def test_deliver_email(self):
        payload = NotifyRequest(**_make_payload(channel="email"))
        result = await _deliver_email(payload)
        assert result == "sent"

    @pytest.mark.asyncio
    async def test_deliver_slack(self):
        payload = NotifyRequest(**_make_payload(channel="slack"))
        result = await _deliver_slack(payload)
        assert result == "sent"

    @pytest.mark.asyncio
    async def test_deliver_webhook_no_url(self):
        payload = NotifyRequest(**_make_payload(channel="webhook"))
        with patch.object(main, "WEBHOOK_URL", ""):
            result = await _deliver_webhook(payload)
            assert result == "sent"

    @pytest.mark.asyncio
    async def test_deliver_webhook_success(self):
        payload = NotifyRequest(**_make_payload(channel="webhook"))
        mock_resp = MagicMock(status_code=200)
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        with patch.object(main, "WEBHOOK_URL", "http://hooks.example.com/test"):
            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await _deliver_webhook(payload)
                assert result == "sent"

    @pytest.mark.asyncio
    async def test_deliver_webhook_failure_status(self):
        payload = NotifyRequest(**_make_payload(channel="webhook"))
        mock_resp = MagicMock(status_code=500)
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        with patch.object(main, "WEBHOOK_URL", "http://hooks.example.com/test"):
            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await _deliver_webhook(payload)
                assert result == "failed"

    @pytest.mark.asyncio
    async def test_deliver_webhook_exception(self):
        payload = NotifyRequest(**_make_payload(channel="webhook"))
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        with patch.object(main, "WEBHOOK_URL", "http://hooks.example.com/test"):
            with patch("httpx.AsyncClient", return_value=mock_client):
                result = await _deliver_webhook(payload)
                assert result == "failed"

    def test_channel_handlers_map(self):
        assert set(CHANNEL_HANDLERS.keys()) == set(VALID_CHANNELS)

    def test_channel_handlers_all_callable(self):
        for ch, handler in CHANNEL_HANDLERS.items():
            assert callable(handler)


# ══════════════════════════════════════════════════════════════════════════
# STORE NOTIFICATION
# ══════════════════════════════════════════════════════════════════════════
class TestStoreNotification:
    @patch.object(main, "engine")
    def test_store_persists_to_db(self, mock_eng):
        mc = _mock_begin()
        mock_eng.begin.return_value = mc
        entry = {
            "id": str(uuid.uuid4()),
            "incident_id": "test-inc",
            "channel": "mock",
            "recipient": "alice@example.com",
            "message": "test",
            "severity": "high",
            "status": "sent",
            "metadata": None,
            "created_at": "2026-02-10T12:00:00+00:00",
        }
        _store_notification(entry)
        mc.execute.assert_called_once()

    @patch.object(main, "engine")
    def test_store_handles_db_error(self, mock_eng):
        from sqlalchemy.exc import SQLAlchemyError
        mc = _mock_begin()
        mc.execute.side_effect = SQLAlchemyError("DB write error")
        mock_eng.begin.return_value = mc
        entry = {
            "id": str(uuid.uuid4()),
            "incident_id": "test-inc",
            "channel": "mock",
            "recipient": "a@b.com",
            "message": "test",
            "severity": None,
            "status": "sent",
            "metadata": None,
            "created_at": "2026-02-10T12:00:00+00:00",
        }
        # Should not raise — error is logged
        _store_notification(entry)


# ══════════════════════════════════════════════════════════════════════════
# PYDANTIC MODEL VALIDATION
# ══════════════════════════════════════════════════════════════════════════
class TestNotifyRequestModel:
    def test_valid_payload(self):
        req = NotifyRequest(**_make_payload())
        assert req.channel == "mock"
        assert req.recipient == "alice@example.com"

    def test_channel_normalised_to_lowercase(self):
        req = NotifyRequest(**_make_payload(channel="MOCK"))
        assert req.channel == "mock"

    def test_invalid_channel_raises(self):
        with pytest.raises(Exception):
            NotifyRequest(**_make_payload(channel="telegram"))

    def test_recipient_stripped(self):
        req = NotifyRequest(**_make_payload(recipient="  bob@test.com  "))
        assert req.recipient == "bob@test.com"

    def test_severity_optional(self):
        req = NotifyRequest(**_make_payload())
        assert req.severity is None

    def test_severity_provided(self):
        req = NotifyRequest(**_make_payload(severity="critical"))
        assert req.severity == "critical"

    def test_metadata_optional(self):
        req = NotifyRequest(**_make_payload())
        assert req.metadata is None

    def test_metadata_provided(self):
        req = NotifyRequest(**_make_payload(metadata={"key": "value"}))
        assert req.metadata == {"key": "value"}

    def test_incident_id_whitespace_passes_model(self):
        # Whitespace-only passes min_length=1 (strip not enforced on incident_id)
        req = NotifyRequest(**_make_payload(incident_id="   "))
        assert req.incident_id == "   "


# ══════════════════════════════════════════════════════════════════════════
# EDGE CASES
# ══════════════════════════════════════════════════════════════════════════
class TestEdgeCases:
    @patch.object(main, "engine")
    def test_long_message(self, mock_eng):
        mc = _mock_begin()
        mock_eng.begin.return_value = mc
        msg = "A" * 4999
        resp = client.post("/api/v1/notify", json=_make_payload(message=msg))
        assert resp.status_code == 200

    def test_message_too_long(self):
        msg = "A" * 5001
        resp = client.post("/api/v1/notify", json=_make_payload(message=msg))
        assert resp.status_code == 422

    @patch.object(main, "engine")
    def test_special_characters_in_message(self, mock_eng):
        mc = _mock_begin()
        mock_eng.begin.return_value = mc
        resp = client.post("/api/v1/notify", json=_make_payload(
            message="Alert: <script>alert('xss')</script> & \"quotes\""
        ))
        assert resp.status_code == 200

    @patch.object(main, "engine")
    def test_unicode_in_recipient(self, mock_eng):
        mc = _mock_begin()
        mock_eng.begin.return_value = mc
        resp = client.post("/api/v1/notify", json=_make_payload(recipient="utilisateur@équipe.fr"))
        assert resp.status_code == 200

    def test_get_notification_invalid_id_format(self):
        resp = client.get("/api/v1/notifications/12345")
        assert resp.status_code == 400

    @patch.object(main, "engine")
    def test_notification_id_uuid_format(self, mock_eng):
        mc = _mock_begin()
        mock_eng.begin.return_value = mc
        resp = client.post("/api/v1/notify", json=_make_payload())
        data = resp.json()
        # Verify the returned ID is a valid UUID
        uuid.UUID(data["id"])  # Raises if invalid

    @patch.object(main, "engine")
    def test_created_at_iso_format(self, mock_eng):
        mc = _mock_begin()
        mock_eng.begin.return_value = mc
        resp = client.post("/api/v1/notify", json=_make_payload())
        data = resp.json()
        # Should be parseable as ISO datetime
        datetime.fromisoformat(data["created_at"])
