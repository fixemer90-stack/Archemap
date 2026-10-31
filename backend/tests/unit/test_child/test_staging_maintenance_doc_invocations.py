"""Execute published maintenance invocations against the offline state machine."""

from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
from scripts import child_staging_maintenance as tool
from tests.unit.test_child.test_staging_maintenance_lifecycle import FakeRuntime, record, setup

ROOT = Path(__file__).resolve().parents[4]
DOC = ROOT / "docs/deployment/child-staging-maintenance.md"


def test_published_lifecycle_invocation_executes_real_cli_with_fake_docker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = FakeRuntime()
    root, source = setup(tmp_path, runtime)
    monkeypatch.setattr(tool, "CONTROLLER_ROOT", root, raising=False)
    monkeypatch.setattr(tool, "DockerRuntime", lambda: runtime)
    section = DOC.read_text().split("## Exact controller lifecycle", 1)[1].split("## Source recreation", 1)[0]
    block = next(block for block in re.findall(r"```bash\n(.*?)\n```", section, re.S) if " preflight " in block)
    actions = []
    for line in block.splitlines():
        argv = shlex.split(line)
        assert argv[:2] == ["python3", "$MAINTENANCE"]
        arguments = [
            part.replace("$MAINTENANCE_RECORD", str(source)).replace("$MAINTENANCE_OPERATOR", "reviewer")
            for part in argv[2:]
        ]
        actions.append(arguments[0])
        assert tool.main(arguments) == 0
    assert actions == ["preflight", "freeze", "status", "drain"]
    restore = DOC.read_text().split("## Exact restore and failure recovery", 1)[1]
    for line in re.findall(r'^python3 "\$MAINTENANCE" (?:restore|status).*$', restore, re.M):
        args = shlex.split(line)[2:]
        args = [
            part.replace("$MAINTENANCE_RECORD", str(source)).replace("$MAINTENANCE_OPERATOR", "reviewer")
            for part in args
        ]
        assert tool.main(args) == 0
    assert not (root / "owner.json").exists()


@pytest.mark.parametrize("drain_status", [0, 53])
def test_published_rollout_keeps_scheduler_stopped_and_uses_infinite_grace(tmp_path: Path, drain_status: int) -> None:
    text = (ROOT / "docs/deployment/child-report-rollout.md").read_text()
    block = next(
        block for block in re.findall(r"```sh\n(.*?)\n```", text, re.S) if "compose build backend worker" in block
    )
    events = tmp_path / "events"
    harness = r"""
record() { printf '%s\n' "$*" >> "$EVENTS"; }
git() { case "$*" in *rev-parse*) printf '<approved full SHA>\n';; esac; }
docker() { record "$*"; }
python3() { record drain; return "$DRAIN_STATUS"; }
"""
    result = subprocess.run(  # noqa: S603 -- complete published shell, only fake external functions
        ["/bin/bash", "--noprofile", "--norc", "-c", harness + block],
        env={
            "PATH": "",
            "APP_CHECKOUT": "/synthetic/app",
            "MAINTENANCE": "/synthetic/controller.py",
            "MAINTENANCE_RECORD": "/synthetic/approved.json",
            "MAINTENANCE_OPERATOR": "reviewer",
            "MAINTENANCE_SCHEDULER_OVERLAY": "/synthetic/scheduler.compose.json",
            "DRAIN_CONFIRMED": "true",
            "EVENTS": str(events),
            "DRAIN_STATUS": str(drain_status),
        },
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == drain_status, result.stderr
    calls = events.read_text().splitlines()
    up = [call for call in calls if " up " in call]
    if drain_status:
        assert not up and not any(" create " in call for call in calls)
    else:
        assert len(up) == 1 and up[0].endswith(
            "up -d --no-deps --timeout -1 backend worker refinement-monitor frontend"
        )
        assert calls[calls.index(up[0]) - 1] == "drain"
        assert any(call.endswith("create --no-deps scheduler") for call in calls)
        assert not any("exec -T scheduler" in call for call in calls)


def test_published_record_builder_creates_exclusive_valid_private_artifact(tmp_path: Path) -> None:
    runtime = FakeRuntime()
    root, source = setup(tmp_path, runtime)
    inventory = root / "inventory.json"
    fields = root / "approved-fields.json"
    result_path = root / "new-approved.json"
    tool.exclusive(inventory, runtime.inventory())
    tool.exclusive(fields, record(runtime))
    block = next(
        block
        for block in re.findall(r"```bash\n(.*?)\n```", DOC.read_text(), re.S)
        if "spec_from_file_location" in block
    )
    body = block.split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    command = [sys.executable, "-", str(Path(tool.__file__)), str(inventory), str(fields), str(result_path)]
    result = subprocess.run(command, input=body, text=True, capture_output=True, check=False, timeout=20)  # noqa: S603
    assert result.returncode == 0, result.stderr
    tool.validate_record(tool.read_private(result_path))
    assert result_path.stat().st_mode & 0o777 == 0o600
    result = subprocess.run(command, input=body, text=True, capture_output=True, check=False, timeout=20)  # noqa: S603
    assert result.returncode != 0
    assert json.loads(source.read_text()) == json.loads(result_path.read_text())
