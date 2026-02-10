#!/bin/bash
# ============================================
# STAGE 3: Tests & Coverage
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

COVERAGE_THRESHOLD=60
ERRORS=0
TESTED=0

# ── Load .env ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a; source "$PROJECT_DIR/.env"; set +a
fi

echo -e "${YELLOW}🧪 Installing test dependencies...${NC}"
pip install pytest pytest-cov httpx fastapi uvicorn prometheus-client pydantic --quiet 2>/dev/null || \
pip3 install pytest pytest-cov httpx fastapi uvicorn prometheus-client pydantic --quiet 2>/dev/null || true

echo ""
echo -e "${YELLOW}🧪 Running tests for each service...${NC}"
echo ""

for service_dir in services/*/; do
    service_name=$(basename "$service_dir")
    
    # Check if test file exists
    if [ -f "$service_dir/test_main.py" ]; then
        TESTED=$((TESTED + 1))
        echo -e "${YELLOW}  Testing $service_name...${NC}"
        
        cd "$service_dir"
        
        if python -m pytest test_main.py \
            --cov=main \
            --cov-report=term-missing \
            --cov-fail-under=$COVERAGE_THRESHOLD \
            -v \
            --tb=short \
            2>&1; then
            echo -e "  ${GREEN} $service_name: tests passed (coverage ≥ ${COVERAGE_THRESHOLD}%)${NC}"
        else
            echo -e "  ${RED} $service_name: tests FAILED or coverage < ${COVERAGE_THRESHOLD}%${NC}"
            ERRORS=$((ERRORS + 1))
        fi
        
        cd - > /dev/null
        echo ""
    else
        echo -e "  ${YELLOW}  $service_name: no test_main.py found — skipping${NC}"
    fi
done

echo ""
echo -e "${YELLOW} Test Summary:${NC}"
echo -e "  Services tested: $TESTED"
echo -e "  Coverage threshold: ${COVERAGE_THRESHOLD}%"

if [ $TESTED -eq 0 ]; then
    echo -e "${YELLOW} No test files found — ensure at least oncall-service has tests${NC}"
    # Don't fail if no tests exist yet (WIP), but warn
    exit 0
fi

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED} $ERRORS service(s) failed tests or coverage${NC}"
    exit 1
else
    echo -e "${GREEN}✅ All tests passed with ≥ ${COVERAGE_THRESHOLD}% coverage${NC}"
    exit 0
fi
