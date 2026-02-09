#!/bin/bash
# ============================================
# STAGE 8: Integration / E2E Tests
# ============================================
# Runs end-to-end tests against the live stack
# Tests the full request lifecycle across services
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
TOTAL=0

BASE_URL_ALERT="http://localhost:8001"
BASE_URL_INCIDENT="http://localhost:8002"
BASE_URL_ONCALL="http://localhost:8003"
BASE_URL_NOTIF="http://localhost:8004"
BASE_URL_WEB="http://localhost:8080"

# -----------------------------------------------
run_test() {
    local name="$1"
    local cmd="$2"
    local expected="$3"

    TOTAL=$((TOTAL + 1))
    echo -n "  [$TOTAL] $name ... "

    RESULT=$(eval "$cmd" 2>/dev/null)
    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ] && echo "$RESULT" | grep -q "$expected"; then
        echo -e "${GREEN}PASS${NC}"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}FAIL${NC}"
        echo -e "       Expected: $expected"
        echo -e "       Got: $(echo "$RESULT" | head -1)"
        FAIL=$((FAIL + 1))
    fi
}

# -----------------------------------------------
echo -e "${YELLOW}🔗 Running Integration Tests...${NC}"
echo ""

# --- 1. Health checks ---
echo -e "${YELLOW}  ── Health Checks ──${NC}"
run_test "Alert Ingestion /health" \
    "curl -s $BASE_URL_ALERT/health" \
    "healthy"

run_test "Incident Management /health" \
    "curl -s $BASE_URL_INCIDENT/health" \
    "healthy"

run_test "OnCall Service /health" \
    "curl -s $BASE_URL_ONCALL/health" \
    "healthy"

run_test "Notification Service /health" \
    "curl -s $BASE_URL_NOTIF/health" \
    "healthy"

run_test "Web UI /health" \
    "curl -s $BASE_URL_WEB/health" \
    "healthy"

echo ""

# --- 2. Prometheus metrics exposed ---
echo -e "${YELLOW}  ── Metrics Endpoints ──${NC}"
run_test "OnCall /metrics exposes prometheus" \
    "curl -s $BASE_URL_ONCALL/metrics" \
    "request_count"

run_test "Alert Ingestion /metrics" \
    "curl -s $BASE_URL_ALERT/metrics" \
    "HELP\|TYPE\|_total\|_count"

run_test "Incident Management /metrics" \
    "curl -s $BASE_URL_INCIDENT/metrics" \
    "HELP\|TYPE\|_total\|_count"

echo ""

# --- 3. OnCall Service CRUD ---
echo -e "${YELLOW}  ── OnCall Service E2E ──${NC}"

# Create schedule
run_test "POST /api/v1/schedules — create schedule" \
    "curl -s -o /dev/null -w '%{http_code}' -X POST $BASE_URL_ONCALL/api/v1/schedules -H 'Content-Type: application/json' -d '{\"team\":\"integration-test\",\"members\":[\"tester1\",\"tester2\"],\"rotation_days\":7}'" \
    "200"

# Get schedules
run_test "GET /api/v1/schedules — list schedules" \
    "curl -s $BASE_URL_ONCALL/api/v1/schedules" \
    "integration-test"

# Get current on-call
run_test "GET /api/v1/oncall/current — current on-call" \
    "curl -s -o /dev/null -w '%{http_code}' $BASE_URL_ONCALL/api/v1/oncall/current?team=integration-test" \
    "200"

# Set override
run_test "POST /api/v1/oncall/override — set override" \
    "curl -s -o /dev/null -w '%{http_code}' -X POST $BASE_URL_ONCALL/api/v1/oncall/override -H 'Content-Type: application/json' -d '{\"team\":\"integration-test\",\"override_person\":\"tester-override\",\"duration_hours\":2}'" \
    "200"

# Escalate
run_test "POST /api/v1/escalate — escalate incident" \
    "curl -s -o /dev/null -w '%{http_code}' -X POST $BASE_URL_ONCALL/api/v1/escalate -H 'Content-Type: application/json' -d '{\"team\":\"integration-test\",\"incident_id\":\"INT-TEST-001\",\"reason\":\"Integration test escalation\"}'" \
    "200"

# Get escalations
run_test "GET /api/v1/escalations — list escalations" \
    "curl -s $BASE_URL_ONCALL/api/v1/escalations" \
    "INT-TEST-001"

# Get teams
run_test "GET /api/v1/teams — list teams" \
    "curl -s $BASE_URL_ONCALL/api/v1/teams" \
    "integration-test"

echo ""

# --- 4. Cross-service: Prometheus scraping ---
echo -e "${YELLOW}  ── Cross-Service Checks ──${NC}"

run_test "Prometheus targets — all UP" \
    "curl -s http://localhost:9090/api/v1/targets | python3 -c \"import sys,json; d=json.load(sys.stdin); targets=[t for t in d['data']['activeTargets'] if t['health']=='up']; print(len(targets))\"" \
    "6"

run_test "Grafana health check" \
    "curl -s http://localhost:3000/api/health" \
    "ok"

run_test "Grafana datasource configured" \
    "curl -s -u admin:admin http://localhost:3000/api/datasources | python3 -c \"import sys,json; ds=json.load(sys.stdin); print(len(ds))\"" \
    "1"

run_test "Grafana dashboards provisioned (>=3)" \
    "curl -s -u admin:admin 'http://localhost:3000/api/search?type=dash-db' | python3 -c \"import sys,json; d=json.load(sys.stdin); print('OK' if len(d)>=3 else 'FAIL')\"" \
    "OK"

echo ""

# --- Summary ---
echo -e "${YELLOW}═══════════════════════════════════════${NC}"
echo -e "  Integration Tests: ${GREEN}$PASS passed${NC} / ${RED}$FAIL failed${NC} / $TOTAL total"
echo -e "${YELLOW}═══════════════════════════════════════${NC}"
echo ""

if [ $FAIL -gt 0 ]; then
    echo -e "${RED}❌ $FAIL integration test(s) failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All integration tests passed!${NC}"
exit 0
