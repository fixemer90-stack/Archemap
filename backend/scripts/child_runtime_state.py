"""Read-only staging Child/account row hashes. Run on the approved staging Docker host."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

CONTAINER = "astrotype-staging-postgres-1"
ACCOUNTS = {"users", "person_profiles", "entitlements", "payments"}


def command(args: list[str], *, query: str | None = None) -> str:
    # All callers use literal Docker operations and the exact allowlisted container.
    result = subprocess.run(args, input=query, capture_output=True, text=True, timeout=120, check=False)  # noqa: S603
    if result.returncode:
        raise ValueError("staging read transport failed")
    return result.stdout.strip()


def normalize_schema(schema: str) -> str:
    """Same narrow PostgreSQL dump normalization as the existing QA restore proof."""
    literal = r"'(?:''|[^'])*'::character varying"
    casts = re.compile(r"\(\(ARRAY\[(" + literal + r"(?:,\s*" + literal + r")*)\]\)::text\[\]\)")

    def elements(match: re.Match[str]) -> str:
        return "(ARRAY[" + ", ".join("(" + v + ")::text" for v in re.findall(literal, match.group(1))) + "])"

    lines = (line for line in schema.splitlines() if not line.startswith(("\\restrict", "\\unrestrict", "-- Dumped")))
    return casts.sub(elements, "\n".join(lines)).strip()


def snapshot(container: str, *, all_public: bool = False, database: str | None = None) -> dict[str, Any]:
    if container != CONTAINER:
        raise ValueError("only the approved staging container is allowed")
    if database is not None and not re.fullmatch(r"e22_restore_[0-9a-f]{12}_[0-9]+", database):
        raise ValueError("only disposable restore database names are allowed")
    inspected = json.loads(command(["docker", "inspect", container]))[0]
    labels = inspected["Config"]["Labels"]
    if (
        labels.get("com.docker.compose.project") != "astrotype-staging"
        or labels.get("com.docker.compose.service") != "postgres"
    ):
        raise ValueError("staging project/service identity mismatch")

    def sql(query: str) -> str:
        return command(
            [
                "docker",
                "exec",
                "-i",
                container,
                "sh",
                "-c",
                'psql -XAtq -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "${1:-$POSTGRES_DB}"',
                "sh",
                database or "",
            ],
            query="BEGIN TRANSACTION READ ONLY;\n" + query + ";\nCOMMIT;\n",
        )

    inventory_query = (
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
        if all_public
        else "SELECT tablename FROM pg_tables WHERE schemaname='public' "
        "AND (left(tablename,6)='child_' OR tablename IN "
        "('users','person_profiles','entitlements','payments')) ORDER BY tablename"
    )
    names = sql(inventory_query).splitlines()
    if (
        not ACCOUNTS.issubset(names)
        or (not all_public and not any(n.startswith("child_") for n in names))
        or len(names) != len(set(names))
    ):
        raise ValueError("incomplete or duplicate protected inventory")
    if not all(
        re.fullmatch(r"[a-z][a-z0-9_]*", n) and (all_public or n.startswith("child_") or n in ACCOUNTS) for n in names
    ):
        raise ValueError("unexpected protected inventory")
    tables = {}
    for name in names:
        # Identifiers above are ASCII-validated and restricted to the protected inventory.
        rows = sql(f'SELECT to_jsonb(t)::text FROM public."{name}" t ORDER BY to_jsonb(t)::text')  # noqa: S608
        count = int(sql(f'SELECT count(*) FROM public."{name}"'))  # noqa: S608
        tables[name] = {"rows": count, "sha256": hashlib.sha256(rows.encode()).hexdigest()}
    result: dict[str, Any] = {"container": container, "tables": tables, "all_public": all_public}
    if all_public:
        schema = command(
            [
                "docker",
                "exec",
                container,
                "sh",
                "-c",
                'pg_dump -U "$POSTGRES_USER" -d "${1:-$POSTGRES_DB}" --schema-only --no-owner --no-privileges',
                "sh",
                database or "",
            ]
        )
        result["schema_sha256"] = hashlib.sha256(normalize_schema(schema).encode()).hexdigest()
    return result


def private_write(path: Path, body: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(json.dumps(body, indent=2) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--snapshot", type=Path)
    mode.add_argument("--compare", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--all-public", action="store_true", help="Full application public schema and all table hashes")
    parser.add_argument("--database", help="Disposable e22_restore_<12 hex>_<digits> database; default is staging app")
    args = parser.parse_args(argv)
    try:
        if args.container != CONTAINER or (args.compare and not args.report) or (args.snapshot and args.report):
            raise ValueError("invalid staging scope or output mode")
        output = args.snapshot or args.report
        if output.exists():
            raise ValueError("output already exists")
        baseline = json.loads(args.compare.read_text()) if args.compare else None
        current = snapshot(args.container, all_public=args.all_public, database=args.database)
        if args.snapshot:
            private_write(args.snapshot, current)
            print("PASS: private staging snapshot saved")
            return 0
        passed = baseline == current
        private_write(
            args.report,
            {
                "passed": passed,
                "protected_tables": len(current["tables"]),
                "scope": "full application public schema and rows"
                if args.all_public
                else "Child and account/billing hashes",
            },
        )
        print("PASS: protected rows unchanged" if passed else "FAIL: protected rows changed; inspect privately")
        return 0 if passed else 1
    except (ValueError, KeyError, TypeError, IndexError, OSError, subprocess.SubprocessError):
        print("FAIL: staging identity, read transport or private output; inspect privately")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
