#!/bin/bash
# ============================================================
# LOCAL CD SCRIPT — Continuous Deployment (Local)
# ============================================================
# Usage:  ./deploy-local.sh [--clean] [--skip-build] [--skip-tests]
#
# Deploys the full Incident Platform locally via Docker Compose.
# Includes: build, deploy, health checks, smoke tests, rollback.
#
# Options:
#   --clean        Remove volumes (fresh DB) before deploy
#   --skip-build   Use existing images (no rebuild)
#   --skip-tests   Skip smoke tests after deploy
# ============================================================

set -e

# ── Colors ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

# ── Config ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

CLEAN=false
SKIP_BUILD=false
SKIP_TESTS=false

for arg in "$@"; do
    case $arg in
        --clean)      CLEAN=true ;;
        --skip-build) SKIP_BUILD=true ;;
        --skip-tests) SKIP_TESTS=true ;;
        --help|-h)
            echo "Usage: ./deploy-local.sh [--clean] [--skip-build] [--skip-tests]"
            echo ""
            echo "Options:"
            echo "  --clean        Remove volumes (fresh DB) before deploy"
            echo "  --skip-build   Use existing images (no rebuild)"
            echo "  --skip-tests   Skip smoke tests after deploy"
            exit 0
            ;;
    esac
done

DEPLOY_START=$(date +%s)
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

# ============================================================
echo ""
echo -e "${BOLD}${BLUE}"
echo "  ╔══════════════════════════════════════════╗"
echo "  ║     🚀 LOCAL DEPLOYMENT — CD SCRIPT      ║"
echo "  ║     Incident Platform v2.0               ║"
echo "  ╚══════════════════════════════════════════╝"
echo -e "${NC}"
echo -e "  📅 $(date)"
echo -e "  🌿 Branch: ${GIT_BRANCH} (${GIT_SHA})"
echo -e "  📁 Dir: $(pwd)"
echo ""

# ============================================================
# STEP 1: Check .env
# ============================================================
echo -e "${BOLD}${CYAN}── STEP 1: Check environment ──${NC}"

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}  ⚠️  No .env file found — creating default...${NC}"
    cat > .env << 'EOF'
POSTGRES_USER=hackathon
POSTGRES_PASSWORD=hackathon2026
POSTGRES_DB=incident_platform
API_KEYS=hackathon-api-key-2026
LOGIN_API_KEY=hackathon-api-key-2026
AUTH_USERS=admin:admin,operator:operator
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin
EOF
    echo -e "${GREEN}  ✅ .env created${NC}"
else
    echo -e "${GREEN}  ✅ .env exists${NC}"
fi

# Check Docker
if ! docker info &>/dev/null; then
    echo -e "${RED}  ❌ Docker is not running! Start Docker Desktop first.${NC}"
    exit 1
fi
echo -e "${GREEN}  ✅ Docker is running${NC}"
echo ""

# ============================================================
# STEP 2: Backup current images (for rollback)
# ============================================================
echo -e "${BOLD}${CYAN}── STEP 2: Backup current images ──${NC}"

SERVICES=("alert-ingestion" "incident-management" "oncall-service" "notification-service" "api-gateway" "web-ui")
IMAGE_PREFIX="incident-platform"

for svc in "${SERVICES[@]}"; do
    IMG="${IMAGE_PREFIX}-${svc}"
    if docker image inspect "${IMG}:latest" &>/dev/null; then
        docker tag "${IMG}:latest" "${IMG}:previous" 2>/dev/null || true
        echo -e "  📦 ${IMG}:latest → :previous"
    fi
done
echo ""

# ============================================================
# STEP 3: Stop existing stack
# ============================================================
echo -e "${BOLD}${CYAN}── STEP 3: Stop existing containers ──${NC}"

if [ "$CLEAN" = true ]; then
    echo -e "${YELLOW}  🧹 Clean mode: removing containers + volumes...${NC}"
    docker compose down -v --remove-orphans 2>/dev/null || true
else
    docker compose down --remove-orphans 2>/dev/null || true
fi
echo -e "${GREEN}  ✅ Previous stack stopped${NC}"
echo ""

# ============================================================
# STEP 4: Build & Deploy
# ============================================================
echo -e "${BOLD}${CYAN}── STEP 4: Build & Deploy ──${NC}"

BUILD_START=$(date +%s)

if [ "$SKIP_BUILD" = true ]; then
    echo -e "${YELLOW}  ⏩ Skipping build (--skip-build)${NC}"
    docker compose up -d 2>&1 | tail -5
