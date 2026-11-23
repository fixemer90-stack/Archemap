#!/usr/bin/env bash
# Run migrated S07 against disposable Unix-socket PostgreSQL + Redis.
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
python=${PYTHON:-.venv/bin/python}
pg="$(pg_config --bindir)"
scratch=$(mktemp -d "${TMPDIR:?Set TMPDIR to a private scratch directory}/s07.XXXXXX")
cleanup() {
    redis-cli -s "$scratch/redis.sock" shutdown nosave >/dev/null 2>&1 || true
    "$pg/pg_ctl" -D "$scratch/pg" -m immediate -w stop >/dev/null 2>&1 || true
    if [[ "$scratch" == "${TMPDIR}/s07."* ]]; then rm -rf -- "$scratch"; fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

"$pg/initdb" -D "$scratch/pg" -U e23_s07 -A trust --encoding=UTF8 --locale=C.UTF-8 >"$scratch/init.log"
"$pg/pg_ctl" -D "$scratch/pg" -l "$scratch/pg.log" \
    -o "-c listen_addresses='' -c fsync=off -c synchronous_commit=off -k $scratch" -w start
"$pg/createdb" -h "$scratch" -U e23_s07 e23_s07_tests
redis-server --port 0 --unixsocket "$scratch/redis.sock" --unixsocketperm 700 \
    --dir "$scratch" --dbfilename discard.rdb --save '' --appendonly no --daemonize yes --pidfile "$scratch/redis.pid"
redis-cli -s "$scratch/redis.sock" ping
export DATABASE_URL="postgresql+asyncpg://e23_s07@/e23_s07_tests?host=$scratch"
export TEST_DATABASE_URL="$DATABASE_URL"
export REDIS_URL="unix://$scratch/redis.sock?db=0"
export CELERY_BROKER_URL="redis+socket://$scratch/redis.sock?virtual_host=1"
export CELERY_RESULT_BACKEND="redis+socket://$scratch/redis.sock?virtual_host=2"
export E23_S07_DISPOSABLE="$scratch" BUSINESS_MONITORING_ENABLED=true BUSINESS_ALERTS_ENABLED=false
export DATABASE_ECHO=false OTEL_EXPORTER_OTLP_METRICS_ENDPOINT= PYTHONNOUSERSITE=1

parent=$("$python" -c 'import runpy; print(runpy.run_path("alembic/versions/e23s07b001_add_business_operations.py")["down_revision"])')
"$python" -m alembic upgrade e23s07b001
"$python" -m alembic downgrade "$parent"
"$python" -m alembic upgrade e23s07b001
"$python" -m alembic upgrade e23s07t001
"$python" -m alembic downgrade e23s08a001
"$python" -m alembic upgrade e23s07t001
"$python" -m pytest tests/unit/test_business_operations.py tests/unit/test_business_telegram.py \
    tests/integration/test_e23_s07_operations_runtime.py "$@"
if "$python" -m alembic downgrade e23s08a001 >"$scratch/blocked.log" 2>&1; then
    printf 'Expected S07 downgrade to protect used delivery fences\n' >&2
    exit 1
fi
rg --fixed-strings --max-count 1 'refusing downgrade of used S07 Telegram delivery fences' "$scratch/blocked.log"
"$pg/psql" -h "$scratch" -U e23_s07 -d e23_s07_tests -v ON_ERROR_STOP=1 -At -c \
    "SELECT version_num, (SELECT count(*) FROM business_telegram_deliveries) FROM alembic_version;"
