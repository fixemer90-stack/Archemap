"""Security regressions; synthetic clocks and private local files only."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import pytest
from scripts import child_staging_maintenance as tool
from tests.unit.test_child.test_staging_maintenance_lifecycle import FakeRuntime, call, record


def test_drain_rechecks_approval_after_live_probes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = FakeRuntime()
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    data = record(runtime)
    data["expires_at"] = 1010
    source = root / "approved.json"
    tool.exclusive(source, data)
    clock = [1000.0]
    monkeypatch.setattr(time, "time", lambda: clock[0])
    call(root, source, runtime, "freeze")
    original_probe = runtime.probe

    def delayed_probe(backend: str, nodes: dict[str, object]) -> dict[str, object]:
        result = original_probe(backend, nodes)
        clock[0] += 6
        return result

    monkeypatch.setattr(runtime, "probe", delayed_probe)
    before = list(runtime.mutations)
    with pytest.raises(ValueError, match="approval window expired"):
        call(root, source, runtime, "drain")
    state = tool.load_state(root / data["run_id"])
    assert state["phase"] == "FROZEN" and state["decision"] is None
    assert runtime.mutations == before


@pytest.mark.parametrize("original_deadline,adopted_deadline", [(1010, None), (1020, 1005), (1005, 1020)])
def test_drain_validity_never_outlives_any_approval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, original_deadline: int, adopted_deadline: int | None
) -> None:
    runtime = FakeRuntime()
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    data = record(runtime)
    data["expires_at"] = original_deadline
    source = root / "approved.json"
    tool.exclusive(source, data)
    monkeypatch.setattr(time, "time", lambda: 1000.0)
    call(root, source, runtime, "freeze")
    if adopted_deadline is not None:
        directory = root / data["run_id"]
        state = tool.load_state(directory)
        state["adopted"] = {**data, "expires_at": adopted_deadline}
        tool.save_state(directory, state)
    result = call(root, source, runtime, "drain")
    assert result["at"] == 1000
    assert result["expires_at"] == min(1030, original_deadline, adopted_deadline or original_deadline)


def test_read_private_validates_opened_replacement_not_previous_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "approved.json"
    source.write_text('{"approved": true}')
    source.chmod(0o600)
    replacement = tmp_path / "replacement.json"
    replacement.write_text('{"approved": false}')
    replacement.chmod(0o644)  # Deliberately unsafe replacement.
    real_open = os.open
    replaced = False

    def replace_before_open(path: Any, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
        nonlocal replaced
        if Path(path).name == source.name and not replaced:
            replacement.replace(source)
            replaced = True
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", replace_before_open)
    with pytest.raises(ValueError, match="owner/mode/type"):
        tool.read_private(source)
    assert replaced


@pytest.mark.parametrize("mode", [0o777, 0o770, 0o1777])
@pytest.mark.parametrize("directory", [False, True])
def test_private_paths_reject_writable_ancestors(tmp_path: Path, mode: int, directory: bool) -> None:
    ancestor = tmp_path / "untrusted"
    ancestor.mkdir(mode=0o700)
    private = ancestor / "private"
    private.mkdir(mode=0o700)
    source = private / "approved.json"
    source.write_text("{}")
    source.chmod(0o600)
    ancestor.chmod(mode)
    try:
        with pytest.raises(ValueError, match="ancestor"):
            tool.private_path(private if directory else source, directory=directory)
    finally:
        ancestor.chmod(0o700)


@pytest.mark.parametrize("component", ["file", "parent"])
def test_private_reads_reject_symlinks_in_every_component(tmp_path: Path, component: str) -> None:
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    tool.exclusive(private / "approved.json", {"approved": True})
    if component == "file":
        source = private / "link.json"
        source.symlink_to(private / "approved.json")
    else:
        link = tmp_path / "link"
        link.symlink_to(private, target_is_directory=True)
        source = link / "approved.json"
    with pytest.raises(ValueError):
        tool.read_private(source)


@pytest.mark.parametrize("kind", ["hardlink", "fifo", "directory", "symlink"])
def test_opened_replacement_must_be_single_link_regular_private_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    source = tmp_path / "approved.json"
    tool.exclusive(source, {"approved": True})
    other = tmp_path / "other.json"
    tool.exclusive(other, {"approved": False})
    real_open = os.open
    replaced = False

    def replace_before_open(path: Any, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
        nonlocal replaced
        if Path(path).name == source.name and not replaced:
            replaced = True
            source.unlink()
            if kind == "hardlink":
                os.link(other, source)
            elif kind == "fifo":
                os.mkfifo(source, 0o600)
            elif kind == "directory":
                source.mkdir(mode=0o700)
            else:
                source.symlink_to(other)
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", replace_before_open)
    with pytest.raises(ValueError):
        tool.read_private(source)
    assert replaced


@pytest.mark.parametrize("target", ["ancestor", "file"])
def test_opened_inodes_require_trusted_owner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str) -> None:
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    source = private / "approved.json"
    tool.exclusive(source, {"approved": True})
    inode = (private if target == "ancestor" else source).stat().st_ino
    real_fstat = os.fstat

    def foreign_owner(fd: int) -> os.stat_result:
        info = real_fstat(fd)
        if info.st_ino == inode:
            values = list(info)
            values[4] = os.geteuid() + 1
            return os.stat_result(values)
        return info

    monkeypatch.setattr(os, "fstat", foreign_owner)
    with pytest.raises(ValueError, match="owner"):
        tool.read_private(source)


def test_read_private_pins_parent_before_pathname_replacement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    source = private / "approved.json"
    tool.exclusive(source, {"approved": True})
    other = tmp_path / "other"
    other.mkdir(mode=0o700)
    tool.exclusive(other / source.name, {"approved": False})
    real_open = os.open
    replaced = False

    def replace_parent(path: Any, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
        nonlocal replaced
        if Path(path).name == source.name and not replaced:
            replaced = True
            private.rename(tmp_path / "retained")
            private.symlink_to(other, target_is_directory=True)
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", replace_parent)
    assert tool.read_private(source) == {"approved": True}
    assert replaced


def test_normal_approved_private_files_remain_usable(tmp_path: Path) -> None:
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    source = private / "approved.json"
    expected = record(FakeRuntime())
    tool.exclusive(source, expected)
    tool.private_path(private, directory=True)
    assert tool.read_private(source) == expected
    tool.validate_record(tool.read_private(source))
