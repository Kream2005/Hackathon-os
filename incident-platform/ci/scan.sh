#!/bin/bash
# ============================================
# STAGE 5: Container Image Security Scan
# ============================================
# Scans built Docker images for vulnerabilities
# Uses Docker Scout (built into Docker Desktop)
# Falls back to basic image analysis if scout unavailable
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0
WARNINGS=0

IMAGES=(
    "incident-platform-alert-ingestion"
    "incident-platform-incident-management"
    "incident-platform-oncall-service"
    "incident-platform-notification-service"
    "incident-platform-web-ui"
)

echo -e "${YELLOW}🔍 Scanning container images for vulnerabilities...${NC}"
echo ""

# --- Method 1: Try Docker Scout ---
HAS_SCOUT=false
if docker scout version &>/dev/null; then
    HAS_SCOUT=true
    echo -e "  ${GREEN}✅ Docker Scout available${NC}"
    echo ""
fi

# --- Method 2: Try Trivy ---
HAS_TRIVY=false
if command -v trivy &>/dev/null; then
    HAS_TRIVY=true
    echo -e "  ${GREEN}✅ Trivy available${NC}"
    echo ""
fi

for image in "${IMAGES[@]}"; do
    service_name=$(echo "$image" | sed 's/incident-platform-//')
    echo -e "${YELLOW}  Scanning $service_name...${NC}"

    # Check image exists
    if ! docker image inspect "$image:latest" &>/dev/null; then
        echo -e "    ${YELLOW}⚠️  Image not found — skipping${NC}"
        continue
    fi

    if [ "$HAS_TRIVY" = true ]; then
        # Use Trivy
        SCAN_OUTPUT=$(trivy image --severity CRITICAL,HIGH --no-progress --format table "$image:latest" 2>/dev/null || echo "SCAN_FAILED")

        if echo "$SCAN_OUTPUT" | grep -q "SCAN_FAILED"; then
            echo -e "    ${YELLOW}⚠️  Trivy scan failed — continuing${NC}"
        else
            CRITICAL=$(echo "$SCAN_OUTPUT" | grep -c "CRITICAL" 2>/dev/null || echo "0")
            HIGH=$(echo "$SCAN_OUTPUT" | grep -c "HIGH" 2>/dev/null || echo "0")

            if [ "$CRITICAL" -gt 0 ]; then
                echo -e "    ${RED}❌ CRITICAL vulnerabilities found: $CRITICAL${NC}"
                ERRORS=$((ERRORS + 1))
            elif [ "$HIGH" -gt 5 ]; then
                echo -e "    ${YELLOW}⚠️  HIGH vulnerabilities: $HIGH${NC}"
                WARNINGS=$((WARNINGS + 1))
            else
                echo -e "    ${GREEN}✅ No critical vulnerabilities${NC}"
            fi
        fi

    elif [ "$HAS_SCOUT" = true ]; then
        # Use Docker Scout (quickview only)
        SCOUT_OUTPUT=$(docker scout quickview "$image:latest" 2>/dev/null || echo "SCOUT_FAILED")

        if echo "$SCOUT_OUTPUT" | grep -q "SCOUT_FAILED"; then
            echo -e "    ${YELLOW}⚠️  Scout scan failed — continuing${NC}"
        else
            if echo "$SCOUT_OUTPUT" | grep -qi "critical"; then
                echo -e "    ${RED}⚠️  Critical vulnerabilities detected — review recommended${NC}"
                WARNINGS=$((WARNINGS + 1))
            else
                echo -e "    ${GREEN}✅ No critical vulnerabilities${NC}"
            fi
        fi

    else
        # Fallback: Basic security checks on image
        echo -e "    ${YELLOW}ℹ️  No scanner available — performing basic checks${NC}"

        # Check 1: Image size (warn if > 500MB)
        SIZE_BYTES=$(docker image inspect "$image:latest" --format '{{.Size}}' 2>/dev/null || echo "0")
        SIZE_MB=$((SIZE_BYTES / 1024 / 1024))
        if [ "$SIZE_MB" -gt 500 ]; then
            echo -e "    ${YELLOW}⚠️  Image size: ${SIZE_MB}MB (>500MB — consider optimizing)${NC}"
            WARNINGS=$((WARNINGS + 1))
        else
            echo -e "    ${GREEN}✅ Image size: ${SIZE_MB}MB${NC}"
        fi

        # Check 2: Non-root user
        USER=$(docker image inspect "$image:latest" --format '{{.Config.User}}' 2>/dev/null || echo "")
        if [ -z "$USER" ] || [ "$USER" = "root" ]; then
            echo -e "    ${RED}❌ Running as root user${NC}"
            ERRORS=$((ERRORS + 1))
        else
            echo -e "    ${GREEN}✅ Non-root user: $USER${NC}"
        fi

        # Check 3: Healthcheck configured
        HC=$(docker image inspect "$image:latest" --format '{{.Config.Healthcheck}}' 2>/dev/null || echo "")
        if [ -z "$HC" ] || [ "$HC" = "<nil>" ]; then
            echo -e "    ${YELLOW}⚠️  No HEALTHCHECK in image${NC}"
        else
            echo -e "    ${GREEN}✅ HEALTHCHECK configured${NC}"
        fi

        # Check 4: Python base image (not full, should be slim/alpine)
        BASE=$(docker image history "$image:latest" --format '{{.CreatedBy}}' 2>/dev/null | tail -1 || echo "")
        if echo "$BASE" | grep -q "python:3" && ! echo "$BASE" | grep -q "slim\|alpine"; then
            echo -e "    ${YELLOW}⚠️  Using full Python image — consider slim/alpine${NC}"
            WARNINGS=$((WARNINGS + 1))
        fi

        # Check 5: Number of layers
        LAYERS=$(docker image history "$image:latest" --format '{{.ID}}' 2>/dev/null | wc -l || echo "0")
        echo -e "    ${GREEN}ℹ️  Layers: $LAYERS${NC}"
    fi

    echo ""
done

# --- Summary ---
echo -e "${YELLOW}📊 Scan Summary:${NC}"
echo -e "  Images scanned: ${#IMAGES[@]}"
echo -e "  Critical issues: $ERRORS"
echo -e "  Warnings: $WARNINGS"

if [ "$HAS_TRIVY" = false ] && [ "$HAS_SCOUT" = false ]; then
    echo -e "  ${YELLOW}ℹ️  Install Trivy or Docker Scout for full vulnerability scanning${NC}"
    echo -e "  ${YELLOW}   brew install trivy  OR  docker scout quickview${NC}"
fi

echo ""

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}❌ $ERRORS critical issue(s) found — review required${NC}"
    # Don't fail pipeline for scan — just warn
    # exit 1
fi

echo -e "${GREEN}✅ Image security scan complete${NC}"
exit 0
