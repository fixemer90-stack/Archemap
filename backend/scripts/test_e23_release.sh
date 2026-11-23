#!/usr/bin/env bash
# Exercise E23's opt-in route, outbox migration, and report queue cases on disposable services.
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
python=${E23_TEST_PYTHON:-.venv/bin/python}
pg=$(pg_config --bindir)
scratch=$(mktemp -d "${TMPDIR:?Use a private temporary directory}/e23-release.XXXXXX")
cleanup() {
    redis-cli -s "$scratch/redis.sock" shutdown nosave >/dev/null 2>&1 || true
    "$pg/pg_ctl" -D "$scratch/pg" -m immediate -w stop >/dev/null 2>&1 || true
    if [[ "$scratch" == "${TMPDIR}/e23-release."* ]]; then rm -rf -- "$scratch"; fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

"$pg/initdb" -D "$scratch/pg" -U e23_ci -A trust --encoding=UTF8 --locale=C.UTF-8 --no-sync >"$scratch/init.log"
"$pg/pg_ctl" -D "$scratch/pg" -l "$scratch/pg.log" -o "-F -c listen_addresses='' -k $scratch -c lock_timeout=5000" -w start
redis-server --port 0 --unixsocket "$scratch/redis.sock" --unixsocketperm 700 --save '' --appendonly no --daemonize yes --dir "$scratch"
for attempt in {1..25}; do
    if redis-cli -s "$scratch/redis.sock" ping >/dev/null 2>&1; then break; fi
    sleep 0.2
done
redis-cli -s "$scratch/redis.sock" ping
"$pg/createdb" -h "$scratch" -U e23_ci e23_tests
"$pg/createdb" -h "$scratch" -U e23_ci e23_migration
export TEST_DATABASE_URL="postgresql+asyncpg://e23_ci@/e23_tests?host=$scratch" DATABASE_URL="postgresql+asyncpg://e23_ci@/e23_tests?host=$scratch"
export BUSINESS_EVENT_MIGRATION_DATABASE_URL="postgresql+asyncpg://e23_ci@/e23_migration?host=$scratch"
export REDIS_URL="unix://$scratch/redis.sock?db=0" CELERY_BROKER_URL="redis+socket://$scratch/redis.sock?virtual_host=1" CELERY_RESULT_BACKEND="redis+socket://$scratch/redis.sock?virtual_host=2"
export E23_DISPOSABLE_TEST_DATABASES=1 LLM_ENABLED=false LLM_PROVIDER=mock CAREER_LLM_PROVIDER=mock CHILD_LLM_PROVIDER=mock
export BUSINESS_ALERTS_ENABLED=false YANDEX_METRICA_EXPORT_ENABLED=false
"$python" -m pytest -q --tb=short \
    tests/unit/test_business_cohorts.py tests/unit/test_business_event_schema.py \
    tests/unit/test_e23_overview_route.py tests/unit/test_e23_s05_collector.py \
    tests/integration/test_e23_overview_postgresql.py tests/integration/test_business_event_outbox.py \
    tests/integration/test_career_report_requested.py tests/integration/test_child_business_events.py "$@"
