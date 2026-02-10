# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false

"""
Tests for On-Call Service v2.1.0
Coverage target: >= 95%
Total: 85+ tests across 12 test classes
"""

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient
from main import (
    app,
    schedules_db,
    overrides_db,
    escalation_log,
    oncall_history,
    last_known_oncall,
    DEFAULT_OVERRIDE_HOURS,
    MAX_HISTORY_SIZE,
    MAX_ESCALATION_LOG_SIZE,
    SERVICE_NAME,
    SERVICE_VERSION,
    record_event,
    cleanup_expired_overrides,
    compute_rotation,
    notify_service,
)

client = TestClient(app)


# ============================================
# Fixtures
# ============================================
@pytest.fixture(autouse=True)
def reset_state():
    """Reset in-memory state before each test, then re-seed one schedule."""
    schedules_db.clear()
    overrides_db.clear()
    escalation_log.clear()
    oncall_history.clear()
    last_known_oncall.clear()
    # Seed one schedule (simulates startup)
    schedules_db["platform-engineering"] = {
        "id": "test-pe-id",
        "team": "platform-engineering",
        "rotation_type": "weekly",
        "members": [
            {"name": "Alice Martin", "email": "alice@company.com", "role": "primary"},
            {"name": "Bob Dupont", "email": "bob@company.com", "role": "primary"},
            {"name": "Carol Chen", "email": "carol@company.com", "role": "secondary"},
        ],
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": None,
    }
    yield


# ============================================
# Health & Metrics
# ============================================
class TestHealth:
    def test_health_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_ok_status(self):
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == SERVICE_NAME
        assert data["version"] == SERVICE_VERSION

    def test_health_includes_schedules_count(self):
        response = client.get("/health")
        data = response.json()
        assert "schedules_count" in data
        assert data["schedules_count"] >= 1

    def test_health_includes_timestamp(self):
        response = client.get("/health")
        data = response.json()
        assert "timestamp" in data

    def test_health_includes_active_overrides(self):
        response = client.get("/health")
        data = response.json()
        assert "active_overrides" in data
        assert data["active_overrides"] == 0


class TestReadiness:
    def test_readiness_returns_200(self):
        response = client.get("/health/ready")
        assert response.status_code == 200

    def test_readiness_has_ready_status(self):
        response = client.get("/health/ready")
        data = response.json()
        assert data["status"] == "ready"
        assert data["service"] == SERVICE_NAME
        assert data["schedules_loaded"] is True

    def test_readiness_no_schedules(self):
        schedules_db.clear()
        response = client.get("/health/ready")
        data = response.json()
        assert data["schedules_loaded"] is False


class TestRequestID:
    def test_response_has_request_id_header(self):
        response = client.get("/health")
        assert "X-Request-ID" in response.headers

    def test_request_id_propagated(self):
        custom_id = "test-req-12345"
        response = client.get("/health", headers={"X-Request-ID": custom_id})
        assert response.headers["X-Request-ID"] == custom_id

    def test_auto_generated_request_id(self):
        response = client.get("/health")
        rid = response.headers.get("X-Request-ID", "")
        assert len(rid) > 0  # auto-generated UUID


class TestMetrics:
    def test_metrics_returns_200(self):
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_contains_oncall_counters(self):
        response = client.get("/metrics")
        text = response.text
        assert "oncall_requests_total" in text or "oncall_" in text

    def test_metrics_contains_escalation_counter(self):
        client.post("/api/v1/escalate", json={
            "team": "platform-engineering",
            "incident_id": "test-123",
        })
        response = client.get("/metrics")
        assert "oncall_escalations_total" in response.text

    def test_metrics_contains_notifications_counter(self):
        client.post("/api/v1/escalate", json={
            "team": "platform-engineering",
            "incident_id": "test-456",
        })
        response = client.get("/metrics")
        assert "oncall_notifications_sent_total" in response.text

    def test_metrics_contains_rotation_changes(self):
        response = client.get("/metrics")
        assert "oncall_rotation_changes_total" in response.text


