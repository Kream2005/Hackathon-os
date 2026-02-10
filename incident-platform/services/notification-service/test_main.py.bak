# type: ignore
"""
Tests for the Notification Service
===================================
Comprehensive unit tests covering all endpoints, channel handlers,
validation, edge cases, and error paths.

Run:  pytest test_main.py -v --cov=main --cov-report=term-missing
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from main import (
    app,
    notification_log,
    notification_index,
    _store_notification,
    _deliver_mock,
    _deliver_email,
    _deliver_slack,
    _deliver_webhook,
    VALID_CHANNELS,
    NotifyRequest,
)

client = TestClient(app)


# ── Fixtures ──────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def clear_log():
    """Reset in-memory state before every test."""
    notification_log.clear()
    notification_index.clear()
    yield
    notification_log.clear()
    notification_index.clear()


def _make_payload(**overrides):
    """Helper to build a valid notify payload with optional overrides."""
    base = {
        "incident_id": "d290f1ee-6c54-4b01-90e6-d701748f0851",
        "channel": "mock",
        "recipient": "alice@example.com",
        "message": "[CRITICAL] frontend-api: HTTP 5xx rate > 10%",
    }
    base.update(overrides)
    return base


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

    def test_readiness(self):
        resp = client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "notifications_in_log" in data
        assert data["notifications_in_log"] == 0

    def test_readiness_with_notifications(self):
        # Send one notification first
        client.post("/api/v1/notify", json=_make_payload())
        resp = client.get("/health/ready")
        data = resp.json()
        assert data["notifications_in_log"] == 1

    def test_metrics_endpoint(self):
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "notifications_sent_total" in resp.text

    def test_metrics_content_type(self):
        resp = client.get("/metrics")
        assert "text/plain" in resp.headers.get("content-type", "")


# ══════════════════════════════════════════════════════════════════════════
# POST /api/v1/notify  — CORE ENDPOINT
# ══════════════════════════════════════════════════════════════════════════
class TestNotifyEndpoint:
    def test_send_mock_notification(self):
        resp = client.post("/api/v1/notify", json=_make_payload())
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "sent"
        assert data["channel"] == "mock"
        assert data["recipient"] == "alice@example.com"
        assert data["incident_id"] == "d290f1ee-6c54-4b01-90e6-d701748f0851"
        assert "id" in data
        assert "created_at" in data

    def test_send_email_notification(self):
        resp = client.post("/api/v1/notify", json=_make_payload(channel="email"))
        assert resp.status_code == 200
        assert resp.json()["channel"] == "email"
        assert resp.json()["status"] == "sent"

    def test_send_slack_notification(self):
        resp = client.post("/api/v1/notify", json=_make_payload(
            channel="slack", recipient="#alerts"
        ))
        assert resp.status_code == 200
        assert resp.json()["channel"] == "slack"
        assert resp.json()["recipient"] == "#alerts"

    def test_send_webhook_notification_mock(self):
        """Webhook without WEBHOOK_URL configured → mock delivery."""
        resp = client.post("/api/v1/notify", json=_make_payload(channel="webhook"))
        assert resp.status_code == 200
        assert resp.json()["channel"] == "webhook"
        assert resp.json()["status"] == "sent"

    def test_notification_with_severity(self):
        resp = client.post("/api/v1/notify", json=_make_payload(severity="critical"))
        assert resp.status_code == 200
        assert resp.json()["severity"] == "critical"

    def test_notification_without_severity(self):
        resp = client.post("/api/v1/notify", json=_make_payload())
        assert resp.status_code == 200
        assert resp.json()["severity"] is None

    def test_notification_with_metadata(self):
        resp = client.post("/api/v1/notify", json=_make_payload(
            metadata={"team": "platform", "priority": 1}
        ))
        assert resp.status_code == 200
        assert resp.json()["status"] == "sent"

    def test_notification_stored_in_log(self):
        resp = client.post("/api/v1/notify", json=_make_payload())
        assert len(notification_log) == 1
        assert notification_log[0]["id"] == resp.json()["id"]

    def test_notification_indexed(self):
        resp = client.post("/api/v1/notify", json=_make_payload())
        nid = resp.json()["id"]
        assert nid in notification_index
        assert notification_index[nid]["channel"] == "mock"

    def test_request_id_in_response_headers(self):
        resp = client.post("/api/v1/notify", json=_make_payload())
        assert "x-request-id" in resp.headers

    def test_custom_request_id_echoed(self):
        resp = client.post(
            "/api/v1/notify",
            json=_make_payload(),
            headers={"X-Request-ID": "my-trace-123"},
        )
        assert resp.headers["x-request-id"] == "my-trace-123"

    def test_multiple_notifications_sequential(self):
        for i in range(5):
            resp = client.post("/api/v1/notify", json=_make_payload(
                incident_id=f"incident-{i}"
            ))
            assert resp.status_code == 200
        assert len(notification_log) == 5


# ══════════════════════════════════════════════════════════════════════════
# VALIDATION ERRORS (422)
# ══════════════════════════════════════════════════════════════════════════
class TestValidation:
    def test_missing_required_fields(self):
        resp = client.post("/api/v1/notify", json={"bad": "data"})
        assert resp.status_code == 422

    def test_missing_incident_id(self):
        resp = client.post("/api/v1/notify", json={
            "recipient": "alice@example.com", "message": "test"
        })
        assert resp.status_code == 422

    def test_missing_recipient(self):
        resp = client.post("/api/v1/notify", json={
            "incident_id": "inc-1", "message": "test"
        })
        assert resp.status_code == 422

    def test_missing_message(self):
        resp = client.post("/api/v1/notify", json={
            "incident_id": "inc-1", "recipient": "alice@example.com"
        })
        assert resp.status_code == 422

    def test_empty_incident_id(self):
        resp = client.post("/api/v1/notify", json=_make_payload(incident_id=""))
        assert resp.status_code == 422

    def test_empty_recipient(self):
        resp = client.post("/api/v1/notify", json=_make_payload(recipient=""))
        assert resp.status_code == 422

    def test_empty_message(self):
        resp = client.post("/api/v1/notify", json=_make_payload(message=""))
        assert resp.status_code == 422

    def test_invalid_channel(self):
        resp = client.post("/api/v1/notify", json=_make_payload(channel="telegram"))
        assert resp.status_code == 422

    def test_channel_normalised_to_lowercase(self):
        resp = client.post("/api/v1/notify", json=_make_payload(channel="EMAIL"))
        assert resp.status_code == 200
        assert resp.json()["channel"] == "email"

    def test_recipient_whitespace_stripped(self):
        resp = client.post("/api/v1/notify", json=_make_payload(recipient="  bob@test.com  "))
        assert resp.status_code == 200
        assert resp.json()["recipient"] == "bob@test.com"

    def test_empty_json_body(self):
        resp = client.post("/api/v1/notify", json={})
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════
# GET /api/v1/notifications/{id}  — SINGLE NOTIFICATION
# ══════════════════════════════════════════════════════════════════════════
class TestGetNotification:
    def test_get_existing_notification(self):
        post_resp = client.post("/api/v1/notify", json=_make_payload())
        nid = post_resp.json()["id"]
        resp = client.get(f"/api/v1/notifications/{nid}")
        assert resp.status_code == 200
        assert resp.json()["id"] == nid
        assert resp.json()["channel"] == "mock"

    def test_get_notification_includes_metadata(self):
        post_resp = client.post("/api/v1/notify", json=_make_payload(
            metadata={"key": "value"}
        ))
        nid = post_resp.json()["id"]
        resp = client.get(f"/api/v1/notifications/{nid}")
        assert resp.status_code == 200
        assert resp.json()["metadata"] == {"key": "value"}

    def test_get_nonexistent_notification(self):
        resp = client.get("/api/v1/notifications/d290f1ee-6c54-4b01-90e6-d701748f0000")
        assert resp.status_code == 404

    def test_get_notification_invalid_uuid(self):
        resp = client.get("/api/v1/notifications/not-a-uuid")
        assert resp.status_code == 400
        assert "Invalid notification ID" in resp.json()["detail"]


# ══════════════════════════════════════════════════════════════════════════
# GET /api/v1/notifications  — LIST WITH PAGINATION & FILTERS
# ══════════════════════════════════════════════════════════════════════════
class TestListNotifications:
    def _seed(self, count=5):
        """Send multiple notifications for list testing."""
        channels = ["mock", "email", "slack", "mock", "email"]
        for i in range(count):
            client.post("/api/v1/notify", json=_make_payload(
                incident_id=f"incident-{i}",
                channel=channels[i % len(channels)],
                recipient=f"user{i}@test.com",
            ))

    def test_list_empty(self):
        resp = client.get("/api/v1/notifications")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["notifications"] == []

    def test_list_all(self):
        self._seed(3)
        resp = client.get("/api/v1/notifications")
        assert resp.status_code == 200
        assert resp.json()["total"] == 3
        assert len(resp.json()["notifications"]) == 3

    def test_pagination_defaults(self):
        self._seed(3)
        resp = client.get("/api/v1/notifications")
        data = resp.json()
        assert data["page"] == 1
        assert data["per_page"] == 50

    def test_pagination_custom(self):
        self._seed(5)
        resp = client.get("/api/v1/notifications?page=2&per_page=2")
        data = resp.json()
        assert data["total"] == 5
        assert data["page"] == 2
        assert data["per_page"] == 2
        assert len(data["notifications"]) == 2

    def test_pagination_beyond_last_page(self):
        self._seed(3)
        resp = client.get("/api/v1/notifications?page=100&per_page=50")
        data = resp.json()
        assert data["total"] == 3
        assert len(data["notifications"]) == 0

    def test_filter_by_channel(self):
        self._seed(5)
        resp = client.get("/api/v1/notifications?channel=email")
        data = resp.json()
        assert all(n["channel"] == "email" for n in data["notifications"])

    def test_filter_by_status(self):
        self._seed(3)
        resp = client.get("/api/v1/notifications?status=sent")
        data = resp.json()
        assert all(n["status"] == "sent" for n in data["notifications"])

    def test_filter_by_incident_id(self):
        self._seed(5)
        resp = client.get("/api/v1/notifications?incident_id=incident-2")
        data = resp.json()
        assert data["total"] == 1
        assert data["notifications"][0]["incident_id"] == "incident-2"

    def test_filter_by_recipient(self):
        self._seed(5)
        resp = client.get("/api/v1/notifications?recipient=user0@test.com")
        data = resp.json()
        assert data["total"] == 1

    def test_filter_combined(self):
        self._seed(5)
        resp = client.get("/api/v1/notifications?channel=mock&status=sent")
        data = resp.json()
        assert all(
            n["channel"] == "mock" and n["status"] == "sent"
            for n in data["notifications"]
        )


# ══════════════════════════════════════════════════════════════════════════
# GET /api/v1/notifications/stats/summary
# ══════════════════════════════════════════════════════════════════════════
class TestStats:
    def test_stats_empty(self):
        resp = client.get("/api/v1/notifications/stats/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["sent"] == 0
        assert data["failed"] == 0
        assert data["by_channel"] == {}

    def test_stats_after_notifications(self):
        for ch in ["mock", "email", "slack", "mock"]:
            client.post("/api/v1/notify", json=_make_payload(channel=ch))
        resp = client.get("/api/v1/notifications/stats/summary")
        data = resp.json()
        assert data["total"] == 4
        assert data["sent"] == 4
        assert data["by_channel"]["mock"] == 2
        assert data["by_channel"]["email"] == 1
        assert data["by_channel"]["slack"] == 1

    def test_stats_severity_tracking(self):
        client.post("/api/v1/notify", json=_make_payload(severity="critical"))
        client.post("/api/v1/notify", json=_make_payload(severity="high"))
        client.post("/api/v1/notify", json=_make_payload())  # no severity → "unknown"
        resp = client.get("/api/v1/notifications/stats/summary")
        data = resp.json()
        assert data["by_severity"]["critical"] == 1
        assert data["by_severity"]["high"] == 1
        assert data["by_severity"]["unknown"] == 1


# ══════════════════════════════════════════════════════════════════════════
# CHANNEL HANDLER UNIT TESTS
# ══════════════════════════════════════════════════════════════════════════
class TestChannelHandlers:
    @pytest.mark.asyncio
    async def test_deliver_mock(self):
        req = NotifyRequest(
            incident_id="inc-1", recipient="alice@test.com",
            message="test msg", channel="mock",
        )
        result = await _deliver_mock(req)
        assert result == "sent"

    @pytest.mark.asyncio
    async def test_deliver_email(self):
        req = NotifyRequest(
            incident_id="inc-1", recipient="alice@test.com",
            message="test msg", channel="email",
        )
        result = await _deliver_email(req)
        assert result == "sent"

    @pytest.mark.asyncio
    async def test_deliver_slack(self):
        req = NotifyRequest(
            incident_id="inc-1", recipient="#alerts",
            message="test msg", channel="slack",
        )
        result = await _deliver_slack(req)
        assert result == "sent"

    @pytest.mark.asyncio
    async def test_deliver_webhook_no_url(self):
        """Without WEBHOOK_URL → mock delivery → sent."""
        req = NotifyRequest(
            incident_id="inc-1", recipient="alice@test.com",
            message="test msg", channel="webhook",
        )
        result = await _deliver_webhook(req)
        assert result == "sent"

    @pytest.mark.asyncio
    @patch("main.WEBHOOK_URL", "http://hooks.example.com/webhook")
    @patch("main.httpx.AsyncClient")
    async def test_deliver_webhook_success(self, mock_client_cls):
        """With WEBHOOK_URL and successful delivery → sent."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        req = NotifyRequest(
            incident_id="inc-1", recipient="alice@test.com",
            message="test msg", channel="webhook",
        )
        result = await _deliver_webhook(req)
        assert result == "sent"

    @pytest.mark.asyncio
    @patch("main.WEBHOOK_URL", "http://hooks.example.com/webhook")
    @patch("main.httpx.AsyncClient")
    async def test_deliver_webhook_server_error(self, mock_client_cls):
        """Webhook returns 500 → failed."""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        req = NotifyRequest(
            incident_id="inc-1", recipient="alice@test.com",
            message="test msg", channel="webhook",
        )
        result = await _deliver_webhook(req)
        assert result == "failed"

    @pytest.mark.asyncio
    @patch("main.WEBHOOK_URL", "http://hooks.example.com/webhook")
    @patch("main.httpx.AsyncClient")
    async def test_deliver_webhook_connection_error(self, mock_client_cls):
        """Webhook unreachable → failed."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("Connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        req = NotifyRequest(
            incident_id="inc-1", recipient="alice@test.com",
            message="test msg", channel="webhook",
        )
        result = await _deliver_webhook(req)
        assert result == "failed"


# ══════════════════════════════════════════════════════════════════════════
# STORE HELPER & RING BUFFER
# ══════════════════════════════════════════════════════════════════════════
class TestStoreHelper:
    def test_store_adds_to_log_and_index(self):
        entry = {"id": "test-1", "channel": "mock", "status": "sent"}
        _store_notification(entry)
        assert len(notification_log) == 1
        assert notification_index["test-1"] == entry

    @patch("main.MAX_LOG_SIZE", 3)
    def test_ring_buffer_eviction(self):
        """When log exceeds MAX_LOG_SIZE, oldest entries are evicted."""
        for i in range(5):
            _store_notification({"id": f"n-{i}", "channel": "mock", "status": "sent"})
        # Only last 3 should remain
        assert len(notification_log) == 3
        assert "n-0" not in notification_index
        assert "n-1" not in notification_index
        assert "n-4" in notification_index


# ══════════════════════════════════════════════════════════════════════════
# VALID CHANNELS CONSTANT
# ══════════════════════════════════════════════════════════════════════════
class TestConstants:
    def test_valid_channels(self):
        assert "mock" in VALID_CHANNELS
        assert "email" in VALID_CHANNELS
        assert "slack" in VALID_CHANNELS
        assert "webhook" in VALID_CHANNELS
        assert len(VALID_CHANNELS) == 4
