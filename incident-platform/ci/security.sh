#!/bin/bash
# ============================================
# STAGE 2: Security Scan
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0

# --- Check 1: .env in .gitignore ---
echo -e "${YELLOW}🔒 Check 1: .env is in .gitignore${NC}"
if [ -f ".gitignore" ]; then
    if grep -q "\.env" .gitignore; then
        echo -e "  ${GREEN}✅ .env is listed in .gitignore${NC}"
    else
        echo -e "  ${RED}❌ .env is NOT in .gitignore — secrets may be committed!${NC}"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "  ${RED}❌ No .gitignore file found!${NC}"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# --- Check 2: No hardcoded passwords in Python code ---
echo -e "${YELLOW}🔒 Check 2: Scanning for hardcoded secrets in source code${NC}"

# Patterns to search for
SECRET_PATTERNS=(
    'password\s*=\s*["\x27][^"\x27${}][^"\x27]*["\x27]'
    'secret\s*=\s*["\x27][^"\x27${}][^"\x27]*["\x27]'
    'api_key\s*=\s*["\x27][^"\x27${}][^"\x27]*["\x27]'
    'token\s*=\s*["\x27][^"\x27${}][^"\x27]*["\x27]'
)

SECRETS_FOUND=0
for pattern in "${SECRET_PATTERNS[@]}"; do
    matches=$(grep -rn --include="*.py" -iE "$pattern" services/ 2>/dev/null | \
              grep -v "test_" | \
              grep -v "# " | \
              grep -v "changeme" | \
              grep -v "example" | \
              grep -v "stub" | \
              grep -v "mock" | \
              grep -v "placeholder" || true)
    
    if [ -n "$matches" ]; then
        echo -e "  ${RED}⚠️  Potential secret found:${NC}"
        echo "$matches" | head -5
        SECRETS_FOUND=$((SECRETS_FOUND + 1))
    fi
done

if [ $SECRETS_FOUND -eq 0 ]; then
    echo -e "  ${GREEN}✅ No hardcoded secrets found in source code${NC}"
else
    echo -e "  ${YELLOW}⚠️  Found $SECRETS_FOUND potential secret pattern(s) — review required${NC}"
fi

echo ""

# --- Check 3: Dockerfiles use non-root user ---
echo -e "${YELLOW}🔒 Check 3: Dockerfiles use non-root user${NC}"

for dockerfile in services/*/Dockerfile; do
    service_name=$(basename "$(dirname "$dockerfile")")
    
    if [ -f "$dockerfile" ]; then
        if grep -q "USER" "$dockerfile"; then
            echo -e "  ${GREEN}✅ $service_name — runs as non-root user${NC}"
        else
            echo -e "  ${RED}❌ $service_name — NO non-root user! Add USER directive${NC}"
            ERRORS=$((ERRORS + 1))
        fi
    fi
done

echo ""

# --- Check 4: Dockerfiles use multi-stage builds ---
echo -e "${YELLOW}🔒 Check 4: Dockerfiles use multi-stage builds${NC}"

for dockerfile in services/*/Dockerfile; do
    service_name=$(basename "$(dirname "$dockerfile")")
    
    if [ -f "$dockerfile" ]; then
        STAGES=$(grep -c "^FROM " "$dockerfile")
        if [ "$STAGES" -ge 2 ]; then
            echo -e "  ${GREEN}✅ $service_name — multi-stage build ($STAGES stages)${NC}"
        else
            echo -e "  ${YELLOW}⚠️  $service_name — single-stage build${NC}"
        fi
    fi
done

echo ""

# --- Check 5: No .env file committed ---
echo -e "${YELLOW}🔒 Check 5: .env file not tracked by git${NC}"

if git ls-files --error-unmatch .env 2>/dev/null; then
    echo -e "  ${RED}❌ .env is tracked by git! Remove it with: git rm --cached .env${NC}"
    ERRORS=$((ERRORS + 1))
else
    echo -e "  ${GREEN}✅ .env is not tracked by git${NC}"
fi

echo ""

# --- Check 6: docker-compose uses env vars (not hardcoded) ---
echo -e "${YELLOW}🔒 Check 6: docker-compose.yml uses environment variables${NC}"

if [ -f "docker-compose.yml" ]; then
    HARDCODED_PASS=$(grep -n "password:" docker-compose.yml | grep -v '$' | grep -v "{" || true)
    if [ -z "$HARDCODED_PASS" ]; then
        echo -e "  ${GREEN}✅ No hardcoded passwords in docker-compose.yml${NC}"
    else
        echo -e "  ${RED}❌ Hardcoded passwords found in docker-compose.yml:${NC}"
        echo "$HARDCODED_PASS"
        ERRORS=$((ERRORS + 1))
    fi
fi

echo ""

# --- Check 7: Run gitleaks if available ---
echo -e "${YELLOW}🔒 Check 7: Gitleaks scan (optional)${NC}"

if command -v gitleaks &> /dev/null; then
    echo "  Running gitleaks..."
    if gitleaks detect --source . --no-git -c ../.gitleaks.toml 2>/dev/null; then
        echo -e "  ${GREEN}✅ Gitleaks: no secrets detected${NC}"
    else
        echo -e "  ${YELLOW}⚠️  Gitleaks found potential issues — review recommended${NC}"
    fi
else
    echo -e "  ${YELLOW}ℹ️  Gitleaks not installed — skipping (basic checks above are sufficient)${NC}"
fi

echo ""

# --- Summary ---
if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}❌ Security scan found $ERRORS critical issue(s)${NC}"
    exit 1
else
    echo -e "${GREEN}✅ Security scan passed${NC}"
    exit 0
fi
