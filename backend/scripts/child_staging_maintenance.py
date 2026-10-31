"""Staging-only maintenance controller. Run locally on the approved Docker host.

No application imports; no production commands; no secrets in normal output.
See docs/deployment/child-staging-maintenance.md for the run-record contract.
"""

from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import hmac
import http.client
import io
import json
import math
import os
import re
import secrets
import stat
import subprocess
import time
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from typing import Any, Protocol

PROJECT = "astrotype-staging"
CONTROLLER_ROOT = Path("/opt/astrotype-staging/maintenance")
PRODUCER_PATHS = {"public_gateway", "private_api", "shared_edge_api", "host_api", "direct_broker", "operator_scripts"}
ASSERTIONS = {
    "exclusive_operator_window",
    "direct_producers_excluded",
    "all_network_paths_reviewed",
    "no_gateway_recreate_or_restart",
    "no_scheduler_recreate",
    "native_mock_no_payments",
    "all_task_families_reviewed",
    "protected_state_recorded",
}
TASKS = {
    "astrotype_v2.generate_natal_report",
    "career.generate_report",
    "career.monitor_pipeline",
    "child.generate_report",
    "child.reconcile_generations",
    "profiles.dispatch_birth_data_refinements",
    "profiles.monitor_birth_data_refinements",
    "reports.generate_pdf",
    "reports.generate_report_narrative",
    "workers.tasks.notifications.send_notification",
    "workers.tasks.notifications.send_bulk_notification",
    "workers.tasks.reconciliation.run_payment_reconciliation",
    "workers.tasks.renewals.check_and_renew_subscriptions",
}
TABLES = {
    "child_generations",
    "child_generation_events",
    "child_segment_generations",
    "career_generations",
    "career_segment_generations",
    "astrotype_v2_natal_report_generations",
    "astrotype_v2_report_segment_generations",
    "profile_birth_data_revisions",
    "report_narratives",
    "payments",
    "payment_webhooks",
}
BASE_SERVICES = {"gateway", "backend", "frontend", "scheduler", "worker", "refinement-monitor", "postgres", "redis"}
PASSIVE_SERVICES = {"prometheus", "alertmanager", "otel-collector"}
NO_RESTART = {"Name": "no", "MaximumRetryCount": 0}


class Runtime(Protocol):
    def inventory(self) -> list[dict[str, Any]]: ...
    def config(self, gateway: str) -> tuple[dict[str, Any], str]: ...
    def validate(self, gateway: str, config: dict[str, Any]) -> None: ...
    def load(self, gateway: str, config: dict[str, Any], etag: str) -> None: ...
    def restart_policy(self, identity: str, policy: dict[str, Any]) -> None: ...
    def running(self, identity: str, value: bool) -> None: ...
    def probe(self, backend: str, nodes: dict[str, Any]) -> dict[str, Any]: ...


