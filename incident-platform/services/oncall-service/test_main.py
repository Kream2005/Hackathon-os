"""
Tests for On-Call Service
Coverage target: ≥ 75% (above the 60% minimum)
"""

import pytest
from fastapi.testclient import TestClient
from main import app, schedules_db, overrides_db, escalation_log

client = TestClient(app)


# ============================================
# Fixtures
# ============================================
@pytest.fixture(autouse=True)
def reset_state():
    """Reset in-memory state before each test, then re-seed defaults."""
    schedules_db.clear()
    overrides_db.clear()
    escalation_log.clear()
    # Re-seed default schedules (simulates startup)
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
        assert data["service"] == "oncall-service"
        assert data["version"] == "1.0.0"

    def test_health_includes_schedules_count(self):
        response = client.get("/health")
        data = response.json()
        assert "schedules_count" in data
        assert data["schedules_count"] >= 1

    def test_health_includes_timestamp(self):
        response = client.get("/health")
        data = response.json()
        assert "timestamp" in data


class TestMetrics:
    def test_metrics_returns_200(self):
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_contains_oncall_counters(self):
        response = client.get("/metrics")
        text = response.text
        assert "oncall_requests_total" in text or "oncall_" in text

    def test_metrics_contains_escalation_counter(self):
        # Trigger an escalation first to ensure the metric exists
        client.post("/api/v1/escalate", json={
            "team": "platform-engineering",
            "incident_id": "test-123",
        })
        response = client.get("/metrics")
        text = response.text
        assert "oncall_escalations_total" in text

    def test_metrics_contains_notifications_counter(self):
        client.post("/api/v1/escalate", json={
            "team": "platform-engineering",
            "incident_id": "test-456",
        })
        response = client.get("/metrics")
        text = response.text
        assert "oncall_notifications_sent_total" in text


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
        assert response.status_code == 422  # Pydantic validation error

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

    def test_list_schedules(self):
        response = client.get("/api/v1/schedules")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # At least the seeded schedule

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

        # Verify it's gone
        response = client.get("/api/v1/schedules/platform-engineering")
        assert response.status_code == 404

    def test_delete_schedule_not_found(self):
        response = client.delete("/api/v1/schedules/nonexistent")
        assert response.status_code == 404


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
        assert response.status_code == 422  # Missing required param

    def test_get_current_oncall_daily_rotation(self):
        # Create daily rotation schedule
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
        assert response.json()["status"] == "override_set"

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

    def test_remove_override(self):
        # Set override first
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
        # Should escalate to secondary
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

    def test_list_escalations(self):
        # Create some escalations
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

    def test_escalation_default_reason(self):
        response = client.post("/api/v1/escalate", json={
            "team": "platform-engineering",
            "incident_id": "inc-030",
        })
        data = response.json()
        assert "No acknowledgment" in data["message"] or "escalat" in data["message"].lower()


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