else
    echo -e "${YELLOW}  🐳 Building and starting all services...${NC}"
    docker compose up -d --build 2>&1 | tail -10
fi

BUILD_END=$(date +%s)
BUILD_DURATION=$((BUILD_END - BUILD_START))
echo -e "${GREEN}  ✅ Docker Compose up (${BUILD_DURATION}s)${NC}"
echo ""

# ============================================================
# STEP 5: Wait for databases
# ============================================================
echo -e "${BOLD}${CYAN}── STEP 5: Wait for databases ──${NC}"

for db in alert-db incident-db notification-db; do
    echo -n "  ⏳ $db... "
    for i in $(seq 1 30); do
        if docker compose exec -T "$db" pg_isready -U hackathon &>/dev/null; then
            echo -e "${GREEN}ready${NC}"
            break
        fi
        if [ "$i" -eq 30 ]; then
            echo -e "${RED}TIMEOUT${NC}"
        fi
        sleep 2
    done
done
echo ""

# ============================================================
# STEP 6: Wait for services healthy
# ============================================================
echo -e "${BOLD}${CYAN}── STEP 6: Wait for services healthy ──${NC}"

MAX_WAIT=120
INTERVAL=5
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
    HEALTHY=0
    TOTAL=0

    for svc in "${SERVICES[@]}"; do
        PORT=""
        case $svc in
            alert-ingestion)       PORT=8001 ;;
            incident-management)   PORT=8002 ;;
            oncall-service)        PORT=8003 ;;
            notification-service)  PORT=8004 ;;
            api-gateway)           PORT=8080 ;;
            web-ui)                PORT=3001 ;;
        esac
        TOTAL=$((TOTAL + 1))

        if [ "$svc" = "web-ui" ]; then
            curl -sf "http://localhost:${PORT}/" &>/dev/null && HEALTHY=$((HEALTHY + 1))
        else
            curl -sf "http://localhost:${PORT}/health" &>/dev/null && HEALTHY=$((HEALTHY + 1))
        fi
    done

    echo -e "  ⏳ ${HEALTHY}/${TOTAL} services healthy (${ELAPSED}s elapsed)"

    if [ "$HEALTHY" -eq "$TOTAL" ]; then
        echo -e "${GREEN}  ✅ All services healthy!${NC}"
        break
    fi

    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

if [ "$HEALTHY" -lt "$TOTAL" ]; then
    echo -e "${RED}  ❌ Only ${HEALTHY}/${TOTAL} services healthy after ${MAX_WAIT}s${NC}"
    echo ""
    echo -e "${YELLOW}  Failing services:${NC}"
    for svc in "${SERVICES[@]}"; do
        PORT=""
        case $svc in
            alert-ingestion)       PORT=8001 ;;
            incident-management)   PORT=8002 ;;
            oncall-service)        PORT=8003 ;;
            notification-service)  PORT=8004 ;;
            api-gateway)           PORT=8080 ;;
            web-ui)                PORT=3001 ;;
        esac
        if [ "$svc" = "web-ui" ]; then
            curl -sf "http://localhost:${PORT}/" &>/dev/null || echo -e "    ${RED}✗ $svc (:${PORT})${NC}"
        else
            curl -sf "http://localhost:${PORT}/health" &>/dev/null || echo -e "    ${RED}✗ $svc (:${PORT})${NC}"
        fi
    done

    # ── ROLLBACK ──
    echo ""
    echo -e "${YELLOW}  🔄 ROLLING BACK to previous version...${NC}"
    docker compose down --remove-orphans 2>/dev/null || true

    HAS_PREVIOUS=false
    for svc in "${SERVICES[@]}"; do
        IMG="${IMAGE_PREFIX}-${svc}"
        if docker image inspect "${IMG}:previous" &>/dev/null; then
            docker tag "${IMG}:previous" "${IMG}:latest" 2>/dev/null || true
            HAS_PREVIOUS=true
        fi
    done

    if [ "$HAS_PREVIOUS" = true ]; then
        docker compose up -d 2>&1
        echo -e "${YELLOW}  ⚠️  Rolled back to previous version${NC}"
    else
        echo -e "${YELLOW}  ⚠️  No previous images — first deploy failed${NC}"
    fi
    exit 1
fi
echo ""

