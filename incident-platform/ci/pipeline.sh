#!/bin/bash
# ============================================
# CI/CD PIPELINE — Orchestrateur Principal
# ============================================
# Usage: ./ci/pipeline.sh
# Exécute toutes les étapes du pipeline séquentiellement
# Exit code: 0 si tout passe, 1 sinon
# ============================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

# Get script directory (for relative imports)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Track results
declare -a STAGE_NAMES
declare -a STAGE_RESULTS
declare -a STAGE_TIMES
PIPELINE_START=$(date +%s)
TOTAL_STAGES=0
PASSED_STAGES=0

# ============================================
# Helper Functions
# ============================================
run_stage() {
    local stage_num=$1
    local stage_name=$2
    local stage_script=$3
    
    TOTAL_STAGES=$((TOTAL_STAGES + 1))
    STAGE_NAMES+=("$stage_name")
    
    echo ""
    echo -e "${BOLD}${CYAN}══════════════════════════════════════════${NC}"
    echo -e "${BOLD}${CYAN}  STAGE ${stage_num}: ${stage_name}${NC}"
    echo -e "${BOLD}${CYAN}══════════════════════════════════════════${NC}"
    echo ""
    
    local stage_start=$(date +%s)
    
    if bash "$SCRIPT_DIR/$stage_script"; then
        local stage_end=$(date +%s)
        local duration=$((stage_end - stage_start))
        STAGE_RESULTS+=("PASS")
        STAGE_TIMES+=("${duration}s")
        PASSED_STAGES=$((PASSED_STAGES + 1))
        echo ""
        echo -e "${GREEN}  ✅ Stage ${stage_num} PASSED (${duration}s)${NC}"
    else
        local stage_end=$(date +%s)
        local duration=$((stage_end - stage_start))
        STAGE_RESULTS+=("FAIL")
        STAGE_TIMES+=("${duration}s")
        echo ""
        echo -e "${RED}  ❌ Stage ${stage_num} FAILED (${duration}s)${NC}"
        
        # Print summary and exit
        print_summary
        exit 1
    fi
}

print_summary() {
    local pipeline_end=$(date +%s)
    local total_duration=$((pipeline_end - PIPELINE_START))
    
    echo ""
    echo ""
    echo -e "${BOLD}${PURPLE}══════════════════════════════════════════${NC}"
    echo -e "${BOLD}${PURPLE}           PIPELINE SUMMARY${NC}"
    echo -e "${BOLD}${PURPLE}══════════════════════════════════════════${NC}"
    echo ""
    
    for i in "${!STAGE_NAMES[@]}"; do
        local icon="✅"
        local color="$GREEN"
        if [ "${STAGE_RESULTS[$i]}" = "FAIL" ]; then
            icon="❌"
            color="$RED"
        fi
        printf "  ${color}${icon} %-30s %s${NC}\n" "${STAGE_NAMES[$i]}" "${STAGE_TIMES[$i]}"
    done
    
    echo ""
    echo -e "  ${BOLD}Stages: ${PASSED_STAGES}/${TOTAL_STAGES} passed${NC}"
    echo -e "  ${BOLD}Duration: ${total_duration}s${NC}"
    echo ""
    
    if [ "$PASSED_STAGES" -eq "$TOTAL_STAGES" ]; then
        echo -e "${BOLD}${GREEN}  🎉 PIPELINE PASSED ✅${NC}"
    else
        echo -e "${BOLD}${RED}  💥 PIPELINE FAILED ❌${NC}"
    fi
    echo ""
    echo -e "${PURPLE}══════════════════════════════════════════${NC}"
}

# ============================================
# Pipeline Execution
# ============================================
echo -e "${BOLD}${BLUE}"
echo "  ╔══════════════════════════════════════╗"
echo "  ║     INCIDENT PLATFORM CI/CD          ║"
echo "  ║     Pipeline v2.0.0 (8 stages)       ║"
echo "  ╚══════════════════════════════════════╝"
echo -e "${NC}"
echo -e "  📅 $(date)"
echo -e "  📁 Project: $PROJECT_DIR"

GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "no-git")
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "no-branch")
echo -e "  🌿 Branch: $GIT_BRANCH ($GIT_SHA)"
echo ""

# Run all stages
run_stage 1 "Code Quality (Lint)"       "quality.sh"
run_stage 2 "Security Scan"             "security.sh"
run_stage 3 "Tests & Coverage"          "test.sh"
run_stage 4 "Build Container Images"    "build.sh"
run_stage 5 "Image Vulnerability Scan"  "scan.sh"
run_stage 6 "Deploy (docker compose)"   "deploy.sh"
run_stage 7 "Post-Deploy Verification"  "verify.sh"
run_stage 8 "Integration Tests (E2E)"   "integration-test.sh"

# Print final summary
print_summary
exit 0
