"""Transport contracts using fake command output, never a Docker daemon."""

from __future__ import annotations

import json
from typing import Any

import pytest
from scripts import child_staging_maintenance as tool
from tests.unit.test_child.test_staging_maintenance_controller import native_config


def test_admin_http_uses_exact_gateway_loopback_cas_and_stdin_not_secret_argv() -> None:
    calls: list[tuple[list[str], str | None]] = []
    identity = "a" * 64
    body = json.dumps(native_config())

    def command(args: list[str], *, payload: str | None = None) -> str:
        calls.append((args, payload))
        if args[1] == "inspect":
            return json.dumps(
                [
                    {
                        "Id": identity,
                        "Name": "/astrotype-staging-gateway-1",
                        "Config": {
                            "Labels": {
                                "com.docker.compose.project": "astrotype-staging",
                                "com.docker.compose.service": "gateway",
                            }
                        },
                    }
                ]
            )
        if args[-3:] == ["-c", "nc -w 15 127.0.0.1 2019", "maintenance-admin"]:
            if payload and payload.startswith("GET"):
                return f'HTTP/1.1 200 OK\r\nEtag: "native-tag"\r\nContent-Length: {len(body.encode())}\r\n\r\n{body}'
            return "HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n"
        return ""

    runtime = tool.DockerRuntime(command)
    config, etag = runtime.config(identity)
    assert config == native_config() and etag == '"native-tag"'
    runtime.load(identity, config, etag)
    argv, payload = calls[-1]
    assert "synthetic-hash" not in json.dumps(argv)
    assert payload and 'If-Match: "native-tag"\r\n' in payload
    assert payload.startswith("POST /config/ HTTP/1.1\r\nHost: localhost:2019")
    assert all("production" not in json.dumps(args) for args, _ in calls)


def test_native_adapter_rejects_production_even_if_caller_bypasses_run() -> None:
    calls: list[list[str]] = []

    def command(args: list[str], *, payload: str | None = None) -> str:
        calls.append(args)
        return json.dumps(
            [
                {
                    "Id": "a" * 64,
                    "Name": "/production-gateway",
                    "Config": {
                        "Labels": {"com.docker.compose.project": "production", "com.docker.compose.service": "gateway"}
                    },
                }
            ]
        )

    runtime = tool.DockerRuntime(command)
    with pytest.raises(ValueError):
        runtime.load("a" * 64, native_config(), "etag")
    assert len(calls) == 1 and calls[0][1] == "inspect"
    with pytest.raises(ValueError):
        runtime.running("production-name", False)
    assert len(calls) == 1


def test_probe_matches_every_named_node_to_exact_consumer_container(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = tool.DockerRuntime(lambda args, payload=None: "MAINTENANCE_RESULT={}\n")
    inventory = [
        {
            "id": f"{index:064x}",
            "project": tool.PROJECT,
            "service": service,
            "networks": {"private": {"ip": f"172.30.0.{index}"}},
        }
        for index, service in enumerate(["postgres", "redis", "worker", "refinement-monitor"], 1)
    ]
    monkeypatch.setattr(runtime, "inventory", lambda: inventory)
    monkeypatch.setattr(runtime, "require", lambda identity, service: {"Config": {"Hostname": "actual-hostname"}})
    with pytest.raises(ValueError):
        runtime.probe("a" * 64, {"celery@wrong-hostname": {"service": "worker", "queues": ["celery"]}})


def test_parser_decodes_chunked_json_and_rejects_missing_etag() -> None:
    payload = b'{"apps":{}}'
    response = b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\nEtag: "x"\r\n\r\n'
    response += f"{len(payload):x}\r\n".encode() + payload + b"\r\n0\r\n\r\n"
    body, etag = tool.admin_response(response.decode(), require_etag=True)
    assert json.loads(body) == {"apps": {}} and etag == '"x"'
    with pytest.raises(ValueError):
        tool.admin_response("HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n{}", require_etag=True)


def test_readonly_probe_is_published_bundled_source_and_compiles() -> None:
    from scripts import child_staging_probe

    source = tool.PROBE_PATH.read_text()
    compile(source, str(tool.PROBE_PATH), "exec")
    assert child_staging_probe.TABLE_TERMINALS["child_generations"] == {
        "ready",
        "narrative_failed",
        "failed",
        "age_update_ready",
        "age_update_failed",
    }
    assert "deterministic_ready" not in child_staging_probe.TABLE_TERMINALS["child_generations"]
    assert set(child_staging_probe.TABLE_TERMINALS) | child_staging_probe.SPECIAL_TABLES == tool.TABLES


def test_readonly_probe_rejects_live_unknown_statuses_and_unknown_outcomes() -> None:
    from scripts import child_staging_probe as probe

    assert probe.settled("child_segment_generations", {"status": "ready", "error_code": None})
    rows: list[dict[str, Any]] = [
        {"status": "retry_waiting"},
        {"status": "new_unreviewed_status"},
        {"status": "failed", "error_code": "child_narrative_provider_outcome_unknown"},
        {"status": "failed", "diagnostics": {"provider_outcome": "unknown"}},
    ]
    for row in rows:
        assert not probe.settled("child_segment_generations", row)
    assert not probe.settled(
        "profile_birth_data_revisions", {"status": "deterministic_ready", "dispatch_status": "pending"}
    )


def test_payment_webhook_and_legacy_narrative_families_cannot_hide_unsettled_work() -> None:
    from scripts import child_staging_probe as probe

    assert not probe.settled("payments", {"status": "pending"})
    assert probe.settled("payments", {"status": "succeeded"})
    assert not probe.settled("payment_webhooks", {"processed": False})
    assert probe.settled("payment_webhooks", {"processed": True})
    assert probe.settled("report_narratives", {"status": "narrative_failed"})
    assert not probe.settled(
        "report_narratives", {"status": "ready", "content": {"stage_artifacts": [{"status": "running"}]}}
    )


def test_http_socket_inventory_counts_ipv4_ipv6_accepted_requests_not_listeners() -> None:
    from scripts import child_staging_probe as probe

    rows = "  sl local_address rem_address st\n"
    rows += " 0: 00000000:1F40 00000000:0000 0A\n"  # listener :8000
    rows += " 1: 0100007F:1F40 0100007F:A050 01\n"  # established :8000
    rows += " 2: 0100007F:1F40 0100007F:A051 08\n"  # close-wait :8000
    rows += " 3: 0100007F:15B3 0100007F:A051 01\n"  # unrelated DB connection
    assert probe.http_connections(rows) == 2
    assert probe.http_connections(rows.replace("0100007F:", "00000000000000000000000001000000:")) == 2


def test_probe_endpoint_scope_rejects_nonstage_dns_before_inspections() -> None:
    from scripts import child_staging_probe as probe

    def resolver(name: str) -> str:
        return "172.30.0.5" if name == "postgres" else "172.30.0.6"

    probe.require_endpoints(
        "postgresql+asyncpg://hidden@postgres/stage",
        "redis://redis/0",
        {"postgres": ["172.30.0.5"], "redis": ["172.30.0.6"]},
        resolver,
    )
    with pytest.raises(ValueError):
        probe.require_endpoints(
            "postgresql+asyncpg://hidden@production/stage",
            "redis://redis/0",
            {"postgres": ["172.30.0.5"], "redis": ["172.30.0.6"]},
            resolver,
        )
