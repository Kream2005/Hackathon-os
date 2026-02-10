#!/bin/bash
# ============================================
# STAGE 6: Automated Deployment with Rollback
# ============================================
# Deploys the full incident-platform stack via
# Docker Compose. Includes:
#   - Prerequisites validation
#   - Port conflict detection
#   - Immutable image tagging (SHA + :previous)
#   - Health-check gate with retry
#   - Automatic rollback on failure
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
MAX_RETRIES=12
RETRY_INTERVAL=5
DEPLOY_TIMEOUT=$((MAX_RETRIES * RETRY_INTERVAL))

# All application services (excluding infra: DBs, Prometheus, Grafana)
SERVICES=("alert-ingestion" "incident-management" "oncall-service" "notification-service" "api-gateway" "web-ui")

# Service → host port mapping (matches docker-compose.yml)
declare -A SERVICE_PORTS=(
    [alert-ingestion]=8001
    [incident-management]=8002
    [oncall-service]=8003
    [notification-service]=8004
    [api-gateway]=8080
    [web-ui]=3001
)

# Service → health endpoint (web-ui is nginx, no /health)
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
log_step()  { echo ""; echo -e "${BOLD}${YELLOW}── $* ──${NC}"; }

# ── Trap: clean up on unexpected exit ──
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        log_error "Deploy script exited with code $exit_code"
    fi
}
trap cleanup EXIT

# ============================================
# STEP 1: Prerequisites Check
# ============================================
log_step "Step 1/6: Prerequisites Validation"

# Docker daemon
if ! docker info &>/dev/null; then
    log_error "Docker daemon is not running. Start Docker Desktop and retry."
    exit 1
fi
log_ok "Docker daemon is running"

# Docker Compose
if ! docker compose version &>/dev/null; then
    log_error "docker compose not found. Install Docker Compose V2."
    exit 1
fi
COMPOSE_VER=$(docker compose version --short 2>/dev/null || echo "unknown")
log_ok "Docker Compose $COMPOSE_VER"

# docker-compose.yml
if [ ! -f "$PROJECT_DIR/docker-compose.yml" ]; then
    log_error "docker-compose.yml not found in $PROJECT_DIR"
    exit 1
fi
log_ok "docker-compose.yml found"

# .env file
if [ ! -f "$PROJECT_DIR/.env" ]; then
    log_warn ".env file not found — Docker Compose may use defaults"
else
    log_ok ".env file loaded"
fi

# ============================================
# STEP 2: Port Conflict Detection
# ============================================
log_step "Step 2/6: Port Conflict Detection"

PORTS_IN_USE=()
ALL_PORTS=(8001 8002 8003 8004 8080 3001 9090 3000 5432)

for port in "${ALL_PORTS[@]}"; do
    # Check if port is in use by a non-Docker process
    if command -v ss &>/dev/null; then
        if ss -tlnp 2>/dev/null | grep -q ":${port} " && ! docker compose ps 2>/dev/null | grep -q "${port}"; then
            PORTS_IN_USE+=("$port")
        fi
    elif command -v netstat &>/dev/null; then
        if netstat -tln 2>/dev/null | grep -q ":${port} " && ! docker compose ps 2>/dev/null | grep -q "${port}"; then
            PORTS_IN_USE+=("$port")
        fi
    fi
done

