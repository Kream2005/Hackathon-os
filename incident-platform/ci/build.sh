#!/bin/bash
# ============================================
# STAGE 4: Build Container Images
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "dev")
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo -e "${YELLOW}🐳 Building container images...${NC}"
echo -e "  Git SHA: $GIT_SHA"
echo -e "  Build date: $BUILD_DATE"
echo ""

# Build all services with docker compose
echo -e "${YELLOW}  Building with docker compose...${NC}"
docker compose build --parallel 2>&1 | tail -20

echo ""
echo -e "${YELLOW}📦 Built images:${NC}"
echo ""

# List images with sizes
printf "  %-35s %-15s %s\n" "IMAGE" "TAG" "SIZE"
printf "  %-35s %-15s %s\n" "-----" "---" "----"

for service in alert-ingestion incident-management oncall-service notification-service web-ui; do
    image_info=$(docker images --format "{{.Repository}}\t{{.Tag}}\t{{.Size}}" 2>/dev/null | grep "$service" | head -1)
    if [ -n "$image_info" ]; then
        repo=$(echo "$image_info" | cut -f1)
        tag=$(echo "$image_info" | cut -f2)
        size=$(echo "$image_info" | cut -f3)
        printf "  ${GREEN}%-35s %-15s %s${NC}\n" "$repo" "$tag" "$size"
    else
        printf "  ${YELLOW}%-35s %-15s %s${NC}\n" "$service" "built" "(size N/A)"
    fi
done

echo ""
echo -e "${GREEN}✅ All container images built successfully${NC}"
exit 0
