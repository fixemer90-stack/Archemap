from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import httpx
import pytest
from scripts.child_backup_restore import require_disposable
from scripts.child_rollout_smoke import DISABLED_CASES, check_response, smoke
from sqlalchemy import Table

from app.modules.child import models
from app.modules.child.privacy_export import CHILD_EXPORT_TABLES, _without_credentials


def test_export_inventory_matches_all_child_models_including_s11() -> None:
    actual = {
        cast(Table, mapper.local_table).name
        for mapper in models.ChildProfile.registry.mappers
        if mapper.class_.__module__ == models.__name__
    }
    assert {table.name for table in CHILD_EXPORT_TABLES} == actual
    assert {"child_generations", "child_generation_events", "child_report_assemblies"} <= actual


def test_credentials_are_recursively_removed_without_stripping_owner_data() -> None:
    source = {
        "API_KEY": "SECRET",
        "Provider_Credentials": {"token": "SECRET"},
        "answers": [{"Authorization": "SECRET", "value": "protected owner answer"}],
        "claim_token": "SECRET",
    }
    result = _without_credentials(source)
    assert "SECRET" not in json.dumps(result)
    assert result["answers"][0]["value"] == "protected owner answer"


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://e22test@127.0.0.1:55434/app",
        "postgresql://e22test@db:55434/e22_qa_test",
        "postgresql://e22test@127.0.0.1:5432/e22_qa_test",
        "postgresql://e22test@127.0.0.1:55434/e22_qa_restore",
        "postgresql://other@127.0.0.1:55434/e22_qa_test",
        "postgresql://e22test@127.0.0.1:55434/e22_qa_test?host=prod",
    ],
)
def test_backup_never_accepts_application_or_wrong_target(url: str) -> None:
    with pytest.raises(ValueError):
        require_disposable(url, database="e22_qa_test")


def test_backup_accepts_only_explicit_disposable_endpoint() -> None:
    require_disposable("postgresql://e22test@127.0.0.1:55434/e22_qa_test", database="e22_qa_test")


@pytest.mark.parametrize(
    "compose_name", ["docker-compose.yml", "docker-compose.staging.yml", "docker-compose.prod.yml"]
)
def test_child_rollout_flag_is_operator_configurable_for_every_writer(compose_name: str) -> None:
    import yaml

    compose = yaml.safe_load((Path(__file__).parents[4] / compose_name).read_text())
    for service in ("backend", "worker", "scheduler", "refinement-monitor"):
        assert compose["services"][service]["environment"]["CHILD_REPORT_ENABLED"] == "${CHILD_REPORT_ENABLED:-false}"


