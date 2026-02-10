#!/bin/bash
# ============================================
# ROLLBACK: Restore Previous Deployment
# ============================================
# Restores :previous tagged images and redeploys.
# Called automatically by deploy.sh on failure,
# or manually: ./ci/rollback.sh [reason]
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

IMAGE_PREFIX="incident-platform"
REASON="${1:-manual-rollback}"

SERVICES=("alert-ingestion" "incident-management" "oncall-service" "notification-service" "api-gateway" "web-ui")

declare -A SERVICE_PORTS=(
    [alert-ingestion]=8001
    [incident-management]=8002
    [oncall-service]=8003
    [notification-service]=8004
    [api-gateway]=8080
    [web-ui]=3001
)

declare -A HEALTH_ENDPOINTS=(
    [alert-ingestion]="/health"
    [incident-management]="/health"
    [oncall-service]="/health"
    [notification-service]="/health"
    [api-gateway]="/health"
    [web-ui]="/"
)

# ── Logging helpers ──
log_info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ============================================
echo ""
echo -e "${BOLD}${RED}══════════════════════════════════════════${NC}"
echo -e "${BOLD}${RED}         ROLLBACK INITIATED${NC}"
echo -e "${BOLD}${RED}══════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BOLD}Reason:${NC} $REASON"
echo -e "  ${BOLD}Time:${NC}   $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# ============================================
# STEP 1: Check for :previous images
# ============================================
log_info "Checking for :previous tagged images..."

HAS_PREVIOUS=false
RESTORED=0

for svc in "${SERVICES[@]}"; do
    IMG="${IMAGE_PREFIX}-${svc}"
    if docker image inspect "${IMG}:previous" &>/dev/null; then
        docker tag "${IMG}:previous" "${IMG}:latest" 2>/dev/null || true
        log_ok "Restored ${IMG}:previous → :latest"
        RESTORED=$((RESTORED + 1))
        HAS_PREVIOUS=true
    else
        log_warn "${IMG}:previous not found — cannot rollback this service"
    fi
done

if [ "$HAS_PREVIOUS" = false ]; then
    log_error "No :previous images found. Cannot rollback."
    log_error "This might be the first deployment — no rollback target exists."
    exit 1
fi

echo ""
log_info "Restored $RESTORED/${#SERVICES[@]} images"

# ============================================
# STEP 2: Redeploy with previous images
# ============================================
echo ""
log_info "Tearing down current stack..."
docker compose down --remove-orphans 2>/dev/null || true

log_info "Redeploying with previous images (no build)..."
if ! docker compose up -d --no-build 2>&1; then
    log_error "Rollback deployment failed — manual intervention required"
    exit 1
fi

# ============================================
# STEP 3: Wait for services to come up
# ============================================
echo ""
log_info "Waiting for services to stabilize (30s max)..."
sleep 10

MAX_ATTEMPTS=4
RETRY_WAIT=5

for attempt in $(seq 1 $MAX_ATTEMPTS); do
    HEALTHY=0
    TOTAL=${#SERVICES[@]}

    for svc in "${SERVICES[@]}"; do
        PORT="${SERVICE_PORTS[$svc]}"
        ENDPOINT="${HEALTH_ENDPOINTS[$svc]}"
        URL="http://localhost:${PORT}${ENDPOINT}"

        if curl -sf -o /dev/null "$URL" --max-time 3 2>/dev/null; then
            HEALTHY=$((HEALTHY + 1))
        fi
    done

    echo -e "  Attempt ${attempt}/${MAX_ATTEMPTS}: ${GREEN}${HEALTHY}${NC}/${TOTAL} healthy"

    if [ $HEALTHY -eq $TOTAL ]; then
        break
    fi

    if [ $attempt -lt $MAX_ATTEMPTS ]; then
        sleep $RETRY_WAIT
    fi
done

# ============================================
# STEP 4: Rollback Result
# ============================================
echo ""
echo -e "${BOLD}${CYAN}══════════════════════════════════════════${NC}"
echo -e "${BOLD}${CYAN}         ROLLBACK RESULT${NC}"
echo -e "${BOLD}${CYAN}══════════════════════════════════════════${NC}"
echo ""

if [ $HEALTHY -ge $((TOTAL - 1)) ]; then
    echo -e "  ${BOLD}Status:${NC}   ${GREEN}ROLLBACK SUCCESSFUL${NC}"
    echo -e "  ${BOLD}Healthy:${NC}  ${HEALTHY}/${TOTAL} services"
    echo -e "  ${BOLD}Reason:${NC}   $REASON"
    echo ""

    # Show container status
    docker compose ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null || docker compose ps
    echo ""

    log_ok "Previous version restored successfully"
    exit 0
else
    echo -e "  ${BOLD}Status:${NC}   ${RED}ROLLBACK FAILED${NC}"
    echo -e "  ${BOLD}Healthy:${NC}  ${HEALTHY}/${TOTAL} services"
    echo ""

    log_error "Rollback failed — only $HEALTHY/$TOTAL services healthy"
    log_error "Manual intervention required. Check logs with: docker compose logs"
    exit 1
fi
