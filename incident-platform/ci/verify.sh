#!/bin/bash
# ============================================
# STAGE 6: Post-Deployment Verification
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0
CHECKS=0

# ============================================
# Health Checks
# ============================================
echo -e "${YELLOW}🏥 Health Checks${NC}"
echo ""

check_health() {
    local name=$1
    local url=$2
    CHECKS=$((CHECKS + 1))
    
    echo -n "  $name ($url)... "
    
    HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" "$url" --max-time 5 2>/dev/null || echo "000")
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}✅ OK (HTTP $HTTP_CODE)${NC}"
    else
        echo -e "${RED}❌ FAILED (HTTP $HTTP_CODE)${NC}"
        ERRORS=$((ERRORS + 1))
    fi
}

check_health "Alert Ingestion"      "http://localhost:8001/health"
check_health "Incident Management"  "http://localhost:8002/health"
check_health "On-Call Service"      "http://localhost:8003/health"
check_health "Notification Service" "http://localhost:8004/health"
check_health "Web UI"               "http://localhost:8080/health"
check_health "Prometheus"           "http://localhost:9090/-/healthy"
check_health "Grafana"              "http://localhost:3000/api/health"

echo ""

# ============================================
# Prometheus Targets Check
# ============================================
echo -e "${YELLOW}📡 Prometheus Targets${NC}"
echo ""

PROM_TARGETS=$(curl -sf "http://localhost:9090/api/v1/targets" --max-time 5 2>/dev/null || echo "")
if [ -n "$PROM_TARGETS" ]; then
    ACTIVE=$(echo "$PROM_TARGETS" | python3 -c "import sys,json; data=json.load(sys.stdin); print(len([t for t in data.get('data',{}).get('activeTargets',[]) if t.get('health')=='up']))" 2>/dev/null || echo "?")
    TOTAL_T=$(echo "$PROM_TARGETS" | python3 -c "import sys,json; data=json.load(sys.stdin); print(len(data.get('data',{}).get('activeTargets',[])))" 2>/dev/null || echo "?")
    echo -e "  Targets UP: ${GREEN}$ACTIVE / $TOTAL_T${NC}"
else
    echo -e "  ${YELLOW}⚠️  Could not query Prometheus targets${NC}"
fi

echo ""

# ============================================
# Smoke Test: End-to-End
# ============================================
echo -e "${YELLOW}🔥 Smoke Test: End-to-End Flow${NC}"
echo ""

# Test 1: Create on-call schedule
echo -n "  1. Create on-call schedule... "
SCHEDULE_RESP=$(curl -sf -X POST "http://localhost:8003/api/v1/schedules" \
    -H "Content-Type: application/json" \
    -d '{"team":"smoke-test","rotation_type":"weekly","members":[{"name":"Test User","email":"test@test.com","role":"primary"}]}' \
    --max-time 5 2>/dev/null || echo "")

if echo "$SCHEDULE_RESP" | grep -q "smoke-test" 2>/dev/null; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${RED}❌ FAILED${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Test 2: Get current on-call
echo -n "  2. Query current on-call... "
ONCALL_RESP=$(curl -sf "http://localhost:8003/api/v1/oncall/current?team=smoke-test" --max-time 5 2>/dev/null || echo "")

if echo "$ONCALL_RESP" | grep -q "Test User" 2>/dev/null; then
    echo -e "${GREEN}✅ OK — On-call: Test User${NC}"
else
    echo -e "${RED}❌ FAILED${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Test 3: Send alert
echo -n "  3. Send test alert... "
ALERT_RESP=$(curl -sf -X POST "http://localhost:8001/api/v1/alerts" \
    -H "Content-Type: application/json" \
    -d '{"service":"smoke-test-svc","severity":"high","message":"Smoke test alert","timestamp":"2026-02-09T00:00:00Z"}' \
    --max-time 5 2>/dev/null || echo "")

if echo "$ALERT_RESP" | grep -q "received\|created" 2>/dev/null; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${YELLOW}⚠️  Response: $ALERT_RESP${NC}"
fi

# Test 4: Trigger escalation
echo -n "  4. Trigger escalation... "
ESCALATION_RESP=$(curl -sf -X POST "http://localhost:8003/api/v1/escalate" \
    -H "Content-Type: application/json" \
    -d '{"team":"smoke-test","incident_id":"smoke-inc-001","reason":"Smoke test escalation"}' \
    --max-time 5 2>/dev/null || echo "")

if echo "$ESCALATION_RESP" | grep -q "escalated" 2>/dev/null; then
    echo -e "${GREEN}✅ OK${NC}"
else
    echo -e "${RED}❌ FAILED${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Test 5: Metrics are being generated
echo -n "  5. Metrics endpoint check... "
METRICS_RESP=$(curl -sf "http://localhost:8003/metrics" --max-time 5 2>/dev/null || echo "")

if echo "$METRICS_RESP" | grep -q "oncall_" 2>/dev/null; then
    echo -e "${GREEN}✅ OK — Prometheus metrics exposed${NC}"
else
    echo -e "${RED}❌ FAILED${NC}"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# ============================================
# Summary
# ============================================
if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}❌ Post-deployment verification: $ERRORS failure(s) out of $CHECKS checks${NC}"
    exit 1
else
    echo -e "${GREEN}✅ All post-deployment checks passed ($CHECKS checks)${NC}"
    exit 0
fi