def test_restore_rejects_empty_history_instead_of_claiming_data_proof(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from scripts import child_backup_restore as backup

    monkeypatch.setattr(backup, "sql", lambda *_: "0")
    monkeypatch.setattr(backup, "manifest", lambda _: {"tables": {}, "schema_sha256": "empty"})
    monkeypatch.setattr(backup, "command", lambda _: "not-an-execution")
    with pytest.raises(ValueError, match="nonempty"):
        backup.prove_restore(
            source="postgresql://e22test@127.0.0.1:55434/e22_qa_test",
            target="postgresql://e22test@127.0.0.1:55434/e22_qa_restore",
            report=tmp_path / "empty.json",
        )


def test_restore_schema_hash_normalizes_postgres_array_cast_deparse_only() -> None:
    from scripts.child_backup_restore import normalize_schema

    before = "CHECK (status::text = ANY ((ARRAY['exact'::character varying, 'unknown'::character varying])::text[]));"
    after = (
        "CHECK (status::text = ANY (ARRAY[('exact'::character varying)::text, ('unknown'::character varying)::text]));"
    )
    assert normalize_schema(before) == normalize_schema(after)
    assert normalize_schema(before) != normalize_schema(after.replace("unknown", "unsafe"))
    assert normalize_schema(before) != normalize_schema(after.replace("CHECK", "NOT CHECK"))


def disabled_cases() -> list[dict[str, Any]]:
    return [
        {
            "name": "flag_off_read",
            "path": "/api/v1/child/reports/opaque",
            "token_env": "OPS_TOKEN",
            "equals": {"/report_id": "opaque"},
        },
        {
            "name": "flag_off_write",
            "path": "/api/v1/child/reports",
            "token_env": "OPS_TOKEN",
            "body": {"child_profile_id": "opaque"},
        },
    ]


@pytest.mark.parametrize("failure", [False, True])
def test_smoke_records_real_transport_status_and_truthful_failure(
    monkeypatch: pytest.MonkeyPatch,
    failure: bool,
) -> None:
    monkeypatch.setenv("OPS_TOKEN", "not-a-real-token")
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        if failure:
            return httpx.Response(500, json={"private": "NAME DOB ANSWERS PROSE"})
        return (
            httpx.Response(503, json={"detail": "Child Report is not enabled"})
            if request.method == "POST"
            else httpx.Response(200, json={"report_id": "opaque"})
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = smoke(
            base_url="https://stage.invalid", cases=disabled_cases(), phase="disabled", sha="a" * 40, client=client
        )
    assert result["passed"] is not failure
    assert calls == ["GET", "POST"]
    assert {item["scenario"] for item in result["results"]} == DISABLED_CASES
    assert "NAME" not in json.dumps(result)
    assert "not-a-real-token" not in json.dumps(result)
    assert result["staging_budgets"] == "NOT_MEASURED"
    assert result["deployed_sha_verified"] is False


def test_smoke_gateway_auth_isolated_per_actor_on_real_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GATEWAY_USER", "operator")
    monkeypatch.setenv("GATEWAY_PASSWORD", "gateway-private")
    monkeypatch.setenv("OPS_TOKEN", "actor-one.jwt")
    monkeypatch.setenv("OTHER_TOKEN", "actor-two.jwt")
    password_env_name = "GATEWAY_PASSWORD"
    cases = disabled_cases()
    cases[1]["token_env"] = "OTHER_TOKEN"
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200 if request.method == "GET" else 503,
            json={"report_id": "opaque"} if request.method == "GET" else {"detail": "Child Report is not enabled"},
            headers={"Set-Cookie": "access_token=response-poison; Path=/"},
        )

    with httpx.Client(
        transport=httpx.MockTransport(handler),
        auth=("ambient", "wrong"),
        cookies={"access_token": "client-poison", "unrelated": "private"},
        headers={"Cookie": "header-poison=private", "Authorization": "Bearer ambient"},
    ) as client:
        result = smoke(
            base_url="https://stage.invalid",
            cases=cases,
            phase="disabled",
            sha="a" * 40,
            client=client,
            gateway_user_env="GATEWAY_USER",
            gateway_password_env=password_env_name,
        )
    assert result["passed"]
    assert [request.headers["authorization"] for request in requests] == [
        "Basic b3BlcmF0b3I6Z2F0ZXdheS1wcml2YXRl",
    ] * 2
    assert [request.headers["cookie"] for request in requests] == [
        "access_token=actor-one.jwt",
        "access_token=actor-two.jwt",
    ]
    assert all(len(request.headers.get_list("authorization")) == 1 for request in requests)
    assert not any(secret in json.dumps(result) for secret in ("gateway-private", "actor-one.jwt", "actor-two.jwt"))


@pytest.mark.parametrize(
    "user,password",
    [
        (None, "PASS_ENV"),
        ("USER_ENV", None),
        ("USER_ENV", "PASS_ENV"),
        ("", "PASS_ENV"),
        ("not-an-env-name", "PASS_ENV"),
    ],
)
def test_gateway_misconfiguration_never_sends_requests(
    monkeypatch: pytest.MonkeyPatch, user: str | None, password: str | None
) -> None:
    monkeypatch.delenv("USER_ENV", raising=False)
    monkeypatch.delenv("PASS_ENV", raising=False)

    def forbidden(request: httpx.Request) -> httpx.Response:
        pytest.fail("misconfigured credentials must fail before transport")

    with httpx.Client(transport=httpx.MockTransport(forbidden)) as client, pytest.raises(ValueError) as error:
        smoke(
            base_url="https://stage.invalid",
            cases=disabled_cases(),
            phase="disabled",
            sha="a" * 40,
            client=client,
            gateway_user_env=user,
            gateway_password_env=password,
        )
    assert "private" not in str(error.value)


def test_legacy_bearer_overrides_ambient_client_auth_and_cookies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPS_TOKEN", "actor.jwt")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer actor.jwt"
        assert request.headers["Cookie"] == ""
        return (
            httpx.Response(503, json={"detail": "Child Report is not enabled"})
            if request.method == "POST"
            else httpx.Response(200, json={"report_id": "opaque"})
        )

    with httpx.Client(
        transport=httpx.MockTransport(handler), auth=("ambient", "private"), cookies={"access_token": "wrong"}
    ) as client:
        assert smoke(
            base_url="https://stage.invalid", cases=disabled_cases(), phase="disabled", sha="a" * 40, client=client
        )["passed"]


@pytest.mark.parametrize("symlink", [False, True])
def test_smoke_cli_refuses_existing_report_before_transport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    symlink: bool,
) -> None:
    import sys

    from scripts import child_rollout_smoke as rollout

    baseline = tmp_path / "baseline.json"
    baseline.write_text("retained evidence")
    report = tmp_path / "report.json" if symlink else baseline
    if symlink:
        report.symlink_to(baseline)
    manifest = tmp_path / "manifest.json"
    manifest.write_text("[]")
    called = []

    def fake_smoke(**kwargs: Any) -> dict[str, Any]:
        called.append(True)
        return {"passed": True}

    monkeypatch.setattr(rollout, "smoke", fake_smoke)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "smoke",
            "--base-url",
            "https://stage.invalid",
            "--manifest",
            str(manifest),
            "--report",
            str(report),
            "--sha",
            "a" * 40,
        ],
    )
    with pytest.raises(SystemExit) as exc:
        rollout.main()
    assert exc.value.code == 1
    assert baseline.read_text() == "retained evidence"
    assert not called