# ============================================
# Schedule CRUD
# ============================================
class TestSchedules:
    def test_create_schedule(self):
        response = client.post("/api/v1/schedules", json={
            "team": "test-team",
            "rotation_type": "weekly",
            "members": [
                {"name": "Alice", "email": "alice@test.com", "role": "primary"},
                {"name": "Bob", "email": "bob@test.com", "role": "secondary"},
            ],
        })
        assert response.status_code == 201
        data = response.json()
        assert data["team"] == "test-team"
        assert data["rotation_type"] == "weekly"
        assert len(data["members"]) == 2
        assert "id" in data
        assert "created_at" in data

    def test_create_schedule_daily_rotation(self):
        response = client.post("/api/v1/schedules", json={
            "team": "daily-team",
            "rotation_type": "daily",
            "members": [
                {"name": "Alice", "email": "alice@test.com", "role": "primary"},
            ],
        })
        assert response.status_code == 201
        assert response.json()["rotation_type"] == "daily"

    def test_create_schedule_biweekly_rotation(self):
        response = client.post("/api/v1/schedules", json={
            "team": "biweekly-team",
            "rotation_type": "biweekly",
            "members": [
                {"name": "Alice", "email": "alice@test.com", "role": "primary"},
            ],
        })
        assert response.status_code == 201
        assert response.json()["rotation_type"] == "biweekly"

    def test_create_schedule_no_primary_member_fails(self):
        response = client.post("/api/v1/schedules", json={
            "team": "no-primary-team",
            "rotation_type": "weekly",
            "members": [
                {"name": "Bob", "email": "bob@test.com", "role": "secondary"},
            ],
        })
        assert response.status_code == 400
        assert "primary" in response.json()["detail"].lower()

    def test_create_schedule_empty_members_fails(self):
        response = client.post("/api/v1/schedules", json={
            "team": "empty-team",
            "rotation_type": "weekly",
            "members": [],
        })
        assert response.status_code == 422

    def test_create_schedule_replaces_existing(self):
        client.post("/api/v1/schedules", json={
            "team": "replace-team",
            "rotation_type": "weekly",
            "members": [
                {"name": "Alice", "email": "alice@test.com", "role": "primary"},
            ],
        })
        response = client.post("/api/v1/schedules", json={
            "team": "replace-team",
            "rotation_type": "daily",
            "members": [
                {"name": "Bob", "email": "bob@test.com", "role": "primary"},
            ],
        })
        assert response.status_code == 201
        assert response.json()["rotation_type"] == "daily"

    def test_create_schedule_records_history(self):
        client.post("/api/v1/schedules", json={
            "team": "history-test",
            "rotation_type": "weekly",
            "members": [
                {"name": "Alice", "email": "alice@test.com", "role": "primary"},
            ],
        })
        events = [e for e in oncall_history if e["team"] == "history-test" and e["event_type"] == "schedule_created"]
        assert len(events) >= 1

    def test_list_schedules(self):
        response = client.get("/api/v1/schedules")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_schedule_by_team(self):
        response = client.get("/api/v1/schedules/platform-engineering")
        assert response.status_code == 200
        data = response.json()
        assert data["team"] == "platform-engineering"

    def test_get_schedule_not_found(self):
        response = client.get("/api/v1/schedules/nonexistent-team")
        assert response.status_code == 404

    def test_delete_schedule(self):
        response = client.delete("/api/v1/schedules/platform-engineering")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"
        response = client.get("/api/v1/schedules/platform-engineering")
        assert response.status_code == 404

    def test_delete_schedule_not_found(self):
        response = client.delete("/api/v1/schedules/nonexistent")
        assert response.status_code == 404

    def test_delete_schedule_records_history(self):
        client.delete("/api/v1/schedules/platform-engineering")
        events = [e for e in oncall_history if e["event_type"] == "schedule_deleted"]
        assert len(events) >= 1

    def test_create_schedule_invalid_rotation_type(self):
        response = client.post("/api/v1/schedules", json={
            "team": "bad-rotation",
            "rotation_type": "monthly",
            "members": [
                {"name": "Alice", "email": "alice@test.com", "role": "primary"},
            ],
        })
        assert response.status_code == 422

    def test_create_schedule_invalid_role(self):
        response = client.post("/api/v1/schedules", json={
            "team": "bad-role",
            "rotation_type": "weekly",
            "members": [
                {"name": "Alice", "email": "alice@test.com", "role": "manager"},
            ],
        })
        assert response.status_code == 422


