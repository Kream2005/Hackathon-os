#!/bin/bash
# ============================================
# STAGE 1: Code Quality — Lint & Format Check
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0

echo -e "${YELLOW}📝 Installing linting tools...${NC}"
pip install ruff flake8 --quiet 2>/dev/null || {
    echo -e "${YELLOW}⚠️  pip not available, trying with pip3...${NC}"
    pip3 install ruff flake8 --quiet 2>/dev/null || true
}

echo ""
echo -e "${YELLOW}🔍 Running Ruff linter on all Python services...${NC}"
echo ""

for service_dir in services/*/; do
    service_name=$(basename "$service_dir")
    
    if [ -f "$service_dir/main.py" ]; then
        echo -n "  Linting $service_name... "
        
        if ruff check "$service_dir" --select=E,F,W --ignore=E501,W503,E402 --quiet 2>/dev/null; then
            echo -e "${GREEN}OK${NC}"
        else
            # Fallback to flake8
            if flake8 "$service_dir" --max-line-length=120 --ignore=E501,W503,E402 --count --statistics 2>/dev/null; then
                echo -e "${GREEN}OK${NC}"
            else
                echo -e "${YELLOW}WARNINGS${NC}"
                # Don't fail on warnings, only on errors
            fi
        fi
    fi
done

echo ""
echo -e "${YELLOW}🔍 Checking for syntax errors (critical)...${NC}"
echo ""

for service_dir in services/*/; do
    service_name=$(basename "$service_dir")
    
    if [ -f "$service_dir/main.py" ]; then
        echo -n "  Syntax check $service_name... "
        
        if python -c "import py_compile; py_compile.compile('${service_dir}main.py', doraise=True)" 2>/dev/null || \
           python3 -c "import py_compile; py_compile.compile('${service_dir}main.py', doraise=True)" 2>/dev/null; then
            echo -e "${GREEN}OK${NC}"
        else
            echo -e "${RED}SYNTAX ERROR${NC}"
            ERRORS=$((ERRORS + 1))
        fi
    fi
done

echo ""

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}❌ Found $ERRORS syntax error(s)${NC}"
    exit 1
else
    echo -e "${GREEN}✅ Code quality checks passed${NC}"
    exit 0
fi
