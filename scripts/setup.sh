#!/usr/bin/env bash
set -euo pipefail

# Archemap project setup script
# Run from the repository root: ./scripts/setup.sh

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

# ── Prerequisites ───────────────────────────────────────────────────────────

check_prereq() {
  command -v "$1" &>/dev/null || error "$1 is required but not installed."
}

info "Checking prerequisites..."
check_prereq python3
check_prereq node
check_prereq npm
check_prereq docker
check_prereq docker

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if [[ "$(echo "$PYTHON_VERSION < 3.11" | bc)" -eq 1 ]]; then
  error "Python 3.11+ required, found $PYTHON_VERSION"
fi

NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)
if [[ "$NODE_VERSION" -lt 20 ]]; then
  error "Node.js 20+ required, found v$NODE_VERSION"
fi

info "All prerequisites satisfied."

# ── Python virtual environment ──────────────────────────────────────────────

info "Setting up Python virtual environment..."
if [[ ! -d "$BACKEND_DIR/.venv" ]]; then
  python3 -m venv "$BACKEND_DIR/.venv"
  info "Created virtual environment at $BACKEND_DIR/.venv"
else
  info "Virtual environment already exists."
fi

source "$BACKEND_DIR/.venv/bin/activate"

info "Installing Python dependencies..."
pip install --upgrade pip
pip install -r "$BACKEND_DIR/requirements.txt"
pip install -r "$BACKEND_DIR/requirements-dev.txt"

# ── Frontend dependencies ──────────────────────────────────────────────────

info "Installing frontend dependencies..."
cd "$FRONTEND_DIR"
npm install
cd "$ROOT_DIR"

# ── Environment file ────────────────────────────────────────────────────────

info "Setting up environment file..."
if [[ ! -f "$ROOT_DIR/.env" ]]; then
  if [[ -f "$ROOT_DIR/.env.example" ]]; then
    cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
    info "Copied .env.example to .env — review and update values."
  else
    warn ".env.example not found. Create .env manually."
  fi
else
  info ".env already exists."
fi

# ── Docker services ────────────────────────────────────────────────────────

info "Starting Docker Compose services..."
docker compose up -d

info "Waiting for PostgreSQL to be ready..."
for i in $(seq 1 30); do
  if docker compose exec -T postgres pg_isready -U archemap &>/dev/null; then
    break
  fi
  sleep 1
done

# ── Database migrations ────────────────────────────────────────────────────

info "Running database migrations..."
cd "$BACKEND_DIR"
alembic upgrade head
cd "$ROOT_DIR"

info ""
info "Setup complete! Next steps:"
info "  1. Review .env and update secrets"
info "  2. make backend-dev   — start the API server"
info "  3. make frontend-dev  — start the Next.js dev server"