# ============================================
# PATCH Schedule
# ============================================
class TestScheduleUpdate:
    def test_patch_rotation_type(self):
        response = client.patch("/api/v1/schedules/platform-engineering", json={
            "rotation_type": "daily",
        })
        assert response.status_code == 200
        assert response.json()["rotation_type"] == "daily"
        assert response.json()["updated_at"] is not None

    def test_patch_add_member(self):
        response = client.patch("/api/v1/schedules/platform-engineering", json={
            "add_members": [
                {"name": "New Guy", "email": "new@test.com", "role": "primary"},
            ],
        })
        assert response.status_code == 200
        names = [m["name"] for m in response.json()["members"]]
        assert "New Guy" in names

    def test_patch_add_duplicate_member_ignored(self):
        response = client.patch("/api/v1/schedules/platform-engineering", json={
            "add_members": [
                {"name": "Alice Martin", "email": "alice@company.com", "role": "primary"},
            ],
        })
        assert response.status_code == 200
        names = [m["name"] for m in response.json()["members"]]
        assert names.count("Alice Martin") == 1

    def test_patch_remove_member(self):
        response = client.patch("/api/v1/schedules/platform-engineering", json={
            "remove_members": ["Carol Chen"],
        })
        assert response.status_code == 200
        names = [m["name"] for m in response.json()["members"]]
        assert "Carol Chen" not in names

    def test_patch_remove_all_primary_fails(self):
        response = client.patch("/api/v1/schedules/platform-engineering", json={
            "remove_members": ["Alice Martin", "Bob Dupont"],
        })
        assert response.status_code == 400
        assert "primary" in response.json()["detail"].lower()

    def test_patch_nonexistent_team(self):
        response = client.patch("/api/v1/schedules/nonexistent", json={
            "rotation_type": "daily",
        })
        assert response.status_code == 404

    def test_patch_records_history(self):
        client.patch("/api/v1/schedules/platform-engineering", json={
            "rotation_type": "daily",
        })
        events = [e for e in oncall_history if e["event_type"] == "schedule_updated"]
        assert len(events) >= 1
        assert "rotation_type" in events[-1]["details"]

    def test_patch_add_and_remove_simultaneously(self):
        response = client.patch("/api/v1/schedules/platform-engineering", json={
            "add_members": [
                {"name": "NewPrimary", "email": "np@test.com", "role": "primary"},
            ],
            "remove_members": ["Bob Dupont"],
        })
        assert response.status_code == 200
        names = [m["name"] for m in response.json()["members"]]
        assert "NewPrimary" in names
        assert "Bob Dupont" not in names


# ============================================
# On-Call Current
# ============================================
class TestOnCallCurrent:
    def test_get_current_oncall(self):
        response = client.get("/api/v1/oncall/current?team=platform-engineering")
        assert response.status_code == 200
        data = response.json()
        assert data["team"] == "platform-engineering"
        assert "primary" in data
        assert "name" in data["primary"]
        assert "email" in data["primary"]

    def test_get_current_oncall_has_secondary(self):
        response = client.get("/api/v1/oncall/current?team=platform-engineering")
        data = response.json()
        assert "secondary" in data
        assert data["secondary"] is not None
        assert "name" in data["secondary"]

    def test_get_current_oncall_includes_schedule_id(self):
        response = client.get("/api/v1/oncall/current?team=platform-engineering")
        data = response.json()
        assert "schedule_id" in data
        assert "rotation_type" in data

    def test_get_current_oncall_team_not_found(self):
        response = client.get("/api/v1/oncall/current?team=nonexistent")
        assert response.status_code == 404

    def test_get_current_oncall_missing_team_param(self):
        response = client.get("/api/v1/oncall/current")
        assert response.status_code == 422

    def test_get_current_oncall_daily_rotation(self):
        client.post("/api/v1/schedules", json={
            "team": "daily-oncall",
            "rotation_type": "daily",
            "members": [
                {"name": "Day1", "email": "day1@test.com", "role": "primary"},
                {"name": "Day2", "email": "day2@test.com", "role": "primary"},
            ],
        })
        response = client.get("/api/v1/oncall/current?team=daily-oncall")
        assert response.status_code == 200
        assert response.json()["rotation_type"] == "daily"

    def test_get_current_oncall_no_secondary(self):
        client.post("/api/v1/schedules", json={
            "team": "no-sec",
            "rotation_type": "weekly",
            "members": [
                {"name": "Only Primary", "email": "primary@test.com", "role": "primary"},
            ],
        })
        response = client.get("/api/v1/oncall/current?team=no-sec")
        assert response.status_code == 200
        data = response.json()
        assert data["secondary"] is None

    def test_rotation_change_detected(self):
        """When last_known_oncall differs from current, a rotation_change event fires."""
        last_known_oncall["platform-engineering"] = "DOES_NOT_EXIST"
        response = client.get("/api/v1/oncall/current?team=platform-engineering")
        assert response.status_code == 200
        events = [e for e in oncall_history if e["event_type"] == "rotation_change"]
        assert len(events) >= 1


