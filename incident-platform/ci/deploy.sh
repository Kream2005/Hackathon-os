#!/bin/bash
# ============================================
# STAGE 6: Deploy with Automated Rollback
# ============================================
# - Backs up current images before deploy
# - Deploys new version
# - Health checks with retry
# - Automatic rollback on failure
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SERVICES=("alert-ingestion" "incident-management" "oncall-service" "notification-service" "web-ui")
IMAGE_PREFIX="incident-platform"
ROLLBACK_NEEDED=false

echo -e "${YELLOW}🚀 Deploying services with rollback support...${NC}"
echo ""

# ── Step 1: Backup current images ──
echo -e "${YELLOW}📦 Step 1: Backing up current images...${NC}"
for svc in "${SERVICES[@]}"; do
    IMG="${IMAGE_PREFIX}-${svc}"
    if docker image inspect "${IMG}:latest" &>/dev/null; then
        docker tag "${IMG}:latest" "${IMG}:previous" 2>/dev/null || true
        echo -e "  ✅ Tagged ${IMG}:latest → ${IMG}:previous"
    else
        echo -e "  ℹ️  ${IMG}:latest not found — first deploy"
    fi
done
echo ""

# ── Step 2: Stop existing containers ──
echo -e "${YELLOW}🛑 Step 2: Stopping existing containers...${NC}"
docker compose down --remove-orphans 2>/dev/null || true
echo ""

# ── Step 3: Deploy new version ──
echo -e "${YELLOW}🚀 Step 3: Starting services...${NC}"
docker compose up -d 2>&1
echo ""

# ── Step 4: Health check with retry ──
echo -e "${YELLOW}🏥 Step 4: Health checks (max 40s)...${NC}"
MAX_RETRIES=8
RETRY_INTERVAL=5
HEALTHY_COUNT=0

for attempt in $(seq 1 $MAX_RETRIES); do
    echo -n "  Attempt $attempt/$MAX_RETRIES ... "
    sleep $RETRY_INTERVAL

    HEALTHY_COUNT=0
    for svc in "${SERVICES[@]}"; do
        PORT=""
        case $svc in
            alert-ingestion)       PORT=8001 ;;
            incident-management)   PORT=8002 ;;
            oncall-service)        PORT=8003 ;;
            notification-service)  PORT=8004 ;;
            web-ui)                PORT=8080 ;;
        esac

        if curl -sf "http://localhost:${PORT}/health" &>/dev/null; then
            HEALTHY_COUNT=$((HEALTHY_COUNT + 1))
        fi
    done

    echo -e "${HEALTHY_COUNT}/${#SERVICES[@]} healthy"

    if [ "$HEALTHY_COUNT" -eq "${#SERVICES[@]}" ]; then
        break
    fi
done

echo ""

# ── Step 5: Check result or rollback ──
if [ "$HEALTHY_COUNT" -lt "${#SERVICES[@]}" ]; then
    echo -e "${RED}❌ Only ${HEALTHY_COUNT}/${#SERVICES[@]} services healthy after ${MAX_RETRIES} retries${NC}"
    echo ""

    # Show failing services
    echo -e "${YELLOW}Failing services:${NC}"
    for svc in "${SERVICES[@]}"; do
        PORT=""
        case $svc in
            alert-ingestion)       PORT=8001 ;;
            incident-management)   PORT=8002 ;;
            oncall-service)        PORT=8003 ;;
            notification-service)  PORT=8004 ;;
            web-ui)                PORT=8080 ;;
        esac
        if ! curl -sf "http://localhost:${PORT}/health" &>/dev/null; then
            echo -e "  ${RED}✗ $svc (port $PORT)${NC}"
            echo -e "    Last logs:"
            docker compose logs --tail=5 "$svc" 2>/dev/null | sed 's/^/    /' || true
        fi
    done

    # ── Rollback ──
    echo ""
    echo -e "${YELLOW}🔄 INITIATING ROLLBACK...${NC}"

    HAS_PREVIOUS=false
    for svc in "${SERVICES[@]}"; do
        IMG="${IMAGE_PREFIX}-${svc}"
        if docker image inspect "${IMG}:previous" &>/dev/null; then
            docker tag "${IMG}:previous" "${IMG}:latest" 2>/dev/null || true
            echo -e "  ↩️  Restored ${IMG}:previous → ${IMG}:latest"
            HAS_PREVIOUS=true
        fi
    done

    if [ "$HAS_PREVIOUS" = true ]; then
        echo ""
        echo -e "${YELLOW}  Redeploying previous version...${NC}"
        docker compose down --remove-orphans 2>/dev/null || true
        docker compose up -d 2>&1
        sleep 15

        # Re-check
        ROLLBACK_HEALTHY=0
        for svc in "${SERVICES[@]}"; do
            PORT=""
            case $svc in
                alert-ingestion)       PORT=8001 ;;
                incident-management)   PORT=8002 ;;
                oncall-service)        PORT=8003 ;;
                notification-service)  PORT=8004 ;;
                web-ui)                PORT=8080 ;;
            esac
            if curl -sf "http://localhost:${PORT}/health" &>/dev/null; then
                ROLLBACK_HEALTHY=$((ROLLBACK_HEALTHY + 1))
            fi
        done

        echo ""
        if [ "$ROLLBACK_HEALTHY" -ge 3 ]; then
            echo -e "${YELLOW}⚠️  Rollback successful — previous version restored (${ROLLBACK_HEALTHY}/${#SERVICES[@]} healthy)${NC}"
        else
            echo -e "${RED}❌ Rollback also failed — manual intervention needed${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  No previous images found — cannot rollback (first deploy)${NC}"
    fi

    exit 1
fi

# ── Success ──
echo -e "${YELLOW}📋 Container Status:${NC}"
echo ""
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || docker compose ps
echo ""
echo -e "${GREEN}✅ Deployment successful — ${HEALTHY_COUNT}/${#SERVICES[@]} services healthy${NC}"
exit 0
