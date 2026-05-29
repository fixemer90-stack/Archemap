#!/usr/bin/env bash
set -euo pipefail

# Archemap database seed script
# Usage: ./scripts/seed.sh [--env development|test]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

ENV="${1:-development}"

echo "=== Archemap Database Seed ==="
echo "Environment: $ENV"
echo ""

source "$BACKEND_DIR/.venv/bin/activate" 2>/dev/null || true

cd "$BACKEND_DIR"

case "$ENV" in
  development)
    echo "Seeding development data..."
    # TODO: Implement seed script
    # python -m scripts.seed_dev
    echo "[PLACEHOLDER] Add seed commands here."
    ;;
  test)
    echo "Seeding test fixtures..."
    # TODO: Implement test fixture seeding
    # python -m scripts.seed_test
    echo "[PLACEHOLDER] Add test fixture commands here."
    ;;
  *)
    echo "Unknown environment: $ENV"
    echo "Usage: $0 [--env development|test]"
    exit 1
    ;;
esac

echo ""
echo "Seed complete."
