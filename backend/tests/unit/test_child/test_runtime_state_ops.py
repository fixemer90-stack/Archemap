"""Read-only operator tooling; all subprocess access is faked."""

import json
import subprocess
from importlib import import_module
from pathlib import Path

import pytest


def test_wrong_container_is_rejected_before_any_access(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state = import_module("scripts.child_runtime_state")

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("transport must not run")

    monkeypatch.setattr(state.subprocess, "run", forbidden)
    assert (
        state.main(["--container", "astrotype-production-postgres-1", "--snapshot", str(tmp_path / "new" / "b.json")])
        == 1
    )
    assert not (tmp_path / "new").exists()


def fake_docker(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
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
        body = "child_generations\nentitlements\npayments\nperson_profiles\nusers\n"
    elif "count(*)" in str(kwargs.get("input")):
        body = "2\n"
    else:
        body = '{"private": "TEST ROW NEVER PRINTED"}\n'
    return subprocess.CompletedProcess(args, 0, stdout=body, stderr="")


def test_snapshot_and_compare_are_private_and_read_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    state = import_module("scripts.child_runtime_state")
    calls: list[list[str]] = []

    def run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args[:2] != ["docker", "inspect"]:
            assert str(kwargs["input"]).startswith("BEGIN TRANSACTION READ ONLY;")
            assert all(x not in str(kwargs["input"]) for x in ["DROP ", "UPDATE ", "DELETE ", "INSERT "])
        return fake_docker(args, **kwargs)

    monkeypatch.setattr(state.subprocess, "run", run)
    base = tmp_path / "private" / "baseline.json"
    report = tmp_path / "private" / "proof.json"
    assert state.main(["--container", "astrotype-staging-postgres-1", "--snapshot", str(base)]) == 0
    assert base.stat().st_mode & 0o777 == 0o600
    assert base.parent.stat().st_mode & 0o777 == 0o700
    assert (
        state.main(["--container", "astrotype-staging-postgres-1", "--compare", str(base), "--report", str(report)])
        == 0
    )
    assert json.loads(report.read_text())["passed"] is True
    assert "TEST ROW" not in base.read_text() + report.read_text() + capsys.readouterr().out
    assert calls[0][:2] == ["docker", "inspect"]


@pytest.mark.parametrize("kind", ["project", "inventory", "transport"])
def test_failures_are_closed_and_redacted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], kind: str
) -> None:
    state = import_module("scripts.child_runtime_state")

    def run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        result = fake_docker(args, **kwargs)
        if kind == "project" and args[:2] == ["docker", "inspect"]:
            return subprocess.CompletedProcess(
                args, 0, stdout=result.stdout.replace("astrotype-staging", "production"), stderr=""
            )
        if kind == "inventory" and "pg_tables" in str(kwargs.get("input")):
            return subprocess.CompletedProcess(args, 0, stdout="users\nunsafe;DROP TABLE users\n", stderr="")
        if kind == "transport":
            return subprocess.CompletedProcess(args, 1, stdout="SECRET RESPONSE", stderr="PRIVATE PASSWORD")
        return result

    monkeypatch.setattr(state.subprocess, "run", run)
    target = tmp_path / "baseline.json"
    assert state.main(["--container", "astrotype-staging-postgres-1", "--snapshot", str(target)]) == 1
    assert not target.exists()
    assert "SECRET" not in capsys.readouterr().out


def test_baseline_cannot_be_overwritten_and_changes_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state = import_module("scripts.child_runtime_state")
    monkeypatch.setattr(state.subprocess, "run", fake_docker)
    base = tmp_path / "baseline.json"
    args = ["--container", "astrotype-staging-postgres-1", "--snapshot", str(base)]
    assert state.main(args) == 0
    original = base.read_bytes()
    assert state.main(args) == 1 and base.read_bytes() == original
    data = json.loads(original)
    data["tables"]["users"]["rows"] += 1
    base.write_text(json.dumps(data))
    report = tmp_path / "proof.json"
    assert (
        state.main(["--container", "astrotype-staging-postgres-1", "--compare", str(base), "--report", str(report)])
        == 1
    )
    assert json.loads(report.read_text())["passed"] is False


def test_full_application_backup_before_child_migration_keeps_legacy_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = import_module("scripts.child_runtime_state")

    def run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        result = fake_docker(args, **kwargs)
        if "pg_tables" in str(kwargs.get("input")):
            return subprocess.CompletedProcess(
                args, 0, stdout="entitlements\npayments\nperson_profiles\nusers\n", stderr=""
            )
        return result

    monkeypatch.setattr(state.subprocess, "run", run)
    baseline = tmp_path / "legacy.json"
    assert state.main(["--container", "astrotype-staging-postgres-1", "--all-public", "--snapshot", str(baseline)]) == 0
    assert set(json.loads(baseline.read_text())["tables"]) == state.ACCOUNTS


def test_full_application_restore_manifest_supports_only_disposable_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = import_module("scripts.child_runtime_state")
    monkeypatch.setattr(state.subprocess, "run", fake_docker)
    base = tmp_path / "all.json"
    assert state.main(["--container", "astrotype-staging-postgres-1", "--all-public", "--snapshot", str(base)]) == 0
    data = json.loads(base.read_text())
    assert data["schema_sha256"] and data["all_public"] is True
    proof = tmp_path / "restore.json"
    assert (
        state.main(
            [
                "--container",
                "astrotype-staging-postgres-1",
                "--all-public",
                "--database",
                "e22_restore_6114db2cdbd2_123",
                "--compare",
                str(base),
                "--report",
                str(proof),
            ]
        )
        == 0
    )

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("unapproved database must fail before access")

    monkeypatch.setattr(state.subprocess, "run", forbidden)
    assert (
        state.main(
            [
                "--container",
                "astrotype-staging-postgres-1",
                "--database",
                "production",
                "--snapshot",
                str(tmp_path / "bad.json"),
            ]
        )
        == 1
    )