# ============================================
# Overrides
# ============================================
class TestOverrides:
    def test_set_override(self):
        response = client.post("/api/v1/oncall/override", json={
            "team": "platform-engineering",
            "user_name": "Override User",
            "user_email": "override@test.com",
            "reason": "Test override",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "override_set"
        assert "expires_at" in data
        assert data["duration_hours"] == DEFAULT_OVERRIDE_HOURS

    def test_set_override_custom_duration(self):
        response = client.post("/api/v1/oncall/override", json={
            "team": "platform-engineering",
            "user_name": "Override User",
            "user_email": "override@test.com",
            "duration_hours": 24,
        })
        assert response.status_code == 200
        assert response.json()["duration_hours"] == 24

    def test_override_affects_current_oncall(self):
        client.post("/api/v1/oncall/override", json={
            "team": "platform-engineering",
            "user_name": "Override User",
            "user_email": "override@test.com",
        })
        response = client.get("/api/v1/oncall/current?team=platform-engineering")
        data = response.json()
        assert data["primary"]["name"] == "Override User"
        assert data["primary"]["override"] is True
        assert "expires_at" in data["primary"]

    def test_override_expired_returns_rotation(self):
        now = datetime.now(timezone.utc)
        overrides_db["platform-engineering"] = {
            "user_name": "Expired User",
            "user_email": "expired@test.com",
            "reason": "Old override",
            "duration_hours": 1,
            "created_at": (now - timedelta(hours=2)).isoformat(),
            "expires_at": (now - timedelta(hours=1)).isoformat(),
        }
        response = client.get("/api/v1/oncall/current?team=platform-engineering")
        data = response.json()
        assert data["primary"]["name"] != "Expired User"
        assert data["primary"].get("override") is not True

    def test_remove_override(self):
        client.post("/api/v1/oncall/override", json={
            "team": "platform-engineering",
            "user_name": "Override User",
            "user_email": "override@test.com",
        })
        response = client.delete("/api/v1/oncall/override/platform-engineering")
        assert response.status_code == 200
        assert response.json()["status"] == "override_removed"

    def test_remove_override_not_found(self):
        response = client.delete("/api/v1/oncall/override/nonexistent")
        assert response.status_code == 404

    def test_override_team_not_found(self):
        response = client.post("/api/v1/oncall/override", json={
            "team": "nonexistent",
            "user_name": "User",
            "user_email": "user@test.com",
        })
        assert response.status_code == 404

    def test_list_active_overrides(self):
        client.post("/api/v1/oncall/override", json={
            "team": "platform-engineering",
            "user_name": "Override User",
            "user_email": "override@test.com",
        })
        response = client.get("/api/v1/oncall/overrides")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["team"] == "platform-engineering"
        assert data[0]["user_name"] == "Override User"
        assert "expires_at" in data[0]

    def test_list_active_overrides_excludes_expired(self):
        now = datetime.now(timezone.utc)
        overrides_db["platform-engineering"] = {
            "user_name": "Expired",
            "user_email": "expired@test.com",
            "reason": "test",
            "duration_hours": 1,
            "created_at": (now - timedelta(hours=2)).isoformat(),
            "expires_at": (now - timedelta(hours=1)).isoformat(),
        }
        response = client.get("/api/v1/oncall/overrides")
        assert response.status_code == 200
        assert len(response.json()) == 0

    def test_override_records_history(self):
        client.post("/api/v1/oncall/override", json={
            "team": "platform-engineering",
            "user_name": "Override User",
            "user_email": "override@test.com",
        })
        events = [e for e in oncall_history if e["event_type"] == "override_start"]
        assert len(events) >= 1

    def test_remove_override_records_history(self):
        client.post("/api/v1/oncall/override", json={
            "team": "platform-engineering",
            "user_name": "Override User",
            "user_email": "override@test.com",
        })
        client.delete("/api/v1/oncall/override/platform-engineering")
        events = [e for e in oncall_history if e["event_type"] == "override_end"]
        assert len(events) >= 1

    def test_override_duration_too_large_fails(self):
        response = client.post("/api/v1/oncall/override", json={
            "team": "platform-engineering",
            "user_name": "User",
            "user_email": "user@test.com",
            "duration_hours": 999,
        })
        assert response.status_code == 422


# ============================================
# Escalation
# ============================================
class TestEscalation:
    def test_escalate(self):
        response = client.post("/api/v1/escalate", json={
            "team": "platform-engineering",
            "incident_id": "inc-001",
            "reason": "No acknowledgment",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "escalated"
        assert data["team"] == "platform-engineering"
        assert data["incident_id"] == "inc-001"
        assert "escalation_id" in data
        assert "timestamp" in data

    def test_escalate_includes_secondary(self):
        response = client.post("/api/v1/escalate", json={
            "team": "platform-engineering",
            "incident_id": "inc-002",
        })
        data = response.json()
        assert data["escalated_to"] is not None
        assert "name" in data["escalated_to"]
        assert "email" in data["escalated_to"]

    def test_escalate_unknown_team(self):
        response = client.post("/api/v1/escalate", json={
            "team": "unknown-team",
            "incident_id": "inc-003",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["escalated_to"] is None

    def test_escalate_records_history(self):
        client.post("/api/v1/escalate", json={
            "team": "platform-engineering",
            "incident_id": "inc-history",
        })
        events = [e for e in oncall_history if e["event_type"] == "escalation"]
        assert len(events) >= 1
        assert events[-1]["details"]["incident_id"] == "inc-history"

    def test_list_escalations(self):
        client.post("/api/v1/escalate", json={
            "team": "platform-engineering",
            "incident_id": "inc-010",
        })
        client.post("/api/v1/escalate", json={
            "team": "platform-engineering",
            "incident_id": "inc-011",
        })
        response = client.get("/api/v1/escalations")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_list_escalations_filter_by_team(self):
        client.post("/api/v1/escalate", json={
            "team": "platform-engineering",
            "incident_id": "inc-020",
        })
        client.post("/api/v1/escalate", json={
            "team": "other-team",
            "incident_id": "inc-021",
        })
        response = client.get("/api/v1/escalations?team=platform-engineering")
        assert response.status_code == 200
        data = response.json()
        for item in data:
            assert item["team"] == "platform-engineering"

    def test_list_escalations_with_limit(self):
        for i in range(5):
            client.post("/api/v1/escalate", json={
                "team": "platform-engineering",
                "incident_id": f"inc-limit-{i}",
            })
        response = client.get("/api/v1/escalations?limit=2")
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_escalation_default_reason(self):
        response = client.post("/api/v1/escalate", json={
            "team": "platform-engineering",
            "incident_id": "inc-030",
        })
        data = response.json()
        assert "No acknowledgment" in data["message"] or "escalat" in data["message"].lower()

    def test_escalation_empty_team_fails(self):
        response = client.post("/api/v1/escalate", json={
            "team": "",
            "incident_id": "inc-999",
        })
        assert response.status_code == 422

    def test_escalation_empty_incident_id_fails(self):
        response = client.post("/api/v1/escalate", json={
            "team": "platform-engineering",
            "incident_id": "",
        })
        assert response.status_code == 422


# ============================================
# On-Call History
# ============================================
class TestHistory:
    def test_history_empty(self):
        response = client.get("/api/v1/oncall/history")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_history_after_schedule_create(self):
        client.post("/api/v1/schedules", json={
            "team": "hist-team",
            "rotation_type": "weekly",
            "members": [
                {"name": "Hist User", "email": "hist@test.com", "role": "primary"},
            ],
        })
        response = client.get("/api/v1/oncall/history?team=hist-team")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[-1]["event_type"] == "schedule_created"

    def test_history_after_escalation(self):
        client.post("/api/v1/escalate", json={
            "team": "platform-engineering",
            "incident_id": "hist-esc-001",
        })
        response = client.get("/api/v1/oncall/history?event_type=escalation")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_history_after_override(self):
        client.post("/api/v1/oncall/override", json={
            "team": "platform-engineering",
            "user_name": "Hist Override",
            "user_email": "hist@test.com",
        })
        response = client.get("/api/v1/oncall/history?event_type=override_start")
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_history_filter_by_team(self):
        client.post("/api/v1/schedules", json={
            "team": "team-a",
            "rotation_type": "weekly",
            "members": [{"name": "A", "email": "a@t.com", "role": "primary"}],
        })
        client.post("/api/v1/schedules", json={
            "team": "team-b",
            "rotation_type": "weekly",
            "members": [{"name": "B", "email": "b@t.com", "role": "primary"}],
        })
        response = client.get("/api/v1/oncall/history?team=team-a")
        data = response.json()
        for event in data:
            assert event["team"] == "team-a"

    def test_history_with_limit(self):
        for i in range(5):
            client.post("/api/v1/schedules", json={
                "team": f"limit-team-{i}",
                "rotation_type": "weekly",
                "members": [{"name": f"User{i}", "email": f"u{i}@t.com", "role": "primary"}],
            })
        response = client.get("/api/v1/oncall/history?limit=2")
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_history_event_structure(self):
        client.post("/api/v1/escalate", json={
            "team": "platform-engineering",
            "incident_id": "struct-test",
        })
        response = client.get("/api/v1/oncall/history")
        data = response.json()
        event = data[-1]
        assert "event_id" in event
        assert "event_type" in event
        assert "team" in event
        assert "timestamp" in event
        assert "details" in event


# ============================================
# Teams
# ============================================
class TestTeams:
    def test_list_teams(self):
        response = client.get("/api/v1/teams")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_teams_structure(self):
        response = client.get("/api/v1/teams")
        data = response.json()
        team = data[0]
        assert "team" in team
        assert "members_count" in team
        assert "rotation_type" in team
        assert "has_override" in team

    def test_list_teams_shows_override(self):
        client.post("/api/v1/oncall/override", json={
            "team": "platform-engineering",
            "user_name": "Override User",
            "user_email": "override@test.com",
        })
        response = client.get("/api/v1/teams")
        data = response.json()
        pe_team = next(t for t in data if t["team"] == "platform-engineering")
        assert pe_team["has_override"] is True


# ============================================
# Stats (NEW)
# ============================================
class TestStats:
    def test_stats_returns_200(self):
        response = client.get("/api/v1/oncall/stats")
        assert response.status_code == 200

    def test_stats_structure(self):
        response = client.get("/api/v1/oncall/stats")
        data = response.json()
        assert "total_schedules" in data
        assert "total_members" in data
        assert "active_overrides" in data
        assert "total_escalations" in data
        assert "total_history_events" in data
        assert "rotation_types" in data
        assert "event_types" in data

    def test_stats_counts_correct(self):
        response = client.get("/api/v1/oncall/stats")
        data = response.json()
        assert data["total_schedules"] == 1
        assert data["total_members"] == 3  # Alice, Bob, Carol
        assert data["active_overrides"] == 0

    def test_stats_after_escalation(self):
        client.post("/api/v1/escalate", json={
            "team": "platform-engineering",
            "incident_id": "stat-esc",
        })
        response = client.get("/api/v1/oncall/stats")
        data = response.json()
        assert data["total_escalations"] == 1
        assert "escalation" in data["event_types"]

    def test_stats_rotation_types(self):
        client.post("/api/v1/schedules", json={
            "team": "daily-stats",
            "rotation_type": "daily",
            "members": [{"name": "D", "email": "d@t.com", "role": "primary"}],
        })
        response = client.get("/api/v1/oncall/stats")
        data = response.json()
        assert "weekly" in data["rotation_types"]
        assert "daily" in data["rotation_types"]


# ============================================
# Configuration
# ============================================
class TestConfiguration:
    def test_service_name_from_env(self):
        assert SERVICE_NAME == "oncall-service"

    def test_service_version_from_env(self):
        assert SERVICE_VERSION == "2.1.0"

    def test_default_override_hours(self):
        assert isinstance(DEFAULT_OVERRIDE_HOURS, int)
        assert DEFAULT_OVERRIDE_HOURS > 0

    def test_notification_timeout_is_float(self):
        from main import NOTIFICATION_TIMEOUT
        assert isinstance(NOTIFICATION_TIMEOUT, float)

    def test_cors_origins_is_list(self):
        from main import CORS_ORIGINS
        assert isinstance(CORS_ORIGINS, list)
        assert len(CORS_ORIGINS) >= 1

    def test_max_history_size(self):
        assert isinstance(MAX_HISTORY_SIZE, int)
        assert MAX_HISTORY_SIZE > 0

    def test_max_escalation_log_size(self):
        assert isinstance(MAX_ESCALATION_LOG_SIZE, int)
        assert MAX_ESCALATION_LOG_SIZE > 0


# ============================================
# Helper Functions
# ============================================
class TestHelpers:
    def test_record_event_returns_event(self):
        event = record_event("test_event", "test-team", {"key": "value"})
        assert event["event_type"] == "test_event"
        assert event["team"] == "test-team"
        assert event["details"]["key"] == "value"
        assert "event_id" in event
        assert "timestamp" in event

    def test_record_event_ring_buffer(self):
        """History should be bounded by MAX_HISTORY_SIZE."""
        oncall_history.clear()
        for i in range(MAX_HISTORY_SIZE + 50):
            record_event("overflow", "team", {"i": i})
        assert len(oncall_history) <= MAX_HISTORY_SIZE

    def test_cleanup_expired_overrides_removes_expired(self):
        now = datetime.now(timezone.utc)
        overrides_db["expired-team"] = {
            "user_name": "Exp",
            "user_email": "exp@t.com",
            "expires_at": (now - timedelta(hours=1)).isoformat(),
        }
        cleanup_expired_overrides()
        assert "expired-team" not in overrides_db

    def test_cleanup_expired_overrides_keeps_active(self):
        now = datetime.now(timezone.utc)
        overrides_db["active-team"] = {
            "user_name": "Act",
            "user_email": "act@t.com",
            "expires_at": (now + timedelta(hours=5)).isoformat(),
        }
        cleanup_expired_overrides()
        assert "active-team" in overrides_db

    def test_compute_rotation_weekly(self):
        schedule = {
            "rotation_type": "weekly",
            "members": [
                {"name": "A", "email": "a@t.com", "role": "primary"},
                {"name": "B", "email": "b@t.com", "role": "primary"},
                {"name": "C", "email": "c@t.com", "role": "secondary"},
            ],
        }
        primary, secondary = compute_rotation(schedule)
        assert primary is not None
        assert primary["role"] == "primary"
        assert secondary is not None
        assert secondary["role"] == "secondary"

    def test_compute_rotation_no_primary(self):
        schedule = {
            "rotation_type": "weekly",
            "members": [
                {"name": "Only Sec", "email": "sec@t.com", "role": "secondary"},
            ],
        }
        primary, secondary = compute_rotation(schedule)
        assert primary is None
        assert secondary is None

    def test_compute_rotation_no_secondary(self):
        schedule = {
            "rotation_type": "daily",
            "members": [
                {"name": "Only Pri", "email": "pri@t.com", "role": "primary"},
            ],
        }
        primary, secondary = compute_rotation(schedule)
        assert primary is not None
        assert secondary is None

    def test_compute_rotation_biweekly(self):
        schedule = {
            "rotation_type": "biweekly",
            "members": [
                {"name": "A", "email": "a@t.com", "role": "primary"},
                {"name": "B", "email": "b@t.com", "role": "primary"},
            ],
        }
        primary, secondary = compute_rotation(schedule)
        assert primary is not None
        assert primary["name"] in ("A", "B")

    @patch("main.httpx.Client")
    def test_notify_service_success(self, mock_client_class):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client
        notify_service("mock", "test@t.com", "hello", "inc-1")
        mock_client.post.assert_called_once()

    @patch("main.httpx.Client")
    def test_notify_service_failure_handled(self, mock_client_class):
        mock_client_class.side_effect = Exception("connection refused")
        # Should not raise
        notify_service("mock", "test@t.com", "hello")
