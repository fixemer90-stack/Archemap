"""Offline contracts for the executable operator documentation; no app imports."""

from __future__ import annotations

import ast
import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
SOP = ROOT / "docs/deployment/child-operator-procedures.md"


def _section(heading: str) -> str:
    return SOP.read_text().split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]


def _backup_script() -> str:
    blocks: list[str] = re.findall(r"```bash\n(.*?)\n```", _section("Application backup/restore SOP"), re.S)
    backups = [block for block in blocks if "pre-freeze-identity.json" in block and "application.dump" in block]
    assert len(backups) == 1, "Select the unique backup lifecycle, not the preceding drain-inspection example"
    return backups[0]


@pytest.mark.parametrize(
    ("scenario", "status", "created"),
    [
        ("success", 0, True),
        ("restore_failure", 41, True),
        ("compare_failure", 37, True),
        ("create_failure", 43, False),
        ("INT", 130, True),
        ("TERM", 143, True),
        ("cleanup_failure", 1, True),
        ("failure_and_cleanup_failure", 37, True),
    ],
)
def test_backup_cleanup_finishes_before_caller_resumes(
    tmp_path: Path, scenario: str, status: int, created: bool
) -> None:
    script = tmp_path / "maintenance.bash"
    script.write_text(_backup_script() + "\n")
    events = tmp_path / "events"
    # Bash functions replace every external command in the extracted block.
    # PATH is deliberately empty: an un-stubbed executable must fail closed.
    harness = r"""
record() { printf '%s\n' "$1" >> "$EVENTS"; }
date() { printf '1234567890\n'; }
sha256sum() { printf 'synthetic-checksum\n'; }
docker() {
  case "$*" in
    inspect*) printf 'true\n' ;;
    stop*) record stop ;;
    start*) record restart ;;
    *pg_dump*) record dump; printf 'synthetic archive\n' ;;
    *createdb*)
      record create
      if [[ "$SCENARIO" = create_failure ]]; then return 43; fi ;;
    *pg_restore*)
      record restore
      if [[ "$SCENARIO" = restore_failure ]]; then return 41; fi ;;
    *dropdb*)
      record drop
      if [[ "$SCENARIO" = *cleanup_failure ]]; then return 49; fi ;;
    *) record unexpected_docker; return 99 ;;
  esac
  return 0
}
python3() {
  case "$*" in
    *--database*)
      record compare
      case "$SCENARIO" in
        compare_failure|failure_and_cleanup_failure) return 37 ;;
        INT|TERM) kill -s "$SCENARIO" "$BASHPID" ;;
      esac ;;
    *) record snapshot ;;
  esac
  return 0
}
source "$SCRIPT"
status=$?
printf 'caller:%s\n' "$status" >> "$EVENTS"
exit 0
"""
    result = subprocess.run(  # noqa: S603 -- local Bash with only synthetic, stubbed inputs
        ["/bin/bash", "--noprofile", "--norc", "-c", harness],
        env={
            "PATH": "",
            "HOME": str(tmp_path),
            "CHECKOUT": str(ROOT),
            "PRIVATE_DIR": str(tmp_path),
            "OPERATOR_SHA": "a" * 40,
            "DRAIN_CONFIRMED": "true",
            "SCRIPT": str(script),
            "EVENTS": str(events),
            "SCENARIO": scenario,
            "LC_ALL": "C",
        },
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    observed = events.read_text().splitlines()
    assert "unexpected_docker" not in observed
    assert observed[-1] == f"caller:{status}", observed
    assert observed.count("restart") == 1, observed
    assert observed.index("stop") < observed.index("restart") < len(observed) - 1
    assert observed.count("drop") == int(created), observed
    if created:
        assert observed.index("drop") < observed.index("restart")
    assert os.stat(tmp_path / "application.dump").st_size > 0


@pytest.mark.parametrize("confirmation", [None, "false", "TRUE"])
def test_backup_refuses_unconfirmed_drain_before_any_external_action(tmp_path: Path, confirmation: str | None) -> None:
    events = tmp_path / "external-actions"
    harness = r"""
record() { printf '%s\n' "$1" >> "$EVENTS"; return 99; }
docker() { record docker; }
python3() { record python; }
date() { record date; }
sha256sum() { record checksum; }
"""
    env = {
        "PATH": "",
        "CHECKOUT": str(ROOT),
        "PRIVATE_DIR": str(tmp_path),
        "OPERATOR_SHA": "a" * 40,
        "EVENTS": str(events),
    }
    if confirmation is not None:
        env["DRAIN_CONFIRMED"] = confirmation
    result = subprocess.run(  # noqa: S603 -- extracted documentation with synthetic command stubs
        ["/bin/bash", "--noprofile", "--norc", "-c", harness + _backup_script()],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 1, result.stderr
    assert not events.exists(), "Missing drain approval must stop before Docker, DB reads or backup commands"
    assert not (tmp_path / "application.dump").exists()


def test_initial_backup_guard_executes_against_legacy_only_inventory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import json
    import shlex

    from scripts import child_runtime_state as state

    initial = next(line for line in _backup_script().splitlines() if "pre-freeze-identity.json" in line)
    argv = [
        value.replace("$PG", state.CONTAINER).replace("$PRIVATE_DIR", str(tmp_path))
        for value in shlex.split(initial)[2:]
    ]

    def run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if args[:2] == ["docker", "inspect"]:
            body = json.dumps(
                [
                    {
                        "Config": {
                            "Labels": {
                                "com.docker.compose.project": "astrotype-staging",
                                "com.docker.compose.service": "postgres",
                            }
                        }
                    }
                ]
            )
        elif "pg_tables" in str(kwargs.get("input")):
            body = "entitlements\npayments\nperson_profiles\nusers\n"
        elif "count(*)" in str(kwargs.get("input")):
            body = "1\n"
        else:
            body = "synthetic legacy row or schema\n"
        return subprocess.CompletedProcess(args, 0, stdout=body, stderr="")

    monkeypatch.setattr(subprocess, "run", run)
    assert state.main(argv) == 0
    manifest = json.loads((tmp_path / "pre-freeze-identity.json").read_text())
    assert manifest["all_public"] and set(manifest["tables"]) == state.ACCOUNTS


def test_self_generation_polling_url_matches_implemented_router() -> None:
    router = ast.parse((ROOT / "backend/app/modules/astrotype_v2/router.py").read_text())
    prefix = next(
        ast.literal_eval(keyword.value)
        for node in ast.walk(router)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "APIRouter"
        for keyword in node.keywords
        if keyword.arg == "prefix"
    )
    generation = next(
        node
        for node in router.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "get_v2_generation_status"
    )
    path = next(
        ast.literal_eval(decorator.args[0])
        for decorator in generation.decorator_list
        if isinstance(decorator, ast.Call)
        and isinstance(decorator.func, ast.Attribute)
        and decorator.func.attr == "get"
    )
    assert 'application.include_router(api_router, prefix="/api/v1")' in (ROOT / "backend/app/main.py").read_text()
    assert "api_router.include_router(astrotype_v2_router)" in (ROOT / "backend/app/api/v1/__init__.py").read_text()
    expected = f"/api/v1{prefix}{path}"
    assert expected == "/api/v1/astrotype-v2/reports/generations/{generation_id}"
    ledger = _section("Fixture acquisition ledger")
    assert f"poll `{expected}`" in ledger
    assert "/api/v1/astrotype-v2/generations/" not in SOP.read_text()


def test_expiry_recipe_excludes_every_native_auth_fallback_before_denial_checks() -> None:
    dependencies = ast.parse((ROOT / "backend/app/dependencies.py").read_text())
    auth_router = ast.parse((ROOT / "backend/app/modules/auth/router.py").read_text())
    cookie_names = {
        node.value
        for tree in (dependencies, auth_router)
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.endswith("token")
    }
    assert cookie_names == {"access_token", "astrotype_token", "refresh_token", "astrotype_refresh_token"}
    recipe = _section("Safe scenario trigger matrix").split("### Isolated late-expiry recipe\n", 1)
    assert len(recipe) == 2, "Expiry needs an isolated-context recipe, not access-cookie replacement alone"
    instructions = recipe[1]
    for cookie_name in sorted(cookie_names):
        assert f"`{cookie_name}`" in instructions
    for required in (
        "fresh isolated synthetic browser context",
        "all domains and paths",
        "Authorization: Bearer",
        "localStorage",
        "sessionStorage",
        "in-memory",
        "no normal login/refresh fallback",
        "genuinely signed expired native access token",
        "Do not intercept/mock",
        "actual HTTP 401",
        "before asserting",
        "all 21 hashes unchanged",
        "Close only this browser context",
        "Never log tokens",
        "Historical expiry probes used fresh contexts",
    ):
        assert required in instructions
    assert instructions.index("all domains and paths") < instructions.index(
        "genuinely signed expired native access token"
    )
    assert instructions.index("actual HTTP 401") < instructions.index("all 21 hashes unchanged")