# ============================================================
# STEP 7: Smoke Tests
# ============================================================
if [ "$SKIP_TESTS" = false ]; then
    echo -e "${BOLD}${CYAN}── STEP 7: Smoke Tests ──${NC}"
    echo ""

    PASS=0
    FAIL=0

    smoke_test() {
        local name="$1"
        local cmd="$2"
        local expect="$3"

        echo -n "  $name... "
        RESULT=$(eval "$cmd" 2>/dev/null || echo "CURL_FAILED")

        if echo "$RESULT" | grep -q "$expect"; then
            echo -e "${GREEN}PASS${NC}"
            PASS=$((PASS + 1))
        else
            echo -e "${RED}FAIL${NC}"
            echo -e "    ${RED}Expected: $expect${NC}"
            echo -e "    ${RED}Got: $(echo "$RESULT" | head -1 | cut -c1-100)${NC}"
            FAIL=$((FAIL + 1))
        fi
    }

    # Login
    smoke_test "Login (admin)" \
        "curl -s -X POST http://localhost:8080/api/v1/auth/login -H 'Content-Type: application/json' -d '{\"username\":\"admin\",\"password\":\"admin\"}'" \
        "api_key"

    # Create alert → incident
    smoke_test "Alert → Incident" \
        "curl -s -X POST http://localhost:8080/api/v1/alerts -H 'Content-Type: application/json' -H 'X-API-Key: hackathon-api-key-2026' -d '{\"source\":\"deploy-test\",\"severity\":\"low\",\"message\":\"Deploy smoke test\",\"service\":\"cd-script\"}'" \
        "incident_id"

    # List incidents
    smoke_test "List Incidents" \
        "curl -s http://localhost:8080/api/v1/incidents -H 'X-API-Key: hackathon-api-key-2026'" \
        "incidents"

    # Create schedule
    smoke_test "Create OnCall Schedule" \
        "curl -s -X POST http://localhost:8003/api/v1/schedules -H 'Content-Type: application/json' -d '{\"team\":\"cd-test\",\"rotation_type\":\"weekly\",\"members\":[{\"name\":\"Tester\",\"email\":\"test@test.com\",\"role\":\"primary\"}]}'" \
        "cd-test"

    # Send notification
    smoke_test "Send Notification" \
        "curl -s -X POST http://localhost:8080/api/v1/notify -H 'Content-Type: application/json' -H 'X-API-Key: hackathon-api-key-2026' -d '{\"incident_id\":\"00000000-0000-0000-0000-000000000000\",\"channel\":\"mock\",\"message\":\"CD test\",\"recipient\":\"cd@test.com\"}'" \
        "sent"

    # Prometheus
    smoke_test "Prometheus" \
        "curl -s http://localhost:9090/-/healthy" \
        "Healthy"

    # Grafana
    smoke_test "Grafana" \
        "curl -s http://localhost:3000/api/health" \
        "ok"

    echo ""
    echo -e "  Tests: ${GREEN}${PASS} passed${NC}, ${RED}${FAIL} failed${NC}"
    echo ""
else
    echo -e "${YELLOW}  ⏩ Skipping smoke tests (--skip-tests)${NC}"
    echo ""
fi

# ============================================================
# SUMMARY
# ============================================================
DEPLOY_END=$(date +%s)
TOTAL_DURATION=$((DEPLOY_END - DEPLOY_START))

echo -e "${BOLD}${PURPLE}══════════════════════════════════════════════${NC}"
echo -e "${BOLD}${GREEN}  🚀 DEPLOYMENT SUCCESSFUL${NC}"
echo -e "${BOLD}${PURPLE}══════════════════════════════════════════════${NC}"
echo ""
echo -e "  📅 Date:     $(date)"
echo -e "  🔖 Commit:   ${GIT_SHA}"
echo -e "  🌿 Branch:   ${GIT_BRANCH}"
echo -e "  ⏱️  Duration: ${TOTAL_DURATION}s"
echo ""
echo -e "${BOLD}  📦 Services:${NC}"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || docker compose ps
echo ""
echo -e "${BOLD}  🔗 Access URLs:${NC}"
echo -e "     Web UI:      ${CYAN}http://localhost:3001${NC}"
echo -e "     API Gateway: ${CYAN}http://localhost:8080${NC}"
echo -e "     Grafana:     ${CYAN}http://localhost:3000${NC}  (admin/admin)"
echo -e "     Prometheus:  ${CYAN}http://localhost:9090${NC}"
echo ""
echo -e "${PURPLE}══════════════════════════════════════════════${NC}"
