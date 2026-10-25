"""Disposable E22 backup/restore proof. Never accepts an application database.

Run from backend: .venv/bin/python -m scripts.child_backup_restore --help
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from app.modules.child.privacy_export import CHILD_EXPORT_TABLES


def require_disposable(url: str, *, database: str) -> None:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "postgresql"
        or parsed.hostname not in {"127.0.0.1", "localhost"}
        or parsed.port != 55434
        or parsed.username != "e22test"
        or parsed.path != f"/{database}"
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("only dedicated local E22 QA databases on port 55434 are allowed")


def command(args: list[str]) -> str:
    result = subprocess.run(args, capture_output=True, text=True, check=False)  # noqa: S603
    if result.returncode:
        # pg errors may include row values, credentials or SQL; never echo them.
        raise RuntimeError(f"{Path(args[0]).name} failed (exit {result.returncode}); inspect privately")
    return result.stdout


def sql(url: str, statement: str) -> str:
    return command(["psql", url, "-XAt", "-v", "ON_ERROR_STOP=1", "-c", statement]).strip()


def normalize_schema(schema: str) -> str:
    """Normalize only dump session noise and PostgreSQL's equivalent string-array casts."""
    literal = r"'(?:''|[^'])*'::character varying"
    array_cast = re.compile(r"\(\(ARRAY\[(" + literal + r"(?:,\s*" + literal + r")*)\]\)::text\[\]\)")

    def element_casts(match: re.Match[str]) -> str:
        return "(ARRAY[" + ", ".join(f"({value})::text" for value in re.findall(literal, match.group(1))) + "])"

    lines = (line for line in schema.splitlines() if not line.startswith(("\\restrict", "\\unrestrict", "-- Dumped")))
    return array_cast.sub(element_casts, "\n".join(lines)).strip()


def manifest(url: str) -> dict[str, object]:
    expected = {table.name for table in CHILD_EXPORT_TABLES}
    actual = set(
        sql(
            url, "SELECT tablename FROM pg_tables WHERE schemaname='public' AND left(tablename,6)='child_' "
        ).splitlines()
    )
    if actual != expected:
        raise ValueError("Child table inventory mismatch")
    tables = {}
    for name in sorted(expected):
        # Table names come solely from the explicit model inventory, never user input.
        rows = sql(
            url,
            f'SELECT row_to_json(r)::jsonb::text FROM public."{name}" r ORDER BY row_to_json(r)::jsonb::text',  # noqa: S608
        )
        tables[name] = {
            "rows": int(sql(url, f'SELECT count(*) FROM public."{name}"')),  # noqa: S608
            "sha256": hashlib.sha256(rows.encode()).hexdigest(),
        }
    schema = command(["pg_dump", url, "--schema-only", "--no-owner", "--no-privileges"])
    normalized = normalize_schema(schema)
    return {"tables": tables, "schema_sha256": hashlib.sha256(normalized.encode()).hexdigest()}


def prove_restore(*, source: str, target: str, report: Path) -> dict[str, object]:
    require_disposable(source, database="e22_qa_test")
    require_disposable(target, database="e22_qa_restore")
    if sql(target, "SELECT count(*) FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema')") != "0":
        raise ValueError("restore database must be empty; refuses drop/clean/overwrite")
    report.parent.mkdir(parents=True, exist_ok=True)
    # Raw dump contains sensitive data; private temporary directory, automatic removal.
    with tempfile.TemporaryDirectory(prefix="child-restore-", dir=os.environ.get("TMPDIR")) as directory:
        dump = Path(directory) / "backup.dump"
        before = manifest(source)
        tables = before["tables"]
        required = ("child_profiles", "child_generations", "child_reports")
        if not isinstance(tables, dict) or any(tables.get(name, {}).get("rows", 0) == 0 for name in required):
            raise ValueError("nonempty synthetic child, generation and report history required")
        command(["pg_dump", source, "--format=custom", "--no-owner", "--no-privileges", "--file", str(dump)])
        command(["pg_restore", "--dbname", target, "--no-owner", "--no-privileges", "--exit-on-error", str(dump)])
        restored = manifest(target)
        after = manifest(source)
    passed = before == restored == after
    result: dict[str, object] = {
        "passed": passed,
        "scope": "disposable-local-synthetic-only",
        "source_unchanged": before == after,
        "schema_and_rows_equal": before == restored,
        "manifest": before,
        "git_sha": command(["git", "rev-parse", "HEAD"]).strip(),
        "working_tree": "may-contain-uncommitted-implementation",
    }
    report.write_text(json.dumps(result, indent=2) + "\n")
    report.chmod(0o600)
    if not passed:
        raise RuntimeError("backup/restore verification mismatch; sanitized report written")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-env", default="E22_QA_SOURCE_URL")
    parser.add_argument("--target-env", default="E22_QA_RESTORE_URL")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        prove_restore(source=os.environ[args.source_env], target=os.environ[args.target_env], report=args.report)
    except (KeyError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"FAIL: {exc}\n")
    print("PASS: disposable backup/restore schema, row counts, JSON checksums; source unchanged")


if __name__ == "__main__":
    main()
