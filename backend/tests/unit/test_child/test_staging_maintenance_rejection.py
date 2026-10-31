"""Definitive no-dispatch recovery; all transports are offline fakes."""

from __future__ import annotations

import copy
import json
import shlex
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from scripts import child_staging_maintenance as tool
from tests.unit.test_child.test_staging_maintenance_lifecycle import FakeRuntime, call, setup


def test_native_scheduler_precheck_rejection_recovers_exactly_without_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = FakeRuntime()
    original = runtime.inventory()
    original_config = copy.deepcopy(runtime.current)
    root, source = setup(tmp_path, runtime)
    dispatched: list[list[str]] = []

    def command(args: list[str], *, payload: str | None = None) -> str:
        dispatched.append(args)
        assert args[1] == "inspect"
        raise RuntimeError("read-only inspect denied; private diagnostic")

    native = tool.DockerRuntime(command)
    monkeypatch.setattr(runtime, "running", native.running)
    with pytest.raises(ValueError):
        call(root, source, runtime, "freeze")
    assert runtime.current != original_config
    frozen_routes = runtime.current["apps"]["http"]["servers"]["srv0"]["routes"][0]["handle"][2]["routes"]
    original_routes = original_config["apps"]["http"]["servers"]["srv0"]["routes"][0]["handle"][2]["routes"]
    assert frozen_routes[0] == original_routes[0]  # unconditional Basic Auth remains first
    assert frozen_routes[1]["handle"][0]["status_code"] == 503
    state = tool.load_state(root / "qualification-01")
    assert state["intent"] is None
    assert state["phase"] == "RECOVERY_REQUIRED"
    rejection = state["history"][-1]
    assert rejection["operation"] == "pause-scheduler"
    assert rejection["outcome"] == "not-dispatched"
    evidence = rejection["evidence"]
    assert evidence["run_id"] == "qualification-01"
    assert evidence["record_sha256"] == tool.digest(tool.read_private(source))
    assert len(evidence["attempt_id"]) == 32
    assert evidence["action"] == "pause-scheduler"
    assert evidence["target"] == {"id": original[3]["id"], "running": False}
    assert evidence["prestate"]["running"] is True
    assert evidence["prestate"]["restart"] == tool.NO_RESTART
    assert evidence["prestate"]["id"] == original[3]["id"]
    assert evidence["proof"] == "scheduler-precheck-rejected"
    before = list(runtime.mutations)
    for action in ("freeze", "drain"):
        with pytest.raises(ValueError):
            call(root, source, runtime, action)
    assert runtime.mutations == before
    assert call(root, source, runtime, "status")["phase"] == "RECOVERY_REQUIRED"
    assert call(root, source, runtime, "restore")["phase"] == "RESTORED"
    assert runtime.inventory() == original
    assert runtime.current == original_config
    assert not (root / "owner.json").exists()
    assert all(args[1] == "inspect" for args in dispatched)
    assert "start" not in runtime.mutations and "stop" not in runtime.mutations
    assert tool.load_state(root / "qualification-01")["history"][3] == rejection


@pytest.mark.parametrize("launch_error", [FileNotFoundError, PermissionError])
def test_native_client_launch_failure_is_proven_not_dispatched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, launch_error: type[OSError]
) -> None:
    runtime = FakeRuntime()
    original = runtime.inventory()
    root, source = setup(tmp_path, runtime)
    identity = runtime.items[3]["id"]
    commands: list[list[str]] = []

    def launch(args: list[str], **kwargs: object) -> SimpleNamespace:
        commands.append(args)
        if args[1] == "inspect":
            return SimpleNamespace(
                returncode=0,
                stdout=json.dumps(
                    [
                        {
                            "Id": identity,
                            "Name": "/astrotype-staging-scheduler-1",
                            "Config": {
                                "Labels": {
                                    "com.docker.compose.project": tool.PROJECT,
                                    "com.docker.compose.service": "scheduler",
                                }
                            },
                        }
                    ]
                ).encode(),
            )
        assert args == ["docker", "stop", "-t", "-1", identity]
        raise launch_error("client exec rejected")

    monkeypatch.setattr(subprocess, "run", launch)
    monkeypatch.setattr(runtime, "running", tool.DockerRuntime().running)
    with pytest.raises(ValueError):
        call(root, source, runtime, "freeze")
    state = tool.load_state(root / "qualification-01")
    assert state["intent"] is None
    assert state["history"][-1]["evidence"]["proof"] == "docker-client-not-started"
    assert call(root, source, runtime, "restore")["phase"] == "RESTORED"
    assert runtime.inventory() == original
    assert len(commands) == 2


