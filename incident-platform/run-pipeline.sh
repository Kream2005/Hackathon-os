#!/bin/bash
# ============================================
# Quick Pipeline Runner
# Run from project root: ./run-pipeline.sh
# ============================================

set -e

cd "$(dirname "$0")"

echo "🚀 Starting CI/CD Pipeline..."
echo ""

chmod +x ci/*.sh 2>/dev/null || true
bash ci/pipeline.sh
