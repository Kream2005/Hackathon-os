#!/bin/bash
# ============================================
# Git Pre-commit Hook Setup
# ============================================
# Installs a pre-commit hook that scans staged
# files for hardcoded secrets before committing
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🔧 Setting up Git pre-commit hook...${NC}"

# Find git root
GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
if [ -z "$GIT_ROOT" ]; then
    echo -e "${RED}❌ Not inside a git repository${NC}"
    exit 1
fi

HOOK_DIR="$GIT_ROOT/.git/hooks"
HOOK_FILE="$HOOK_DIR/pre-commit"

# Create hook
cat > "$HOOK_FILE" << 'HOOKEOF'
#!/bin/bash
# ============================================
# Pre-commit Hook: Secret Detection
# ============================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0

echo -e "${YELLOW}🔒 Pre-commit: Scanning for secrets...${NC}"

# Get staged files (only added/modified, not deleted)
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)

if [ -z "$STAGED_FILES" ]; then
    echo -e "${GREEN}✅ No files to scan${NC}"
    exit 0
fi

# --- Pattern List ---
PATTERNS=(
    # AWS
    'AKIA[0-9A-Z]{16}'
    # Generic API key/token/secret
    '["\x27]?[a-zA-Z_]*(?:api[_-]?key|api[_-]?secret|access[_-]?token|secret[_-]?key|password|passwd|pwd)["\x27]?\s*[:=]\s*["\x27][^\s"'\'']{8,}["\x27]'
    # Private keys
    '-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----'
    # Connection strings
    'postgres://[^\s]+:[^\s]+@'
    'mysql://[^\s]+:[^\s]+@'
    'mongodb(\+srv)?://[^\s]+:[^\s]+@'
    # JWT tokens
    'eyJ[a-zA-Z0-9_-]{20,}\.eyJ[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,}'
)

# Files to skip
SKIP_PATTERNS="\.lock$|\.min\.js$|node_modules|\.git/|test_|_test\.py|\.md$|\.json$|\.yml$|\.yaml$|\.toml$|setup-hooks\.sh|\.env\.example"

for file in $STAGED_FILES; do
    # Skip certain files
    if echo "$file" | grep -qE "$SKIP_PATTERNS"; then
        continue
    fi

    for pattern in "${PATTERNS[@]}"; do
        MATCHES=$(grep -nEi "$pattern" "$file" 2>/dev/null || true)
        if [ -n "$MATCHES" ]; then
            echo -e "${RED}❌ Potential secret in $file:${NC}"
            echo "$MATCHES" | head -3
            ERRORS=$((ERRORS + 1))
        fi
    done
done

if [ $ERRORS -gt 0 ]; then
    echo ""
    echo -e "${RED}❌ $ERRORS potential secret(s) found in staged files!${NC}"
    echo -e "${YELLOW}   Use 'git commit --no-verify' to skip (not recommended)${NC}"
    exit 1
fi

echo -e "${GREEN}✅ No secrets detected — commit allowed${NC}"
exit 0
HOOKEOF

chmod +x "$HOOK_FILE"

echo -e "${GREEN}✅ Pre-commit hook installed: $HOOK_FILE${NC}"
echo -e "   Hook scans for: AWS keys, API secrets, private keys, DB URIs, JWTs"
echo ""

# Verify
if [ -f "$HOOK_FILE" ] && [ -x "$HOOK_FILE" ]; then
    echo -e "${GREEN}✅ Hook is executable and ready${NC}"
else
    echo -e "${RED}❌ Hook installation failed${NC}"
    exit 1
fi

exit 0