@pytest.mark.parametrize("failure", ["nonzero", "timeout", "runtime", "unclassified-file-error"])
def test_unchanged_scheduler_after_dispatch_error_never_proves_rejection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    runtime = FakeRuntime()
    original_config = copy.deepcopy(runtime.current)
    root, source = setup(tmp_path, runtime)
    commands: list[list[str]] = []
    native = tool.DockerRuntime()
    monkeypatch.setattr(native, "require", lambda identity, service: {})

    def launch(args: list[str], **kwargs: object) -> SimpleNamespace:
        commands.append(args)
        if failure == "timeout":
            raise subprocess.TimeoutExpired(args, 180)
        if failure == "runtime":
            raise RuntimeError("generic error, may have dispatched")
        return SimpleNamespace(returncode=1, stdout=b"private daemon refusal")

    monkeypatch.setattr(subprocess, "run", launch)
    if failure == "unclassified-file-error":

        def untrusted_runner(args: list[str], *, payload: str | None = None) -> str:
            commands.append(args)
            raise FileNotFoundError("not evidence from subprocess launch boundary")

        native.command = untrusted_runner
    monkeypatch.setattr(runtime, "running", native.running)
    with pytest.raises(ValueError):
        call(root, source, runtime, "freeze")
    checkpoint = tool.load_state(root / "qualification-01")
    assert checkpoint["intent"] == "pause-scheduler"
    assert checkpoint["attempt"]["target"]["running"] is False
    assert not any(h["outcome"] == "not-dispatched" for h in checkpoint["history"])
    before = list(runtime.mutations)
    for action in ("freeze", "restore", "drain"):
        with pytest.raises(ValueError, match="unknown prior outcome"):
            call(root, source, runtime, action)
    assert tool.load_state(root / "qualification-01") == checkpoint
    assert runtime.mutations == before and len(commands) == 1
    assert runtime.current != original_config
    # The original stop later settles; reconcile, never send that stop again.
    runtime.items[3]["running"] = False
    monkeypatch.setattr(runtime, "running", FakeRuntime.running.__get__(runtime))
    assert call(root, source, runtime, "restore")["phase"] == "RESTORED"
    assert runtime.current == original_config and runtime.items[3]["running"]
    assert runtime.mutations.count("start") == 1 and "stop" not in runtime.mutations
    assert len(commands) == 1


def test_documented_native_rejection_recovery_invocations_execute_real_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    doc = Path(__file__).resolve().parents[4] / "docs/deployment/child-staging-maintenance.md"
    section = doc.read_text().split("### Definitive scheduler-stop rejection", 1)
    assert len(section) == 2, "publish the supported native rejection recovery invocation"
    commands = [
        shlex.split(line)
        for line in section[1].split("###", 1)[0].splitlines()
        if line.startswith('python3 "$MAINTENANCE"')
    ]
    assert [cmd[2] for cmd in commands] == ["status", "restore", "status"]
    runtime = FakeRuntime()
    original = runtime.inventory()
    original_config = copy.deepcopy(runtime.current)
    root, source = setup(tmp_path, runtime)

    def command(args: list[str], *, payload: str | None = None) -> str:
        assert args[1] == "inspect"
        raise RuntimeError("private diagnostic")

    native = tool.DockerRuntime(command)
    monkeypatch.setattr(runtime, "running", native.running)
    monkeypatch.setattr(tool, "CONTROLLER_ROOT", root)
    monkeypatch.setattr(tool, "DockerRuntime", lambda: runtime)
    args = ["--root", str(root), "--record", str(source), "--operator", "reviewer"]
    assert tool.main(["freeze", *args]) == 1
    for cmd in commands:
        values = {"$MAINTENANCE_RECORD": str(source), "$MAINTENANCE_OPERATOR": "reviewer"}
        argv = [values.get(arg, arg) for arg in cmd[2:]]
        assert tool.main([*argv, "--root", str(root)]) == 0
    assert runtime.inventory() == original and runtime.current == original_config
    assert not (root / "owner.json").exists()
    assert "private diagnostic" not in capsys.readouterr().out


@pytest.mark.parametrize("boundary", ["legacy", "checkpoint-crash"])
def test_missing_durable_native_proof_never_releases_unknown_intent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, boundary: str
) -> None:
    runtime = FakeRuntime()
    root, source = setup(tmp_path, runtime)
    native = tool.DockerRuntime(lambda args, payload=None: (_ for _ in ()).throw(RuntimeError("inspect failed")))
    monkeypatch.setattr(runtime, "running", native.running)
    real_save = tool.save_state

    def save(directory: Path, state: dict[str, Any]) -> None:
        if state["phase"] == "RECOVERY_REQUIRED":
            raise OSError("crash before durable rejection checkpoint")
        real_save(directory, state)

    monkeypatch.setattr(tool, "save_state", save)
    with pytest.raises(OSError):
        call(root, source, runtime, "freeze")
    checkpoint = tool.load_state(root / "qualification-01")
    assert checkpoint["intent"] == "pause-scheduler"
    if boundary == "legacy":
        checkpoint.pop("attempt")  # pre-feature journal has no native proof
        real_save(root / "qualification-01", checkpoint)
    before = list(runtime.mutations)
    with pytest.raises(ValueError, match="unknown prior outcome"):
        call(root, source, runtime, "restore")
    assert tool.load_state(root / "qualification-01") == checkpoint
    assert runtime.mutations == before
