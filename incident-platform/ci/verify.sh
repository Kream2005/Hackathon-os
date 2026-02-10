#!/bin/bash
# ============================================
# STAGE 7: Post-Deployment Verification
# ============================================
# Comprehensive post-deploy validation:
#   1. Health checks (all services + monitoring)
#   2. Prometheus targets validation
#   3. Database connectivity verification
#   4. E2E smoke tests (via API Gateway)
#   5. Metrics endpoint validation
# ============================================

set -euo pipefail

# ── Colors ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── Configuration ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

CHECKS=0
PASSED=0
FAILED=0
WARNINGS=0

# ── Logging helpers ──
log_info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; WARNINGS=$((WARNINGS + 1)); }
log_error() { echo -e "${RED}[FAIL]${NC} $*"; }
log_section() { echo ""; echo -e "${BOLD}${YELLOW}── $* ──${NC}"; echo ""; }

# ── Test runner ──
check() {
    local name="$1"
    local url="$2"
    local expected_code="${3:-200}"

    CHECKS=$((CHECKS + 1))
    echo -n "  [$CHECKS] $name ... "

    HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" "$url" --max-time 5 2>/dev/null || echo "000")

    if [ "$HTTP_CODE" = "$expected_code" ]; then
        echo -e "${GREEN}PASS${NC} (HTTP $HTTP_CODE)"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}FAIL${NC} (HTTP $HTTP_CODE, expected $expected_code)"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

check_response() {
    local name="$1"
    local cmd="$2"
    local expected="$3"

    CHECKS=$((CHECKS + 1))
    echo -n "  [$CHECKS] $name ... "

    RESULT=$(eval "$cmd" 2>/dev/null) || true

    if echo "$RESULT" | grep -q "$expected" 2>/dev/null; then
        echo -e "${GREEN}PASS${NC}"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}FAIL${NC}"
        echo -e "       Expected pattern: $expected"
        echo -e "       Got: $(echo "$RESULT" | head -c 200)"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# ============================================
# 1. HEALTH CHECKS
# ============================================
log_section "1/5 — Service Health Checks"

check "Alert Ingestion"       "http://localhost:8001/health"
check "Incident Management"   "http://localhost:8002/health"
check "On-Call Service"        "http://localhost:8003/health"
check "Notification Service"   "http://localhost:8004/health"
check "API Gateway"            "http://localhost:8080/health"
check "Web UI (nginx)"         "http://localhost:3001/"
check "Prometheus"             "http://localhost:9090/-/healthy"
check "Grafana"                "http://localhost:3000/api/health"

# ============================================
# 2. PROMETHEUS TARGETS
# ============================================
log_section "2/5 — Prometheus Targets Validation"

PROM_TARGETS=$(curl -sf "http://localhost:9090/api/v1/targets" --max-time 5 2>/dev/null || echo "")