if [ ${#PORTS_IN_USE[@]} -gt 0 ]; then
    log_warn "Ports potentially in use by other processes: ${PORTS_IN_USE[*]}"
    log_warn "Deployment may still succeed if these are from a previous docker compose"
else
    log_ok "No port conflicts detected"
fi

# ============================================
# STEP 3: Backup Current Images
# ============================================
log_step "Step 3/6: Backup Current Images"

GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
BACKUP_COUNT=0

for svc in "${SERVICES[@]}"; do
    IMG="${IMAGE_PREFIX}-${svc}"
    if docker image inspect "${IMG}:latest" &>/dev/null; then
        # Tag as :previous for rollback
        docker tag "${IMG}:latest" "${IMG}:previous" 2>/dev/null || true
        # Tag with commit SHA for traceability
        docker tag "${IMG}:latest" "${IMG}:${GIT_SHA}" 2>/dev/null || true
        BACKUP_COUNT=$((BACKUP_COUNT + 1))
        log_ok "Backed up ${IMG}:latest → :previous + :${GIT_SHA}"
    else
        log_info "${IMG}:latest not found — first deploy for this service"
    fi
done

log_info "Backed up $BACKUP_COUNT/${#SERVICES[@]} images"

# ============================================
# STEP 4: Deploy Stack
# ============================================
log_step "Step 4/6: Deploy via Docker Compose"

log_info "Tearing down existing stack..."
docker compose down --remove-orphans 2>/dev/null || true

log_info "Building and starting all services..."
if ! docker compose up -d --build 2>&1; then
    log_error "docker compose up failed"

    # Attempt rollback if we have previous images
    if [ $BACKUP_COUNT -gt 0 ] && [ -f "$SCRIPT_DIR/rollback.sh" ]; then
        log_warn "Delegating to rollback.sh..."
        bash "$SCRIPT_DIR/rollback.sh" "compose-up-failed" || true
    fi
    exit 1
fi

log_ok "All containers started"

# Show container status
echo ""
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || docker compose ps
echo ""

# ============================================
# STEP 5: Health Check Gate (with retry)
# ============================================
log_step "Step 5/6: Health Check Gate (timeout: ${DEPLOY_TIMEOUT}s)"

# 5a. Wait for databases to be ready first
log_info "Waiting for databases..."
DB_SERVICES=("alert-db" "incident-db" "notification-db")
for db in "${DB_SERVICES[@]}"; do
    for i in $(seq 1 $MAX_RETRIES); do
        if docker compose exec -T "$db" pg_isready -U hackathon &>/dev/null 2>&1; then
            log_ok "$db is ready"
            break
        fi
        if [ $i -eq $MAX_RETRIES ]; then
            log_warn "$db did not become ready in time"
        fi
        sleep 2
    done
done

# 5b. Check application services
log_info "Checking application services..."
HEALTHY_SERVICES=()
UNHEALTHY_SERVICES=()

for attempt in $(seq 1 $MAX_RETRIES); do
    HEALTHY_SERVICES=()
    UNHEALTHY_SERVICES=()

    for svc in "${SERVICES[@]}"; do
        PORT="${SERVICE_PORTS[$svc]}"
        ENDPOINT="${HEALTH_ENDPOINTS[$svc]}"
        URL="http://localhost:${PORT}${ENDPOINT}"

        HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" "$URL" --max-time 3 2>/dev/null || echo "000")

        if [ "$HTTP_CODE" = "200" ]; then
            HEALTHY_SERVICES+=("$svc")
        else
            UNHEALTHY_SERVICES+=("$svc")
        fi
    done

    echo -e "  Attempt ${attempt}/${MAX_RETRIES}: ${GREEN}${#HEALTHY_SERVICES[@]}${NC}/${#SERVICES[@]} healthy"

    if [ ${#HEALTHY_SERVICES[@]} -eq ${#SERVICES[@]} ]; then
        break
    fi

    if [ $attempt -lt $MAX_RETRIES ]; then
        sleep $RETRY_INTERVAL
    fi
done

# 5c. Check monitoring stack
PROM_OK=false
GRAFANA_OK=false

if curl -sf "http://localhost:9090/-/healthy" --max-time 3 &>/dev/null; then
    PROM_OK=true
    log_ok "Prometheus is healthy"
else
    log_warn "Prometheus is not responding"
fi

if curl -sf "http://localhost:3000/api/health" --max-time 3 &>/dev/null; then
    GRAFANA_OK=true
    log_ok "Grafana is healthy"
else
    log_warn "Grafana is not responding"
fi

# ============================================
# STEP 5b: Rollback Decision
# ============================================
if [ ${#UNHEALTHY_SERVICES[@]} -gt 0 ]; then
    log_error "${#UNHEALTHY_SERVICES[@]} service(s) failed health check: ${UNHEALTHY_SERVICES[*]}"
    echo ""

    # Show logs for failing services
    for svc in "${UNHEALTHY_SERVICES[@]}"; do
        log_error "Last 8 log lines for $svc:"
        docker compose logs --tail=8 "$svc" 2>/dev/null | sed 's/^/    /' || true
        echo ""
    done

    # Attempt rollback
    if [ $BACKUP_COUNT -gt 0 ] && [ -f "$SCRIPT_DIR/rollback.sh" ]; then
        log_warn "Initiating automatic rollback..."
        bash "$SCRIPT_DIR/rollback.sh" "health-check-failed: ${UNHEALTHY_SERVICES[*]}" || true
    else
        log_warn "No rollback possible — no previous images or rollback.sh not found"
    fi
    exit 1
fi

# ============================================
# STEP 6: Deployment Summary
# ============================================
log_step "Step 6/6: Deployment Summary"

echo ""
echo -e "  ${BOLD}Services:${NC}     ${GREEN}${#HEALTHY_SERVICES[@]}/${#SERVICES[@]} healthy${NC}"
echo -e "  ${BOLD}Prometheus:${NC}   $([ "$PROM_OK" = true ] && echo -e "${GREEN}UP${NC}" || echo -e "${YELLOW}DOWN${NC}")"
echo -e "  ${BOLD}Grafana:${NC}      $([ "$GRAFANA_OK" = true ] && echo -e "${GREEN}UP${NC}" || echo -e "${YELLOW}DOWN${NC}")"
echo -e "  ${BOLD}Git SHA:${NC}      $GIT_SHA"
echo -e "  ${BOLD}Images:${NC}       Tagged :latest + :previous + :${GIT_SHA}"
echo ""
echo -e "  ${BOLD}Endpoints:${NC}"
echo -e "    Web UI:      http://localhost:3001"
echo -e "    API Gateway: http://localhost:8080"
echo -e "    Grafana:     http://localhost:3000  (admin/admin)"
echo -e "    Prometheus:  http://localhost:9090"
echo ""

log_ok "Deployment successful — all ${#SERVICES[@]} services are healthy"
exit 0
