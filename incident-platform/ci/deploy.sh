#!/bin/bash
# ============================================
# STAGE 5: Deploy (docker compose up)
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🚀 Deploying services...${NC}"

# Clean up existing containers
echo -e "  Stopping existing containers..."
docker compose down --remove-orphans 2>/dev/null || true

# Start fresh
echo -e "  Starting services with docker compose..."
docker compose up -d 2>&1

echo ""
echo -e "${YELLOW}⏳ Waiting for services to initialize (25s)...${NC}"

# Progress bar
for i in $(seq 1 25); do
    echo -n "."
    sleep 1
done
echo ""

echo ""
echo -e "${YELLOW}📋 Container Status:${NC}"
echo ""
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || docker compose ps

echo ""

# Check if all containers are running
RUNNING=$(docker compose ps --format "{{.State}}" 2>/dev/null | grep -c "running" || echo "0")
TOTAL=$(docker compose ps --format "{{.Name}}" 2>/dev/null | wc -l || echo "0")

echo -e "  Containers running: $RUNNING/$TOTAL"

if [ "$RUNNING" -lt 3 ]; then
    echo -e "${RED}❌ Less than 3 containers running — deployment may have issues${NC}"
    echo ""
    echo -e "${YELLOW}Container logs (last 10 lines each):${NC}"
    for service in alert-ingestion incident-management oncall-service notification-service web-ui; do
        echo -e "\n  --- $service ---"
        docker compose logs --tail=10 "$service" 2>/dev/null || true
    done
    exit 1
fi

echo -e "${GREEN}✅ Deployment successful${NC}"
exit 0
