"""Published post-backup adoption against the real controller state machine."""

from __future__ import annotations

import copy
import re
from pathlib import Path

import pytest
from scripts import child_staging_maintenance as tool
from tests.unit.test_child.test_staging_maintenance_lifecycle import FakeRuntime, call, record, setup

SOP = Path(__file__).resolve().parents[4] / "docs/deployment/child-operator-procedures.md"


def backup_transfer_command() -> str:
    blocks: list[str] = re.findall(r"```bash\n(.*?)\n```", SOP.read_text(), re.S)
    matches = [block for block in blocks if "MAINTENANCE_BACKUP_TRANSFER_RECORD" in block and " adopt " in block]
    assert len(matches) == 1, "Backup restart requires a published, explicit approved identity adoption"
    return matches[0]


def test_backup_cleanup_restart_requires_published_adoption_before_restore(tmp_path: Path) -> None:
    runtime = FakeRuntime()
    protected = copy.deepcopy(runtime.items[-1])
    original = copy.deepcopy(runtime.current)
    root, source = setup(tmp_path, runtime)
    call(root, source, runtime, "freeze")
    call(root, source, runtime, "drain")
    # The published backup EXIT cleanup restarts these exact running writers on
    # success, failure and catchable signals, advancing their native StartedAt.
    for item in runtime.items:
        if item["project"] == tool.PROJECT and item["service"] in {
            "backend",
            "worker",
            "refinement-monitor",
            "frontend",
        }:
            item["started_at"] = "2026-10-31T01:00:00Z"
    with pytest.raises(ValueError, match="inventory drift"):
        call(root, source, runtime, "restore")
    command = backup_transfer_command()
    assert '--record "$MAINTENANCE_RECORD"' in command
    assert '--operator "$MAINTENANCE_OPERATOR"' in command
    assert '--replacement "$MAINTENANCE_BACKUP_TRANSFER_RECORD"' in command
    transfer = root / "backup-approved-transfer.json"
    tool.exclusive(transfer, record(runtime))
    result = tool.run(
        "adopt", root=root, record_path=source, runtime=runtime, operator="reviewer", replacement_path=transfer
    )
    assert result["phase"] == "FROZEN"
    assert runtime.items[-1] == protected
    assert call(root, source, runtime, "drain")["phase"] == "DRAIN_CONFIRMED"
    assert call(root, source, runtime, "restore")["phase"] == "RESTORED"
    assert runtime.current == original
    assert runtime.items[-1] == protected


def test_backup_transfer_cannot_bless_protected_started_at_drift(tmp_path: Path) -> None:
    runtime = FakeRuntime()
    root, source = setup(tmp_path, runtime)
    call(root, source, runtime, "freeze")
    call(root, source, runtime, "drain")
    runtime.items[-1]["started_at"] = "2026-10-31T01:00:00Z"
    transfer = root / "unsafe-transfer.json"
    tool.exclusive(transfer, record(runtime))
    with pytest.raises(ValueError, match="protected/gateway/data-service drift"):
        tool.run(
            "adopt", root=root, record_path=source, runtime=runtime, operator="reviewer", replacement_path=transfer
        )