def test_smoke_cli_creates_private_new_evidence_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sys

    from scripts import child_rollout_smoke as rollout

    report = tmp_path / "private" / "result.json"
    manifest = tmp_path / "manifest.json"
    manifest.write_text("[]")
    monkeypatch.setattr(rollout, "smoke", lambda **kwargs: {"passed": True})
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "smoke",
            "--base-url",
            "https://stage.invalid",
            "--manifest",
            str(manifest),
            "--report",
            str(report),
            "--sha",
            "a" * 40,
        ],
    )
    with pytest.raises(SystemExit) as exc:
        rollout.main()
    assert exc.value.code == 0
    assert report.stat().st_mode & 0o777 == 0o600
    assert report.parent.stat().st_mode & 0o777 == 0o700


@pytest.mark.parametrize("name", ["exact", "approximate", "unknown", "two_child", "provider_failure", "flag_off_read"])
def test_successful_smoke_probe_requires_resource_identity_not_just_any_assertion(name: str) -> None:
    body = {
        "id": "owned-child",
        "report_id": "owned-report",
        "generation_id": "owned-generation",
        "birth_time_confidence": name,
        "birth_time": None if name == "unknown" else "10:20:00",
        "status": "narrative_failed",
    }
    case: dict[str, Any] = {
        "name": name,
        "equals": {"/status": "narrative_failed"},
        "forbidden_values": ["sibling-child"],
    }
    response = httpx.Response(200, json=body)
    assert not check_response(case, response)
    identity = "/report_id" if name == "flag_off_read" else "/generation_id" if name == "provider_failure" else "/id"
    case["equals"][identity] = body[identity[1:]]
    assert check_response(case, response)


def test_rollout_pdf_probe_requires_canonical_pinned_snapshot_and_no_credentials() -> None:
    from scripts.child_rollout_smoke import validate_path

    snapshot = "3bd091d7-1774-49d7-9845-f38ea7c2fd7e"
    path = "/api/v1/child/reports/opaque/pdf"
    validate_path({"name": "pdf", "path": f"{path}?age_snapshot_id={snapshot}"})
    for invalid in (
        path,
        f"{path}?access_token=secret",
        f"{path}?age_snapshot_id={snapshot}&token=secret",
        "/api/v1/child/%2e%2e/auth/me",
    ):
        with pytest.raises(ValueError):
            validate_path({"name": "pdf", "path": invalid})


def test_smoke_denies_insecure_remote_transport() -> None:
    with httpx.Client() as client, pytest.raises(ValueError, match="HTTPS"):
        smoke(
            base_url="http://prod.invalid",
            cases=disabled_cases(),
            phase="disabled",
            sha="a" * 40,
            client=client,
            allow_local_http=True,
        )


@pytest.mark.parametrize(
    "name,body",
    [
        ("locked", {"detail": {"display_name": "SECRET"}}),
        ("foreign", {"detail": "Child resource not found", "answers": []}),
        ("unknown", {"birth_time_confidence": "unknown", "birth_time": "12:00"}),
        ("approximate", {"id": "target", "birth_time_confidence": "unknown", "birth_time": None}),
        ("provider_failure", {"status": "ready"}),
        ("two_child", {"id": "sibling"}),
    ],
)
def test_semantically_wrong_smoke_responses_cannot_pass(name: str, body: dict[str, Any]) -> None:
    assert not check_response(
        {"name": name, "equals": {"/id": "target"}, "forbidden_values": ["sibling"]},
        httpx.Response({"locked": 402, "foreign": 404}.get(name, 200), json=body),
    )