if [ -n "$PROM_TARGETS" ]; then
    TARGETS_UP=$(echo "$PROM_TARGETS" | python3 -c "
import sys, json
data = json.load(sys.stdin)
targets = data.get('data', {}).get('activeTargets', [])
up = [t for t in targets if t.get('health') == 'up']
print(len(up))
" 2>/dev/null || echo "0")

    TARGETS_TOTAL=$(echo "$PROM_TARGETS" | python3 -c "
import sys, json
data = json.load(sys.stdin)
targets = data.get('data', {}).get('activeTargets', [])
print(len(targets))
" 2>/dev/null || echo "0")

    CHECKS=$((CHECKS + 1))
    echo -n "  [$CHECKS] Prometheus scrape targets ... "

    if [ "$TARGETS_UP" -gt 0 ] && [ "$TARGETS_UP" = "$TARGETS_TOTAL" ]; then
        echo -e "${GREEN}PASS${NC} ($TARGETS_UP/$TARGETS_TOTAL targets UP)"
        PASSED=$((PASSED + 1))
    elif [ "$TARGETS_UP" -gt 0 ]; then
        echo -e "${YELLOW}PARTIAL${NC} ($TARGETS_UP/$TARGETS_TOTAL targets UP)"
        log_warn "Some Prometheus targets are down"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}FAIL${NC} (0 targets UP)"
        FAILED=$((FAILED + 1))
    fi
else
    CHECKS=$((CHECKS + 1))
    echo -e "  [$CHECKS] Prometheus targets ... ${YELLOW}SKIP${NC} (cannot reach Prometheus API)"
    WARNINGS=$((WARNINGS + 1))
fi

# ============================================
# 3. DATABASE CONNECTIVITY
# ============================================
log_section "3/5 — Database Connectivity"

DB_PAIRS=("alert-db:alert_db" "incident-db:incident_db" "notification-db:notification_db")

for pair in "${DB_PAIRS[@]}"; do
    DB_HOST="${pair%%:*}"
    DB_NAME="${pair##*:}"

    CHECKS=$((CHECKS + 1))
    echo -n "  [$CHECKS] $DB_HOST ($DB_NAME) ... "

    if docker compose exec -T "$DB_HOST" pg_isready -U hackathon -d "$DB_NAME" &>/dev/null 2>&1; then
        echo -e "${GREEN}PASS${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}FAIL${NC}"
        FAILED=$((FAILED + 1))
    fi
done

# ============================================
# 4. END-TO-END SMOKE TESTS (via API Gateway)
# ============================================
log_section "4/5 — E2E Smoke Tests (via API Gateway)"

API_KEY="${API_KEYS:-hackathon-api-key-2026}"
GATEWAY="http://localhost:8080"

# 4a. Login to get session token
log_info "Authenticating via API Gateway..."
LOGIN_RESP=$(curl -sf -X POST "$GATEWAY/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -d '{"username":"admin","password":"admin"}' \
    --max-time 5 2>/dev/null || echo "")

TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null || echo "")
AUTH_HEADER=""
if [ -n "$TOKEN" ]; then
    AUTH_HEADER="-H \"Authorization: Bearer $TOKEN\""
    log_ok "Got auth token"
else
    log_warn "Could not get auth token — some smoke tests may fail"
fi

# 4b. Create on-call schedule (direct to oncall-service)
check_response "Create on-call schedule" \
    "curl -sf -X POST 'http://localhost:8003/api/v1/schedules' \
        -H 'Content-Type: application/json' \
        -d '{\"team\":\"verify-team\",\"rotation_type\":\"weekly\",\"members\":[{\"name\":\"Verify User\",\"email\":\"verify@test.com\",\"role\":\"primary\"}]}' \
        --max-time 5" \
    "verify-team"

# 4c. Query current on-call
check_response "Query current on-call" \
    "curl -sf 'http://localhost:8003/api/v1/oncall/current?team=verify-team' --max-time 5" \
    "Verify User"

# 4d. Send alert via gateway
check_response "Send alert via API Gateway" \
    "curl -sf -X POST '$GATEWAY/api/v1/alerts' \
        -H 'Content-Type: application/json' \
        -H 'X-API-Key: $API_KEY' \
        -d '{\"service\":\"verify-svc\",\"severity\":\"high\",\"message\":\"Verify smoke test alert\",\"timestamp\":\"2026-02-10T00:00:00Z\"}' \
        --max-time 5" \
    "received\|created\|alert_id"

# 4e. List incidents
check_response "List incidents via gateway" \
    "curl -sf '$GATEWAY/api/v1/incidents' \
        -H 'X-API-Key: $API_KEY' \
        --max-time 5" \
    "incidents\|incident_id\|\[\]"

# 4f. Send notification (direct)
check_response "Send notification" \
    "curl -sf -X POST 'http://localhost:8004/api/v1/notify' \
        -H 'Content-Type: application/json' \
        -d '{\"type\":\"incident\",\"recipient\":\"verify@test.com\",\"message\":\"Verify smoke test notification\",\"severity\":\"high\",\"incident_id\":\"verify-001\"}' \
        --max-time 5" \
    "sent\|queued\|delivered\|notification"

# ============================================
# 5. METRICS ENDPOINTS
# ============================================
log_section "5/5 — Metrics Endpoints Validation"

METRIC_SERVICES=("alert-ingestion:8001" "incident-management:8002" "oncall-service:8003" "notification-service:8004" "api-gateway:8080")

for svc_port in "${METRIC_SERVICES[@]}"; do
    SVC="${svc_port%%:*}"
    PORT="${svc_port##*:}"

    CHECKS=$((CHECKS + 1))
    echo -n "  [$CHECKS] $SVC /metrics ... "

    METRICS=$(curl -sf "http://localhost:${PORT}/metrics" --max-time 5 2>/dev/null || echo "")
    if echo "$METRICS" | grep -q "HELP\|TYPE\|process_" 2>/dev/null; then
        echo -e "${GREEN}PASS${NC} (Prometheus format)"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}FAIL${NC} (no Prometheus metrics)"
        FAILED=$((FAILED + 1))
    fi
done

# ============================================
# VERIFICATION SUMMARY
# ============================================
echo ""
echo -e "${BOLD}${CYAN}══════════════════════════════════════════${NC}"
echo -e "${BOLD}${CYAN}       VERIFICATION SUMMARY${NC}"
echo -e "${BOLD}${CYAN}══════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BOLD}Total checks:${NC}  $CHECKS"
echo -e "  ${BOLD}Passed:${NC}        ${GREEN}$PASSED${NC}"
echo -e "  ${BOLD}Failed:${NC}        ${RED}$FAILED${NC}"
echo -e "  ${BOLD}Warnings:${NC}      ${YELLOW}$WARNINGS${NC}"
echo ""

if [ $FAILED -gt 0 ]; then
    log_error "Post-deployment verification: $FAILED failure(s) out of $CHECKS checks"
    exit 1
else
    log_ok "All post-deployment checks passed ($PASSED/$CHECKS)"
    exit 0
fi
