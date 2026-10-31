"""Offline state-machine contracts shared with the native controller adapter."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

import pytest
from scripts import child_staging_maintenance as tool
from tests.unit.test_child.test_staging_maintenance_controller import native_config


class FakeRuntime:
    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []
        for index, service in enumerate(
            [
                "gateway",
                "backend",
                "frontend",
                "scheduler",
                "worker",
                "refinement-monitor",
                "postgres",
                "redis",
                "production",
            ]
        ):
            stage = service != "production"
            self.items.append(
                {
                    "id": f"{index + 1:064x}",
                    "name": f"astrotype-staging-{service}-1" if stage else "protected-edge",
                    "project": "astrotype-staging" if stage else "unrelated",
                    "service": service,
                    "image": f"sha256:{index + 100:064x}",
                    "running": True,
                    "started_at": "2026-10-31T00:00:00Z",
                    "restart": {"Name": "unless-stopped", "MaximumRetryCount": 0},
                    "networks": {"stage-private": {"ip": f"172.25.0.{index + 2}", "aliases": [service]}},
                    "ports": {},
                    "command_sha256": "a" * 64,
                }
            )
        self.current = native_config()
        self.etag = "1"
        self.mutations: list[str] = []
        self.fail_after: str | None = None
        self.evidence: dict[str, Any] = {
            "nodes": {
                "celery@worker": {
                    "ping": {"ok": "pong"},
                    "queues": ["celery"],
                    "registered": sorted(tool.TASKS),
                    "active": [],
                    "reserved": [],
                    "scheduled": [],
                },
                "celery@monitor": {
                    "ping": {"ok": "pong"},
                    "queues": ["birth-data-monitor"],
                    "registered": sorted(tool.TASKS),
                    "active": [],
                    "reserved": [],
                    "scheduled": [],
                },
            },
            "discovered_nodes": ["celery@monitor", "celery@worker"],
            "http_inflight": 0,
            "broker": {"queues": ["birth-data-monitor", "celery"], "pending": 0, "unacked": 0},
            "durable": {"tables": sorted(tool.TABLES), "nonterminal": 0, "unknown": 0},
        }

    def inventory(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self.items)

    def config(self, gateway: str) -> tuple[dict[str, Any], str]:
        assert gateway == self.items[0]["id"]
        return copy.deepcopy(self.current), self.etag

    def validate(self, gateway: str, config: dict[str, Any]) -> None:
        assert gateway == self.items[0]["id"]
        assert config["apps"]

    def load(self, gateway: str, config: dict[str, Any], etag: str) -> None:
        assert gateway == self.items[0]["id"]
        if etag != self.etag:
            raise ValueError("CAS")
        self.current = copy.deepcopy(config)
        self.etag = str(int(self.etag) + 1)
        self.mutations.append("load")
        if self.fail_after == "load":
            self.fail_after = None
            raise TimeoutError("unknown result, sensitive remote output")

    def restart_policy(self, identity: str, policy: dict[str, Any]) -> None:
        item = next(i for i in self.items if i["id"] == identity)
        assert item["service"] in {"gateway", "scheduler"} and item["project"] == "astrotype-staging"
        item["restart"] = copy.deepcopy(policy)
        self.mutations.append("restart")

    def running(self, identity: str, value: bool) -> None:
        item = next(i for i in self.items if i["id"] == identity)
        assert item["service"] == "scheduler" and item["project"] == "astrotype-staging"
        item["running"] = value
        self.mutations.append("start" if value else "stop")
        if self.fail_after == "stop":
            self.fail_after = None
            raise TimeoutError("lost response")

    def probe(self, backend: str, nodes: dict[str, Any]) -> dict[str, Any]:
        assert backend == self.items[1]["id"] and len(nodes) == 2
        return copy.deepcopy(self.evidence)


def record(runtime: FakeRuntime) -> dict[str, Any]:
    return {
        "version": 1,
        "run_id": "qualification-01",
        "approved": True,
        "environment": "staging",
        "project": "astrotype-staging",
        "approver": "owner",
        "operator": "reviewer",
        "authority": "staging-only native-mock maintenance authorized",
        "application_sha": "4f104c8c6e6d297f99b382684ed8e62ebee7da03",
        "operator_sha": "b" * 40,
        "expires_at": 9999999999,
        "inventory": runtime.inventory(),
        "nodes": {
            "celery@worker": {"service": "worker", "queues": ["celery"]},
            "celery@monitor": {"service": "refinement-monitor", "queues": ["birth-data-monitor"]},
        },
        "assertions": {key: True for key in tool.ASSERTIONS},
        "producer_paths": {
            key: "reviewed exact operational path and exclusion owner"
            for key in {
                "public_gateway",
                "private_api",
                "shared_edge_api",
                "host_api",
                "direct_broker",
                "operator_scripts",
            }
        },
        "controller_sha256": __import__("hashlib").sha256(Path(tool.__file__).read_bytes()).hexdigest(),
        "probe_sha256": __import__("hashlib").sha256(tool.PROBE_PATH.read_bytes()).hexdigest(),
        "additional_stage_services": [],
    }


def setup(tmp_path: Path, runtime: FakeRuntime) -> tuple[Path, Path]:
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    source = root / "approved.json"
    source.write_text(json.dumps(record(runtime)))
    source.chmod(0o600)
    return root, source


def call(root: Path, source: Path, runtime: FakeRuntime, action: str) -> dict[str, Any]:
    return tool.run(action, root=root, record_path=source, runtime=runtime, operator="reviewer")


def test_exclusive_checkpoint_creation_syncs_file_and_parent_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import stat

    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    synced: list[bool] = []
    monkeypatch.setattr(os, "fsync", lambda fd: synced.append(stat.S_ISDIR(os.fstat(fd).st_mode)))
    tool.exclusive(root / "claim.json", {"owned": True})
    assert synced == [False, True]


@pytest.mark.parametrize("deadline", [float("nan"), float("inf")])
def test_approval_window_requires_finite_deadline(deadline: float) -> None:
    data = record(FakeRuntime())
    data["expires_at"] = deadline
    with pytest.raises(ValueError):
        tool.validate_record(data)


def test_named_paths_and_executable_source_hashes_are_mandatory() -> None:
    data = record(FakeRuntime())
    tool.validate_record(data)
    data["controller_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        tool.validate_record(data)


def test_full_freeze_double_drain_signed_decision_exact_restore(tmp_path: Path) -> None:
    runtime = FakeRuntime()
    original = runtime.inventory()
    original_config = copy.deepcopy(runtime.current)
    root, source = setup(tmp_path, runtime)
    assert call(root, source, runtime, "preflight")["phase"] == "PREFLIGHT"
    assert not runtime.mutations
    assert call(root, source, runtime, "freeze")["phase"] == "FROZEN"
    assert tool.read_private(root / "qualification-01" / "scheduler.compose.json") == {
        "services": {"scheduler": {"restart": "no"}}
    }
    assert runtime.items[3]["running"] is False
    assert runtime.items[4]["running"] and runtime.items[5]["running"]
    result = call(root, source, runtime, "drain")
    assert result["phase"] == "DRAIN_CONFIRMED" and result["signature"]
    assert result["operator"] == "reviewer" and result["checks"] == 2
    assert call(root, source, runtime, "restore")["phase"] == "RESTORED"
    assert runtime.inventory() == original
    assert runtime.current == original_config
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in (root / "qualification-01").iterdir())


def test_freeze_reentry_and_lost_responses_read_back_without_replay(tmp_path: Path) -> None:
    runtime = FakeRuntime()
    root, source = setup(tmp_path, runtime)
    runtime.fail_after = "load"
    call(root, source, runtime, "freeze")
    before = list(runtime.mutations)
    call(root, source, runtime, "freeze")
    assert runtime.mutations == before
    call(root, source, runtime, "restore")
    before = list(runtime.mutations)
    call(root, source, runtime, "restore")
    assert runtime.mutations == before


@pytest.mark.parametrize("bad", ["production", "project", "missing", "node", "assertion", "expiry"])
def test_unsafe_record_denied_before_mutation(tmp_path: Path, bad: str) -> None:
    runtime = FakeRuntime()
    root, source = setup(tmp_path, runtime)
    data = json.loads(source.read_text())
    if bad == "production":
        data["inventory"][0]["name"] = "production-gateway"
    elif bad == "project":
        data["project"] = "production"
    elif bad == "missing":
        data["inventory"].pop()
    elif bad == "node":
        data["nodes"].pop("celery@monitor")
    elif bad == "assertion":
        data["assertions"]["direct_producers_excluded"] = False
    else:
        data["expires_at"] = 1
    source.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        call(root, source, runtime, "freeze")
    assert not runtime.mutations


@pytest.mark.parametrize(
    "bad", ["missing_node", "extra_node", "work", "broker", "unacked", "unknown", "durable", "queue", "task"]
)
def test_drain_requires_complete_live_evidence(tmp_path: Path, bad: str) -> None:
    runtime = FakeRuntime()
    root, source = setup(tmp_path, runtime)
    call(root, source, runtime, "freeze")
    if bad == "missing_node":
        runtime.evidence["nodes"].pop("celery@monitor")
    elif bad == "extra_node":
        runtime.evidence["discovered_nodes"].append("unknown@extra")
    elif bad == "work":
        runtime.evidence["nodes"]["celery@worker"]["active"] = [{"id": "accepted"}]
    elif bad in {"broker", "unacked"}:
        runtime.evidence["broker"]["pending" if bad == "broker" else "unacked"] = 1
    elif bad in {"unknown", "durable"}:
        runtime.evidence["durable"]["unknown" if bad == "unknown" else "nonterminal"] = 1
    elif bad == "queue":
        runtime.evidence["nodes"]["celery@worker"]["queues"].append("forgotten")
    else:
        runtime.evidence["nodes"]["celery@worker"]["registered"].append("unknown.task")
    with pytest.raises(ValueError):
        call(root, source, runtime, "drain")
    assert call(root, source, runtime, "status")["phase"] != "DRAIN_CONFIRMED"
    assert runtime.items[4]["running"] and runtime.items[5]["running"]


def test_changed_scheduler_hold_overlay_blocks_transition_without_docker_mutation(tmp_path: Path) -> None:
    runtime = FakeRuntime()
    root, source = setup(tmp_path, runtime)
    call(root, source, runtime, "freeze")
    (root / "qualification-01" / "scheduler.compose.json").write_text('{"services":{"scheduler":{"restart":"always"}}}')
    before = list(runtime.mutations)
    with pytest.raises(ValueError):
        call(root, source, runtime, "drain")
    assert runtime.mutations == before


def test_http_request_already_accepted_before_freeze_must_finish(tmp_path: Path) -> None:
    runtime = FakeRuntime()
    root, source = setup(tmp_path, runtime)
    runtime.evidence["http_inflight"] = 1
    call(root, source, runtime, "freeze")
    before = list(runtime.mutations)
    with pytest.raises(ValueError):
        call(root, source, runtime, "drain")
    assert runtime.mutations == before


def test_expired_decision_status_never_republishes_live_drain(tmp_path: Path) -> None:
    runtime = FakeRuntime()
    root, source = setup(tmp_path, runtime)
    call(root, source, runtime, "freeze")
    call(root, source, runtime, "drain")
    status = call(root, source, runtime, "status")
    assert status["phase"] != "DRAIN_CONFIRMED" and not status["drain_confirmed"]


def test_approved_app_identity_adoption_keeps_gateway_frozen_and_restores_only_owned_scheduler(tmp_path: Path) -> None:
    runtime = FakeRuntime()
    root, source = setup(tmp_path, runtime)
    original = copy.deepcopy(runtime.current)
    call(root, source, runtime, "freeze")
    call(root, source, runtime, "drain")
    for item in runtime.items:
        if item["service"] in {"backend", "worker", "refinement-monitor", "frontend"}:
            item["image"] = "sha256:" + "f" * 64
            item["id"] = f"{int(item['id'], 16) + 1000:064x}"
    runtime.items[3]["networks"]["stage-private"]["ip"] = ""
    replacement = record(runtime)
    replacement["authority"] = "explicit source refresh identity transfer, retain frozen gateway and paused scheduler"
    approved = root / "transfer.json"
    approved.write_text(json.dumps(replacement))
    approved.chmod(0o600)
    result = tool.run(
        "adopt", root=root, record_path=source, runtime=runtime, operator="reviewer", replacement_path=approved
    )
    assert result["phase"] == "FROZEN"
    assert runtime.current != original and not runtime.items[3]["running"]
    call(root, source, runtime, "drain")
    call(root, source, runtime, "restore")
    assert runtime.current == original and runtime.items[3]["running"]


@pytest.mark.parametrize("was_running", [False, True])
@pytest.mark.parametrize("approved", [False, True])
def test_new_scheduler_requires_explicit_owned_resume_transfer(
    tmp_path: Path, was_running: bool, approved: bool
) -> None:
    runtime = FakeRuntime()
    runtime.items[3]["running"] = was_running
    root, source = setup(tmp_path, runtime)
    call(root, source, runtime, "freeze")
    call(root, source, runtime, "drain")
    old_id = runtime.items[3]["id"]
    runtime.items[3]["id"] = "f" * 64
    replacement = record(runtime)
    if approved:
        replacement["scheduler_transfer"] = {"old_id": old_id, "new_id": "f" * 64, "approved_resume_owned_state": True}
    transfer = root / "transfer.json"
    tool.exclusive(transfer, replacement)
    before = list(runtime.mutations)
    if not approved:
        with pytest.raises(ValueError):
            tool.run(
                "adopt", root=root, record_path=source, runtime=runtime, operator="reviewer", replacement_path=transfer
            )
        assert runtime.mutations == before
    else:
        tool.run(
            "adopt", root=root, record_path=source, runtime=runtime, operator="reviewer", replacement_path=transfer
        )
        call(root, source, runtime, "restore")
        assert runtime.items[3]["id"] == "f" * 64 and runtime.items[3]["running"] == was_running
        assert ("start" in runtime.mutations) == was_running


def test_adoption_cannot_bless_protected_or_gateway_drift(tmp_path: Path) -> None:
    runtime = FakeRuntime()
    root, source = setup(tmp_path, runtime)
    call(root, source, runtime, "freeze")
    call(root, source, runtime, "drain")
    runtime.items[-1]["image"] = "changed"
    approved = root / "transfer.json"
    approved.write_text(json.dumps(record(runtime)))
    approved.chmod(0o600)
    before = list(runtime.mutations)
    with pytest.raises(ValueError):
        tool.run(
            "adopt", root=root, record_path=source, runtime=runtime, operator="reviewer", replacement_path=approved
        )
    assert before == runtime.mutations


def test_stale_config_and_protected_inventory_drift_never_overwritten(tmp_path: Path) -> None:
    runtime = FakeRuntime()
    root, source = setup(tmp_path, runtime)
    call(root, source, runtime, "freeze")
    runtime.current["unexpected"] = "another operator"
    before = list(runtime.mutations)
    with pytest.raises(ValueError):
        call(root, source, runtime, "restore")
    assert runtime.mutations == before
    del runtime.current["unexpected"]
    runtime.items[-1]["image"] = "changed"
    with pytest.raises(ValueError):
        call(root, source, runtime, "restore")
    assert runtime.mutations == before


def test_scheduler_auto_restart_is_disabled_until_exact_restore(tmp_path: Path) -> None:
    runtime = FakeRuntime()
    root, source = setup(tmp_path, runtime)
    original_policy = copy.deepcopy(runtime.items[3]["restart"])
    call(root, source, runtime, "freeze")
    assert runtime.items[3]["restart"] == tool.NO_RESTART
    call(root, source, runtime, "restore")
    assert runtime.items[3]["restart"] == original_policy


def test_previously_stopped_scheduler_not_started(tmp_path: Path) -> None:
    runtime = FakeRuntime()
    runtime.items[3]["running"] = False
    root, source = setup(tmp_path, runtime)
    call(root, source, runtime, "freeze")
    call(root, source, runtime, "restore")
    assert "start" not in runtime.mutations


def test_interrupted_checkpoint_claim_is_recovered_before_reentry(tmp_path: Path) -> None:
    runtime = FakeRuntime()
    root, source = setup(tmp_path, runtime)
    call(root, source, runtime, "freeze")
    (root / "owner.json").unlink()
    call(root, source, runtime, "freeze")
    assert tool.read_private(root / "owner.json")["run_id"] == "qualification-01"


def test_lock_and_durable_owner_exclude_competing_operator_runs(tmp_path: Path) -> None:
    import fcntl

    runtime = FakeRuntime()
    root, source = setup(tmp_path, runtime)
    lock = os.open(root / "controller.lock", os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):
            call(root, source, runtime, "freeze")
        assert not runtime.mutations
    finally:
        os.close(lock)
    call(root, source, runtime, "freeze")
    other = json.loads(source.read_text())
    other["run_id"] = "competing-run"
    second = root / "second.json"
    second.write_text(json.dumps(other))
    second.chmod(0o600)
    before = list(runtime.mutations)
    with pytest.raises(ValueError):
        call(root, second, runtime, "freeze")
    assert before == runtime.mutations


def test_ambiguous_operation_is_reconciled_before_owned_restore_without_replay(tmp_path: Path) -> None:
    runtime = FakeRuntime()
    root, source = setup(tmp_path, runtime)
    original_config = copy.deepcopy(runtime.current)
    real_load = runtime.load
    failed = False

    def unknown_load(gateway: str, config: dict[str, Any], etag: str) -> None:
        nonlocal failed
        failed = True
        # A lost response where the operation has not settled: no immediate replay.
        raise TimeoutError("private diagnostic")

    runtime.load = unknown_load  # type: ignore[method-assign]
    with pytest.raises(ValueError):
        call(root, source, runtime, "freeze")
    assert failed
    before = list(runtime.mutations)
    with pytest.raises(ValueError):
        call(root, source, runtime, "freeze")
    assert before == runtime.mutations
    # Simulate delayed completion observed after connection loss, not a new call.
    runtime.current = tool.maintenance_config(original_config)
    runtime.etag = "2"
    runtime.load = real_load  # type: ignore[method-assign]
    call(root, source, runtime, "restore")
    assert runtime.current == original_config
    assert runtime.mutations.count("load") == 1  # restoration only


def test_scheduler_network_release_during_stop_does_not_allow_topology_drift(tmp_path: Path) -> None:
    runtime = FakeRuntime()
    root, source = setup(tmp_path, runtime)
    real_running = runtime.running

    def release_ip(identity: str, value: bool) -> None:
        real_running(identity, value)
        runtime.items[3]["networks"]["stage-private"]["ip"] = "172.25.0.240" if value else ""
        if value:
            runtime.items[3]["started_at"] = "2026-10-31T01:00:00Z"

    runtime.running = release_ip  # type: ignore[method-assign]
    call(root, source, runtime, "freeze")
    call(root, source, runtime, "restore")
    assert runtime.items[3]["running"]


def test_completed_checkpoint_with_lost_claim_cleanup_is_released_idempotently(tmp_path: Path) -> None:
    runtime = FakeRuntime()
    root, source = setup(tmp_path, runtime)
    call(root, source, runtime, "freeze")
    claim = tool.read_private(root / "owner.json")
    call(root, source, runtime, "restore")
    tool.exclusive(root / "owner.json", claim)  # Crash after RESTORED checkpoint, before durable unlink.
    before = list(runtime.mutations)
    call(root, source, runtime, "restore")
    assert not (root / "owner.json").exists() and runtime.mutations == before


def test_completed_restore_cannot_reclaim_later_unowned_scheduler_stop(tmp_path: Path) -> None:
    runtime = FakeRuntime()
    root, source = setup(tmp_path, runtime)
    call(root, source, runtime, "freeze")
    call(root, source, runtime, "restore")
    runtime.items[3]["running"] = False  # A later operator owns this stop.
    before = list(runtime.mutations)
    with pytest.raises(ValueError):
        call(root, source, runtime, "restore")
    assert runtime.mutations == before


@pytest.mark.parametrize("action", ["freeze", "drain"])
def test_completed_run_cannot_be_reopened_or_lose_restored_checkpoint(tmp_path: Path, action: str) -> None:
    runtime = FakeRuntime()
    root, source = setup(tmp_path, runtime)
    call(root, source, runtime, "freeze")
    call(root, source, runtime, "restore")
    before = list(runtime.mutations)
    with pytest.raises(ValueError):
        call(root, source, runtime, action)
    assert call(root, source, runtime, "status")["phase"] == "RESTORED"
    assert runtime.mutations == before


def test_symlink_or_public_checkpoint_rejected_before_transport(tmp_path: Path) -> None:
    runtime = FakeRuntime()
    root, source = setup(tmp_path, runtime)
    link = root / "link.json"
    link.symlink_to(source)
    with pytest.raises(ValueError):
        call(root, link, runtime, "freeze")
    os.chmod(root, 0o755)  # noqa: S103 -- negative public-directory test
    with pytest.raises(ValueError):
        call(root, source, runtime, "freeze")
    assert not runtime.mutations
