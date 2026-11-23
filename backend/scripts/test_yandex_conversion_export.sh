#!/usr/bin/env bash
# Verify S08 migration, durable fences and mock transport in a fresh socket-only cluster.
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
python=${PYTHON:-.venv/bin/python}
pg="$(pg_config --bindir)"
scratch=$(mktemp -d "${TMPDIR:?Set TMPDIR to a private scratch directory}/s08.XXXXXX")
cleanup() {
    "$pg/pg_ctl" -D "$scratch/pg" -m immediate -w stop >/dev/null 2>&1 || true
    rm -rf -- "$scratch"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

"$pg/initdb" -D "$scratch/pg" -U e23_s08 -A trust --no-sync --encoding=UTF8 --locale=C.UTF-8 >"$scratch/init.log"
"$pg/pg_ctl" -D "$scratch/pg" -l "$scratch/pg.log" -o "-c synchronous_commit=off -c listen_addresses='' -k '$scratch'" -w start
"$pg/createdb" -h "$scratch" -U e23_s08 e23_s08_tests
export DATABASE_URL="postgresql+asyncpg://e23_s08@/e23_s08_tests?host=$scratch"
export TEST_DATABASE_URL="$DATABASE_URL" TEST_YANDEX_EXPORT_DATABASE_URL="$DATABASE_URL"
export DATABASE_ECHO=false OTEL_EXPORTER_OTLP_METRICS_ENDPOINT= PYTHONNOUSERSITE=1
export LLM_ENABLED=false CAREER_LLM_PROVIDER=mock CHILD_LLM_PROVIDER=mock
export YANDEX_METRICA_EXPORT_ENABLED=false

sql() { "$pg/psql" -h "$scratch" -U e23_s08 -d e23_s08_tests -v ON_ERROR_STOP=1 -At -c "$1"; }
[[ $(sql "SELECT current_database() || ':' || array_to_string(current_schemas(false), ',')") == e23_s08_tests:public ]]
[[ $(sql "SELECT count(*) FROM pg_tables WHERE schemaname='public'") == 0 ]]
parent=e23s07t001
latest=e23s08b001
[[ $("$python" -m alembic heads) == "$latest (head)" ]]
"$python" -m alembic upgrade "$parent"
legacy=00000000-0000-0000-0000-000000000018
sql "INSERT INTO users (id,email,name,hashed_password,is_active,is_verified,is_superuser,created_at,updated_at)
  VALUES ('$legacy','synthetic@example.invalid','','',true,false,false,now(),now());
  INSERT INTO analytics_attributions (owner_id,policy_version,client_id,captured_at,bound_at,expires_at)
  VALUES ('$legacy','approved-v1','123456',now(),now(),now()+interval '1 day');" >/dev/null
"$python" -m alembic upgrade "$latest"
[[ $(sql "SELECT counter_id IS NULL AND client_id='123456' FROM analytics_attributions WHERE owner_id='$legacy'") == t ]]
"$python" -m alembic downgrade "$parent"
[[ $(sql "SELECT client_id FROM analytics_attributions WHERE owner_id='$legacy'") == 123456 ]]
"$python" -m alembic upgrade "$latest"
# Inherit asynchronous commit everywhere else. Real INSERTs, including the winner's
# permanent fence, must override it in their own transaction, not just emit SQL.
[[ $(sql "SHOW synchronous_commit") == off ]]
sql "UPDATE analytics_attributions SET counter_id=123 WHERE owner_id='$legacy'" >/dev/null
if "$python" -m alembic downgrade "$parent" >"$scratch/blocked-attribution.log" 2>&1; then
    printf 'Expected bound attribution to refuse downgrade\n' >&2
    exit 1
fi
rg --fixed-strings --max-count 1 'refusing S08 downgrade: keep retained attribution counter provenance' "$scratch/blocked-attribution.log"
[[ $(sql "SELECT counter_id FROM analytics_attributions WHERE owner_id='$legacy'") == 123 ]]
sql "UPDATE analytics_attributions SET counter_id=NULL WHERE owner_id='$legacy'" >/dev/null
sql 'CREATE FUNCTION fixture_require_sync_fence() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
  IF current_setting($s$synchronous_commit$s$) <> $s$on$s$ THEN
    RAISE EXCEPTION $s$fence must commit synchronously$s$;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER fixture_require_sync_fence BEFORE INSERT ON analytics_yandex_conversion_exports
FOR EACH ROW EXECUTE FUNCTION fixture_require_sync_fence();' >/dev/null
"$python" -m pytest tests/unit/test_yandex_conversion_transport.py tests/integration/test_e23_s08_yandex_conversion.py "$@"
if "$python" -m alembic downgrade "$parent" >"$scratch/blocked.log" 2>&1; then
    printf 'Expected used S08 migration to refuse downgrade\n' >&2
    exit 1
fi
rg --fixed-strings --max-count 1 'refusing S08 downgrade: keep existing offline conversion fences' "$scratch/blocked.log"
[[ $(sql "SELECT version_num FROM alembic_version") == "$latest" ]]
[[ $(sql "SELECT EXISTS (SELECT FROM analytics_yandex_conversion_exports WHERE status='outcome_unknown')") == t ]]