def encoded(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(encoded(value)).hexdigest()


def _private_fd(path: Path, *, directory: bool = False) -> int:
    """Pin directories from /; validate the opened inode, not its pathname.

    Ancestors must be root/operator-owned and never group/world-writable, even
    sticky directories. Use a trusted operator scratch tree, not shared /tmp.
    """
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("private paths must be absolute without parent traversal")
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    fd = os.open("/", flags | os.O_DIRECTORY)
    try:
        for index, component in enumerate(path.parts[1:], start=1):
            ancestor = os.fstat(fd)
            if ancestor.st_uid not in {0, os.geteuid()} or stat.S_IMODE(ancestor.st_mode) & 0o022:
                raise ValueError("untrusted private path ancestor owner/mode")
            is_parent = index < len(path.parts) - 1
            child = os.open(component, flags | (os.O_DIRECTORY if is_parent or directory else 0), dir_fd=fd)
            os.close(fd)
            fd = child
        info = os.fstat(fd)
        expected = 0o700 if directory else 0o600
        correct_kind = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
        if not correct_kind or stat.S_IMODE(info.st_mode) != expected or info.st_uid != os.geteuid():
            raise ValueError("private owner/mode/type mismatch")
        if not directory and info.st_nlink != 1:
            raise ValueError("hardlinked private file")
        result, fd = fd, -1
        return result
    except OSError as exc:
        raise ValueError("private path cannot be opened without symlinks") from exc
    finally:
        if fd != -1:
            os.close(fd)


def private_path(path: Path, *, directory: bool = False) -> None:
    """Require trusted ancestors and a private, operator-owned target inode."""
    os.close(_private_fd(path, directory=directory))


def read_private(path: Path) -> Any:
    with os.fdopen(_private_fd(path)) as stream:
        return json.load(stream)


def exclusive(path: Path, value: Any) -> None:
    private_path(path.parent, directory=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(encoded(value))
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def save_state(directory: Path, state: dict[str, Any]) -> None:
    key = bytes.fromhex(read_private(directory / "key.json"))
    envelope = {"state": state, "signature": hmac.new(key, encoded(state), "sha256").hexdigest()}
    path = directory / "state.json"
    if path.exists() or path.is_symlink():
        private_path(path)
    temporary = directory / f"state-{secrets.token_hex(12)}.json"
    exclusive(temporary, envelope)
    os.replace(temporary, path)
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def load_state(directory: Path) -> dict[str, Any]:
    envelope = read_private(directory / "state.json")
    key = bytes.fromhex(read_private(directory / "key.json"))
    expected = hmac.new(key, encoded(envelope["state"]), "sha256").hexdigest()
    if not hmac.compare_digest(envelope["signature"], expected):
        raise ValueError("checkpoint signature mismatch")
    result: dict[str, Any] = envelope["state"]
    return result


def validate_record(record: dict[str, Any], *, recovery: bool = False) -> None:
    if (
        record.get("version") != 1
        or record.get("approved") is not True
        or record.get("environment") != "staging"
        or record.get("project") != PROJECT
    ):
        raise ValueError("only explicitly approved staging records accepted")
    for field in ("operator", "approver", "authority"):
        if not isinstance(record.get(field), str) or not record[field].strip():
            raise ValueError("missing approval identity")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", record.get("run_id", "")):
        raise ValueError("invalid run ID")
    if not all(re.fullmatch(r"[0-9a-f]{40}", record.get(key, "")) for key in ("application_sha", "operator_sha")):
        raise ValueError("exact source identities required")
    deadline = record.get("expires_at")
    try:
        if not isinstance(deadline, (int, float)) or isinstance(deadline, bool) or not math.isfinite(deadline):
            raise ValueError("finite explicit approval deadline required")
    except OverflowError as exc:
        raise ValueError("invalid approval deadline") from exc
    if not recovery and deadline <= time.time():
        raise ValueError("approval window expired")
    if set(record.get("assertions", {})) != ASSERTIONS or any(v is not True for v in record["assertions"].values()):
        raise ValueError("incomplete operational exclusion assertions")
    if (
        not isinstance(record.get("producer_paths"), dict)
        or set(record["producer_paths"]) != PRODUCER_PATHS
        or not all(isinstance(path, str) and path.strip() for path in record["producer_paths"].values())
    ):
        raise ValueError("all public/private/edge/host/broker/operator producer paths must be reviewed")
    for field, source in (("controller_sha256", Path(__file__)), ("probe_sha256", PROBE_PATH)):
        if record.get(field) != hashlib.sha256(source.read_bytes()).hexdigest():
            raise ValueError("executable source hash differs from approved operator artifact")
    inventory = record["inventory"]
    if not inventory or len({i["id"] for i in inventory}) != len(inventory):
        raise ValueError("duplicate/incomplete inventory")
    stage = [i for i in inventory if i["project"] == PROJECT]
    services = {i["service"] for i in stage}
    extras = set(record.get("additional_stage_services", []))
    if not BASE_SERVICES.issubset(services) or services != BASE_SERVICES | extras | (services & PASSIVE_SERVICES):
        raise ValueError("unreviewed staging service")
    if len(stage) != len(services):
        raise ValueError("replica topology requires explicit controller extension")
    for item in inventory:
        if not re.fullmatch(r"[0-9a-f]{64}", item["id"]):
            raise ValueError("full Docker IDs required")
        if item["project"] == PROJECT and item["name"] != f"{PROJECT}-{item['service']}-1":
            raise ValueError("staging name/project/service mismatch")
    nodes = record["nodes"]
    node_services = [n["service"] for n in nodes.values()]
    if set(node_services) != {"worker", "refinement-monitor"} | extras or len(node_services) != len(set(node_services)):
        raise ValueError("complete consumer/node inventory required")
    for node, spec in nodes.items():
        if not re.fullmatch(r"[A-Za-z0-9_.@-]{1,200}", node) or not spec["queues"]:
            raise ValueError("exact node and queues required")
        if not all(re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", q) for q in spec["queues"]):
            raise ValueError("unsupported queue")
    if not all(i["running"] for i in stage if i["service"] != "scheduler"):
        raise ValueError("required staging service not running")


def validate_evidence(evidence: dict[str, Any], nodes: dict[str, Any], *, empty: bool) -> None:
    if set(evidence["nodes"]) != set(nodes) or set(evidence["discovered_nodes"]) != set(nodes):
        raise ValueError("missing/extra Celery node reply")
    for node, spec in nodes.items():
        reply = evidence["nodes"][node]
        if reply["ping"] != {"ok": "pong"} or sorted(reply["queues"]) != sorted(spec["queues"]):
            raise ValueError("node readiness/queue mismatch")
        if set(reply["registered"]) != TASKS:
            raise ValueError("unreviewed task family registry")
        for kind in ("active", "reserved", "scheduled"):
            if not isinstance(reply[kind], list) or (empty and reply[kind]):
                raise ValueError("accepted work still present")
    queues = {q for spec in nodes.values() for q in spec["queues"]}
    if set(evidence["broker"]["queues"]) != queues or set(evidence["durable"]["tables"]) != TABLES:
        raise ValueError("incomplete broker/durable inventory")
    counts = [
        evidence["http_inflight"],
        evidence["broker"]["pending"],
        evidence["broker"]["unacked"],
        evidence["durable"]["nonterminal"],
        evidence["durable"]["unknown"],
    ]
    if any(type(n) is not int or n < 0 for n in counts) or (empty and any(counts)):
        raise ValueError("broker/durable work or unknown provider outcome")


def run(
    action: str, *, root: Path, record_path: Path, runtime: Runtime, operator: str, replacement_path: Path | None = None
) -> dict[str, Any]:
    """One serialized, durable operation. No automatic worker stop or retry loop."""
    private_path(root, directory=True)
    record = read_private(record_path)
    validate_record(record, recovery=action in {"restore", "status"})
    if operator != record["operator"]:
        raise ValueError("operator must match approved record")
    lock = root / "controller.lock"
    fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        private_path(lock)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        replacement = read_private(replacement_path) if replacement_path else None
        if bool(replacement_path) != (action == "adopt"):
            raise ValueError("replacement record only allowed for explicit adoption")
        return _locked(action, root, record, runtime, operator, replacement)
    finally:
        os.close(fd)


def _locked(
    action: str, root: Path, record: dict[str, Any], runtime: Runtime, operator: str, replacement: dict[str, Any] | None
) -> dict[str, Any]:
    directory = root / record["run_id"]
    claim = root / "owner.json"
    if (claim.exists() or claim.is_symlink()) and read_private(claim) != {
        "run_id": record["run_id"],
        "record_sha256": digest(record),
    }:
        raise ValueError("another maintenance run owns the controller")
    initial = record["inventory"]
    services = {i["service"]: i for i in initial if i["project"] == PROJECT}
    gateway, scheduler, backend = (services[s]["id"] for s in ("gateway", "scheduler", "backend"))
    restore_policy = copy.deepcopy(services["gateway"]["restart"])
    scheduler_policy = copy.deepcopy(services["scheduler"]["restart"])
    resume_scheduler = services["scheduler"]["running"]
    nodes = record["nodes"]

    def inventory_ok(*, owned: bool, initial_check: bool = False) -> list[dict[str, Any]]:
        observed = runtime.inventory()
        wanted = copy.deepcopy(initial)
        for entry in wanted:
            if entry["id"] == scheduler and not initial_check:
                actual = next(i for i in observed if i["id"] == scheduler)
                if set(entry["networks"]) != set(actual["networks"]) or any(
                    entry["networks"][n]["aliases"] != actual["networks"][n]["aliases"] for n in entry["networks"]
                ):
                    raise ValueError("scheduler network/alias drift")
                # Docker releases/reassigns endpoint addresses on a graceful stop/start.
                # Preserve network and alias inventory; only this owned IP may differ.
                for name in entry["networks"]:
                    entry["networks"][name]["ip"] = actual["networks"][name]["ip"]
                if "started_at" in entry:
                    entry["started_at"] = actual["started_at"]
            if entry["id"] == gateway:
                entry["restart"] = restore_policy
            if entry["id"] == scheduler:
                entry["running"] = resume_scheduler
                entry["restart"] = scheduler_policy
        if owned:
            for item in wanted:
                if item["id"] == gateway:
                    # Only controller-owned restart policy may differ.
                    item["restart"] = next(i for i in observed if i["id"] == gateway)["restart"]
                    if item["restart"] not in (NO_RESTART, restore_policy):
                        raise ValueError("gateway policy drift")
                if item["id"] == scheduler:
                    observed_item = next(i for i in observed if i["id"] == scheduler)
                    item["running"] = observed_item["running"]
                    item["restart"] = observed_item["restart"]
                    if item["restart"] not in (NO_RESTART, scheduler_policy):
                        raise ValueError("scheduler policy drift")
        if sorted(observed, key=lambda i: i["id"]) != sorted(wanted, key=lambda i: i["id"]):
            raise ValueError("live/protected inventory drift; reapproval required")
        return observed

    if not directory.exists() and action in {"status", "restore", "drain"}:
        raise ValueError("no owned checkpoint")
    if not directory.exists():
        inventory_ok(owned=False, initial_check=True)
        original, _etag = runtime.config(gateway)
        frozen = maintenance_config(original)
        runtime.validate(gateway, frozen)
        validate_evidence(runtime.probe(backend, record["nodes"]), record["nodes"], empty=False)
        if action == "preflight":
            return {"phase": "PREFLIGHT", "drain_confirmed": False, "record_sha256": digest(record)}
        if action != "freeze":
            raise ValueError("unsupported action")
        directory.mkdir(mode=0o700)
        exclusive(directory / "key.json", secrets.token_hex(32))
        exclusive(directory / "original.json", original)
        exclusive(directory / "frozen.json", frozen)
        exclusive(directory / "approved.json", record)
        exclusive(directory / "scheduler.compose.json", {"services": {"scheduler": {"restart": "no"}}})
        state: dict[str, Any] = {
            "phase": "PREPARED",
            "record_sha256": digest(record),
            "original_sha256": digest(original),
            "frozen_sha256": digest(frozen),
            "intent": None,
            "decision": None,
            "history": [],
        }
        save_state(directory, state)
        exclusive(claim, {"run_id": record["run_id"], "record_sha256": digest(record)})
    private_path(directory, directory=True)
    state = load_state(directory)
    if state["record_sha256"] != digest(record):
        raise ValueError("approved record changed")
    if state["phase"] == "RESTORED" and action not in {"status", "restore"}:
        raise ValueError("completed run cannot be reused")
    if state.get("adopted"):
        adopted = state["adopted"]
        initial = adopted["inventory"]
        nodes = adopted["nodes"]
        services = {i["service"]: i for i in initial if i["project"] == PROJECT}
        scheduler, backend = (services[s]["id"] for s in ("scheduler", "backend"))
    original, frozen = (read_private(directory / name) for name in ("original.json", "frozen.json"))
    if digest(original) != state["original_sha256"] or digest(frozen) != state["frozen_sha256"]:
        raise ValueError("frozen/original checkpoint changed")
    if read_private(directory / "scheduler.compose.json") != {"services": {"scheduler": {"restart": "no"}}}:
        raise ValueError("scheduler hold overlay changed")
    if state["phase"] != "RESTORED" and not claim.exists():
        # Recover interruption between checkpoint and durable claim creation.
        exclusive(claim, {"run_id": record["run_id"], "record_sha256": digest(record)})
    if action == "adopt":
        if replacement is None or state["intent"] is not None or not state["decision"]:
            raise ValueError("adoption requires a retained signed drain and no unknown operation")
        validate_record(replacement)
        if any(replacement[k] != record[k] for k in ("run_id", "operator", "operator_sha", "application_sha")):
            raise ValueError("identity transfer cannot change approved target/source/operator")
        observed = runtime.inventory()
        if sorted(replacement["inventory"], key=lambda i: i["id"]) != sorted(observed, key=lambda i: i["id"]):
            raise ValueError("replacement is not exact live inventory")
        changeable = {"backend", "frontend", "worker", "refinement-monitor"}
        old_scheduler = services["scheduler"]
        new_services = {i["service"]: i for i in observed if i["project"] == PROJECT}
        if new_services["scheduler"]["id"] != scheduler:
            transfer = replacement.get("scheduler_transfer")
            if transfer != {
                "old_id": scheduler,
                "new_id": new_services["scheduler"]["id"],
                "approved_resume_owned_state": True,
            }:
                raise ValueError("new scheduler lacks explicit ownership transfer")
            if new_services["scheduler"]["running"]:
                raise ValueError("replacement scheduler must be created stopped")
            changeable.add("scheduler")
        previous = copy.deepcopy(initial)
        for entry in previous:
            if entry["id"] == gateway:
                entry["restart"] = NO_RESTART
            if entry["id"] == old_scheduler["id"]:
                entry["running"] = False
                entry["restart"] = NO_RESTART
                if new_services["scheduler"]["id"] == old_scheduler["id"]:
                    actual = new_services["scheduler"]
                    if set(entry["networks"]) != set(actual["networks"]) or any(
                        entry["networks"][n]["aliases"] != actual["networks"][n]["aliases"] for n in entry["networks"]
                    ):
                        raise ValueError("scheduler topology changed during app transfer")
                    for network in entry["networks"]:
                        entry["networks"][network]["ip"] = actual["networks"][network]["ip"]
                    if "started_at" in entry:
                        entry["started_at"] = actual["started_at"]

        def fixed(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
            return sorted(
                [i for i in items if not (i["project"] == PROJECT and i["service"] in changeable)],
                key=lambda i: i["id"],
            )

        if fixed(previous) != fixed(observed) or runtime.config(gateway)[0] != frozen:
            raise ValueError("adoption cannot bless protected/gateway/data-service drift")
        if (
            new_services["scheduler"]["running"]
            or new_services["gateway"]["restart"] != NO_RESTART
            or new_services["scheduler"]["restart"] != NO_RESTART
        ):
            raise ValueError("producer freeze was lost during source recreation")
        validate_evidence(
            runtime.probe(new_services["backend"]["id"], replacement["nodes"]), replacement["nodes"], empty=True
        )
        state["adopted"] = replacement
        state["history"].append({"operation": "adopt", "record_sha256": digest(replacement), "at": time.time()})
        state["phase"] = "FROZEN"
        state["decision"] = None
        save_state(directory, state)
        return {"phase": "FROZEN", "drain_confirmed": False}
    inventory_ok(owned=True)
    current, etag = runtime.config(gateway)
    if current not in (original, frozen):
        raise ValueError("stale Caddy config; refusing overwrite")
    if state["phase"] == "RESTORED":
        # A completed run has released ownership; re-entry is read-only.
        # Later operator stops/policy/config changes must never be reclaimed.
        inventory_ok(owned=False)
        if current != original:
            raise ValueError("completed run no longer owns the loaded config")
        if claim.exists():
            claim.unlink()
            sync = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(sync)
            finally:
                os.close(sync)
        return {"phase": "RESTORED", "drain_confirmed": False}

    if state["intent"] and action != "status":
        pending = state["intent"]
        observed_scheduler = next(i for i in runtime.inventory() if i["id"] == scheduler)
        observed_gateway = next(i for i in runtime.inventory() if i["id"] == gateway)
        targets = {
            "disable-restart": observed_gateway["restart"] == NO_RESTART,
            "disable-scheduler-restart": observed_scheduler["restart"] == NO_RESTART,
            "restore-scheduler-restart": observed_scheduler["restart"] == scheduler_policy,
            "freeze-config": current == frozen,
            "pause-scheduler": not observed_scheduler["running"],
            "resume-scheduler": observed_scheduler["running"] == resume_scheduler,
            "restore-config": current == original,
            "restore-restart": observed_gateway["restart"] == restore_policy,
        }
        if not targets.get(pending, False):
            raise ValueError("unknown prior outcome not settled; do not replay or clear its checkpoint")
        state["history"].append({"operation": pending, "outcome": "reconciled", "at": time.time()})
        state["intent"] = None
        save_state(directory, state)

    def effect(name: str, operation: Callable[[], None], matches: Callable[[], bool]) -> None:
        if state["intent"] is not None:
            if state["intent"] != name or not matches():
                raise ValueError("unknown prior outcome; read back exact target, never replay blindly")
            state["intent"] = None
            state["history"].append({"operation": name, "outcome": "reconciled", "at": time.time()})
            save_state(directory, state)
            return
        state["intent"] = name
        state["decision"] = None
        save_state(directory, state)
        inventory_ok(owned=True)
        # A transport failure is ambiguous: exact readback, never automatic replay.
        with suppress(OSError, RuntimeError, ValueError, subprocess.SubprocessError, http.client.HTTPException):
            operation()
        if not matches():
            raise ValueError("operation not confirmed; retained intent blocks replay")
        inventory_ok(owned=True)
        state["intent"] = None
        state["history"].append({"operation": name, "outcome": "confirmed", "at": time.time()})
        save_state(directory, state)

    def item(identity: str) -> dict[str, Any]:
        return next(i for i in runtime.inventory() if i["id"] == identity)

    def frozen_ok() -> None:
        inventory_ok(owned=True)
        if (
            runtime.config(gateway)[0] != frozen
            or item(gateway)["restart"] != NO_RESTART
            or item(scheduler)["running"]
            or item(scheduler)["restart"] != NO_RESTART
        ):
            raise ValueError("producer freeze not intact")

    if action == "status":
        # Only the live double-probe action may publish DRAIN_CONFIRMED.
        result = {"phase": state["phase"], "intent": state["intent"], "drain_confirmed": False}
        if state["phase"] == "DRAIN_CONFIRMED":
            frozen_ok()
            result["phase"] = "FROZEN"
        return result
    if action == "freeze":
        if state["phase"] == "RESTORED":
            raise ValueError("completed run cannot be reused")
        if item(gateway)["restart"] != NO_RESTART or state["intent"] == "disable-restart":
            effect(
                "disable-restart",
                lambda: runtime.restart_policy(gateway, NO_RESTART),
                lambda: item(gateway)["restart"] == NO_RESTART,
            )
        if item(scheduler)["restart"] != NO_RESTART:
            effect(
                "disable-scheduler-restart",
                lambda: runtime.restart_policy(scheduler, NO_RESTART),
                lambda: item(scheduler)["restart"] == NO_RESTART,
            )
        if current != frozen or state["intent"] == "freeze-config":
            effect(
                "freeze-config",
                lambda: runtime.load(gateway, frozen, etag),
                lambda: runtime.config(gateway)[0] == frozen,
            )
        if item(scheduler)["running"] or state["intent"] == "pause-scheduler":
            effect("pause-scheduler", lambda: runtime.running(scheduler, False), lambda: not item(scheduler)["running"])
        frozen_ok()
        state["phase"] = "FROZEN"
        state["decision"] = None
    elif action == "drain":
        state["decision"] = None
        state["phase"] = "FROZEN"
        save_state(directory, state)
        for _ in range(2):
            frozen_ok()
            validate_evidence(runtime.probe(backend, nodes), nodes, empty=True)
        frozen_ok()
        issued_at = time.time()
        approval_deadline = min(record["expires_at"], (state.get("adopted") or record)["expires_at"])
        if approval_deadline <= issued_at:
            raise ValueError("approval window expired")
        decision = {
            "phase": "DRAIN_CONFIRMED",
            "operator": operator,
            "checks": 2,
            "at": issued_at,
            "expires_at": min(issued_at + 30, approval_deadline),
            "record_sha256": digest(record),
            "frozen_sha256": digest(frozen),
            "inventory_sha256": digest(initial),
            "nodes_sha256": digest(nodes),
            "effective_approval_sha256": digest(state.get("adopted") or record),
        }
        key = bytes.fromhex(read_private(directory / "key.json"))
        decision["signature"] = hmac.new(key, encoded(decision), "sha256").hexdigest()
        state["decision"] = decision
        state["phase"] = "DRAIN_CONFIRMED"
        save_state(directory, state)
        return decision
    elif action == "restore":
        # Keep ingress blocked until the scheduler's owned state is recovered.
        # Never start any worker, backend, DB, or previously stopped scheduler.
        if item(scheduler)["running"] != resume_scheduler or state["intent"] == "resume-scheduler":
            desired = resume_scheduler
            effect(
                "resume-scheduler",
                lambda: runtime.running(scheduler, desired),
                lambda: item(scheduler)["running"] == desired,
            )
        if current != original or state["intent"] == "restore-config":
            effect(
                "restore-config",
                lambda: runtime.load(gateway, original, etag),
                lambda: runtime.config(gateway)[0] == original,
            )
        policy = restore_policy
        if item(gateway)["restart"] != policy or state["intent"] == "restore-restart":
            effect(
                "restore-restart",
                lambda: runtime.restart_policy(gateway, policy),
                lambda: item(gateway)["restart"] == policy,
            )
        if item(scheduler)["restart"] != scheduler_policy:
            effect(
                "restore-scheduler-restart",
                lambda: runtime.restart_policy(scheduler, scheduler_policy),
                lambda: item(scheduler)["restart"] == scheduler_policy,
            )
        inventory_ok(owned=False)
        state["phase"] = "RESTORED"
        state["decision"] = None
        save_state(directory, state)
        if claim.exists():
            claim.unlink()
            sync = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(sync)
            finally:
                os.close(sync)
        return {"phase": "RESTORED", "drain_confirmed": False}
    else:
        raise ValueError("unsupported action")
    save_state(directory, state)
    return {"phase": state["phase"], "drain_confirmed": False}


PROBE_PATH = Path(__file__).with_name("child_staging_probe.py")


class Command(Protocol):
    def __call__(self, args: list[str], *, payload: str | None = None) -> str: ...


def command(args: list[str], *, payload: str | None = None) -> str:
    result = subprocess.run(  # noqa: S603
        args,
        input=payload.encode() if payload is not None else None,
        capture_output=True,
        timeout=180,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("Docker transport failed; no remote output printed")
    return result.stdout.decode()


class ResponseSocket:
    def __init__(self, raw: str) -> None:
        self.raw = raw.encode()

    def makefile(self, mode: str) -> io.BytesIO:
        return io.BytesIO(self.raw)


def admin_response(raw: str, *, require_etag: bool) -> tuple[str, str]:
    response = http.client.HTTPResponse(ResponseSocket(raw))  # type: ignore[arg-type]
    response.begin()
    if response.status != 200:
        raise ValueError("Caddy admin denied request; inspect privately")
    etag = response.getheader("Etag", "")
    if require_etag and not etag:
        raise ValueError("Caddy CAS Etag unavailable")
    return response.read().decode(), etag


class DockerRuntime:
    """Only exact verified stage IDs may receive exec/update/start/stop."""

    def __init__(self, runner: Command = command) -> None:
        self.command = runner

    def require(self, identity: str, service: str) -> dict[str, Any]:
        if not re.fullmatch(r"[0-9a-f]{64}", identity):
            raise ValueError("full container ID required")
        item: dict[str, Any] = json.loads(self.command(["docker", "inspect", identity]))[0]
        labels = item["Config"]["Labels"]
        if (
            item["Id"] != identity
            or item["Name"] != f"/{PROJECT}-{service}-1"
            or labels.get("com.docker.compose.project") != PROJECT
            or labels.get("com.docker.compose.service") != service
        ):
            raise ValueError("staging container identity mismatch")
        return item

    def inventory(self) -> list[dict[str, Any]]:
        identities = self.command(["docker", "ps", "-aq", "--no-trunc"]).split()
        if not identities or not all(re.fullmatch(r"[0-9a-f]{64}", i) for i in identities):
            raise ValueError("Docker inventory unavailable")
        items = json.loads(self.command(["docker", "inspect", *sorted(identities)]))
        output = []
        for item in items:
            labels = item["Config"].get("Labels") or {}
            output.append(
                {
                    "id": item["Id"],
                    "name": item["Name"].removeprefix("/"),
                    "project": labels.get("com.docker.compose.project", ""),
                    "service": labels.get("com.docker.compose.service", ""),
                    "image": item["Image"],
                    "running": item["State"]["Running"],
                    "started_at": item["State"]["StartedAt"],
                    "restart": item["HostConfig"]["RestartPolicy"],
                    "networks": {
                        name: {"ip": n["IPAddress"], "aliases": sorted(n.get("Aliases") or [])}
                        for name, n in item["NetworkSettings"]["Networks"].items()
                    },
                    "ports": item["HostConfig"].get("PortBindings") or {},
                    "command_sha256": digest([item["Config"].get("Entrypoint"), item["Config"].get("Cmd")]),
                    "mounts_sha256": digest(sorted(item["Mounts"], key=lambda m: m["Destination"])),
                }
            )
        return sorted(output, key=lambda i: i["id"])

    def admin(self, gateway: str, *, config: dict[str, Any] | None = None, etag: str = "") -> tuple[str, str]:
        self.require(gateway, "gateway")
        if "\r" in etag or "\n" in etag or (config is not None and not etag):
            raise ValueError("invalid Caddy CAS token")
        payload = encoded(config).decode() if config is not None else ""
        method = "POST" if config is not None else "GET"
        request = f"{method} /config/ HTTP/1.1\r\nHost: localhost:2019\r\nConnection: close\r\n"
        if config is not None:
            request += (
                f"If-Match: {etag}\r\nContent-Type: application/json\r\nContent-Length: {len(payload.encode())}\r\n"
            )
        request += "\r\n" + payload
        raw = self.command(
            ["docker", "exec", "-i", gateway, "sh", "-c", "nc -w 15 127.0.0.1 2019", "maintenance-admin"],
            payload=request,
        )
        return admin_response(raw, require_etag=config is None)

    def config(self, gateway: str) -> tuple[dict[str, Any], str]:
        body, etag = self.admin(gateway)
        return json.loads(body), etag

    def validate(self, gateway: str, config: dict[str, Any]) -> None:
        self.require(gateway, "gateway")
        self.command(
            ["docker", "exec", "-i", gateway, "caddy", "validate", "--config", "/dev/stdin"],
            payload=encoded(config).decode(),
        )

    def load(self, gateway: str, config: dict[str, Any], etag: str) -> None:
        self.admin(gateway, config=config, etag=etag)

    def restart_policy(self, identity: str, policy: dict[str, Any]) -> None:
        if not re.fullmatch(r"[0-9a-f]{64}", identity):
            raise ValueError("full staging identity required")
        info = json.loads(self.command(["docker", "inspect", identity]))[0]
        service = info["Config"]["Labels"].get("com.docker.compose.service")
        if service not in {"gateway", "scheduler"}:
            raise ValueError("only controller-owned producer/gateway restart policies allowed")
        self.require(identity, service)
        name = policy["Name"]
        retries = policy["MaximumRetryCount"]
        if name not in {"no", "always", "unless-stopped", "on-failure"} or type(retries) is not int or retries < 0:
            raise ValueError("unsupported restart policy")
        value = f"on-failure:{retries}" if name == "on-failure" and retries else name
        self.command(["docker", "update", f"--restart={value}", identity])

    def running(self, identity: str, value: bool) -> None:
        self.require(identity, "scheduler")
        args = ["docker", "start", identity] if value else ["docker", "stop", "-t", "-1", identity]
        self.command(args)

    def probe(self, backend: str, nodes: dict[str, Any]) -> dict[str, Any]:
        self.require(backend, "backend")
        inventory = self.inventory()
        for node, spec in nodes.items():
            consumers = [i for i in inventory if i["project"] == PROJECT and i["service"] == spec["service"]]
            if len(consumers) != 1:
                raise ValueError("ambiguous consumer container")
            consumer = self.require(consumers[0]["id"], spec["service"])
            if "@" not in node or node.rsplit("@", 1)[1] != consumer["Config"]["Hostname"]:
                raise ValueError("node name does not belong to the exact inventoried consumer")
        endpoints = {}
        for service in ("postgres", "redis"):
            matches = [i for i in inventory if i["project"] == PROJECT and i["service"] == service]
            if len(matches) != 1:
                raise ValueError("ambiguous data service")
            endpoints[service] = [v["ip"] for v in matches[0]["networks"].values() if v["ip"]]
        source = PROBE_PATH.read_text()
        result = self.command(
            ["docker", "exec", "-i", backend, "python", "-c", source],
            payload=encoded({"nodes": nodes, "endpoints": endpoints}).decode(),
        )
        # Import-time app logging must never masquerade as a diagnostic result.
        lines = [
            line.removeprefix("MAINTENANCE_RESULT=")
            for line in result.splitlines()
            if line.startswith("MAINTENANCE_RESULT=")
        ]
        if len(lines) != 1:
            raise ValueError("probe failed or incomplete")
        value: dict[str, Any] = json.loads(lines[0])
        return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["inventory", "preflight", "freeze", "drain", "status", "restore", "adopt"])
    parser.add_argument("--replacement", type=Path)
    parser.add_argument("--root", type=Path, default=CONTROLLER_ROOT)
    parser.add_argument("--record", type=Path)
    parser.add_argument("--operator")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        # A single canonical lock/claim root: alternate roots would evade ownership.
        if args.root != CONTROLLER_ROOT:
            raise ValueError("only canonical staging controller root allowed")
        private_path(args.root, directory=True)
        runtime = DockerRuntime()
        if args.action == "inventory":
            if not args.output or args.record or args.operator or args.replacement:
                raise ValueError("inventory requires a new private output only")
            if args.output.exists() or args.output.is_symlink():
                raise ValueError("inventory output already exists")
            private_path(args.output.parent, directory=True)
            exclusive(args.output, runtime.inventory())
            print("PASS: private operational inventory saved; no drain decision")
        else:
            if not args.record or not args.operator or args.output:
                raise ValueError("approved record/operator required")
            result = run(
                args.action,
                root=args.root,
                record_path=args.record,
                runtime=runtime,
                operator=args.operator,
                replacement_path=args.replacement,
            )
            print(json.dumps(result, sort_keys=True))
        return 0
    except (
        ValueError,
        KeyError,
        TypeError,
        IndexError,
        StopIteration,
        OSError,
        RuntimeError,
        subprocess.SubprocessError,
        http.client.HTTPException,
    ):
        print(
            "STOP: scope, private checkpoint, transport or live evidence not confirmed; "
            "retain state and inspect privately"
        )
        return 1


def maintenance_config(original: dict[str, Any]) -> dict[str, Any]:
    """Recognize the native staging Caddy shape, never patch arbitrary JSON."""
    frozen = copy.deepcopy(original)
    try:
        if set(frozen) != {"apps"} or set(frozen["apps"]) != {"http"}:
            raise ValueError("unsupported Caddy apps")
        http = frozen["apps"]["http"]
        if set(http) != {"servers"} or set(http["servers"]) != {"srv0"}:
            raise ValueError("unsupported Caddy servers")
        server = http["servers"]["srv0"]
        if set(server) != {"listen", "routes"} or server["listen"] != [":8080"] or len(server["routes"]) != 1:
            raise ValueError("unsupported staging listener")
        outer = server["routes"][0]
        if set(outer) != {"handle"} or len(outer["handle"]) != 3:
            raise ValueError("unsupported outer route")
        headers, encode, subroute = outer["handle"]
        if headers != {
            "handler": "headers",
            "response": {
                "set": {
                    "Referrer-Policy": ["no-referrer"],
                    "X-Content-Type-Options": ["nosniff"],
                    "X-Frame-Options": ["SAMEORIGIN"],
                    "X-Robots-Tag": ["noindex, nofollow, noarchive"],
                }
            },
        } or encode != {"handler": "encode", "encodings": {"gzip": {}, "zstd": {}}, "prefer": ["zstd", "gzip"]}:
            raise ValueError("unsupported staging headers/encoding")
        if set(subroute) != {"handler", "routes"} or subroute["handler"] != "subroute":
            raise ValueError("unsupported staging route")
        routes = subroute["routes"]
        if len(routes) != 5 or set(routes[0]) != {"handle"} or len(routes[0]["handle"]) != 1:
            raise ValueError("authentication must be unconditional and first")
        auth = routes[0]["handle"][0]
        if set(auth) != {"handler", "providers"} or auth["handler"] != "authentication":
            raise ValueError("missing authentication")
        providers = auth["providers"]
        if set(providers) != {"http_basic"} or not providers["http_basic"].get("accounts"):
            raise ValueError("missing basic authentication accounts")

        def proxy(dial: str) -> dict[str, Any]:
            return {"handler": "reverse_proxy", "upstreams": [{"dial": dial}]}

        expected = [
            {"handle": [proxy("staging-backend:8000")], "match": [{"path": ["/api/*"]}]},
            {
                "handle": [
                    {"handler": "static_response", "headers": {"Location": ["/career-metrics/"]}, "status_code": 308}
                ],
                "match": [{"path": ["/career-metrics"]}],
            },
            {
                "handle": [
                    {
                        "handler": "subroute",
                        "routes": [
                            {"handle": [{"handler": "rewrite", "strip_path_prefix": "/career-metrics"}]},
                            {"handle": [proxy("prometheus:9090")]},
                        ],
                    }
                ],
                "match": [{"path": ["/career-metrics/*"]}],
            },
            {"handle": [proxy("staging-frontend:3000")]},
        ]
        if routes[1:] != expected:
            raise ValueError("unsupported staging proxy shape")
        routes.insert(
            1,
            {
                "handle": [
                    {
                        "handler": "static_response",
                        "status_code": 503,
                        "body": "Staging maintenance\n",
                        "headers": {"Retry-After": ["60"]},
                    }
                ]
            },
        )
        return frozen
    except (KeyError, TypeError, IndexError) as exc:
        raise ValueError("unsupported staging Caddy shape") from exc


if __name__ == "__main__":
    raise SystemExit(main())
