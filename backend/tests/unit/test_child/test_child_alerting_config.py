"""Offline contracts for the staging-only, privacy-bounded Child alert path."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[4]
ALERT_NAMES = {"ChildWorkerTerminalFailures", "ChildWorkerDurationHigh"}


def load_yaml(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    assert path.is_file(), f"Missing staged Child alert configuration: {relative}"
    return cast(dict[str, Any], yaml.safe_load(path.read_text(encoding="utf-8")))


def test_child_receiver_drops_unrelated_alerts_and_uses_only_private_files() -> None:
    config = load_yaml("deploy/alertmanager-child.staging.yaml")
    route = config["route"]
    assert route == {
        "receiver": "null",
        "group_by": ["alertname"],
        "group_wait": "5s",
        "group_interval": "10s",
        "repeat_interval": "4h",
        "routes": [
            {
                "receiver": "child-telegram",
                "matchers": ['environment="staging"', 'feature="child"'],
                "continue": False,
            }
        ],
    }
    receivers = {receiver["name"]: receiver for receiver in config["receivers"]}
    assert set(receivers) == {"null", "child-telegram"}
    assert receivers["null"] == {"name": "null"}
    telegram = receivers["child-telegram"]["telegram_configs"]
    assert len(telegram) == 1
    assert set(telegram[0]) == {
        "bot_token_file",
        "chat_id_file",
        "send_resolved",
        "parse_mode",
        "http_config",
        "message",
    }
    assert telegram[0]["bot_token_file"] == "/run/secrets/telegram_token"
    assert telegram[0]["chat_id_file"] == "/run/secrets/telegram_chat_id"
    assert telegram[0]["send_resolved"] is True
    assert telegram[0]["parse_mode"] == ""
    assert telegram[0]["http_config"] == {"follow_redirects": False}
    # Exact template contract: all interpolations are bounded conditionals; no raw data rendering.
    assert telegram[0]["message"] == (
        'STAGING E22 Child: {{ if eq .Status "firing" }}FIRING{{ else }}RESOLVED{{ end }}; '
        '{{ if eq .GroupLabels.alertname "ChildWorkerTerminalFailures" }}worker terminal failures'
        '{{ else if eq .GroupLabels.alertname "ChildWorkerDurationHigh" }}worker duration high'
        '{{ else if eq .GroupLabels.alertname "ChildAlertDeliveryProbe" }}alert delivery probe'
        "{{ else }}unclassified Child alert{{ end }}."
    )
    assert "${" not in (ROOT / "deploy/alertmanager-child.staging.yaml").read_text()
    assert not config.get("templates")
    assert not config.get("global")


def test_alertmanager_is_private_hardened_and_preserves_existing_staging_consumers() -> None:
    compose = load_yaml("docker-compose.staging.yml")
    services = compose["services"]
    assert "alertmanager" in services, "Child alert delivery requires a private Alertmanager"
    service = services["alertmanager"]
    assert service["image"] == "prom/alertmanager:v0.34.1"
    assert service["user"] == "65534:65534"
    assert service["read_only"] is True
    assert service["cap_drop"] == ["ALL"]
    assert service["security_opt"] == ["no-new-privileges:true"]
    assert service.get("networks", ["default"]) == ["default"]
    assert not set(service) & {"ports", "network_mode", "privileged", "env_file", "environment"}
    assert service["command"] == [
        "--config.file=/etc/alertmanager/alertmanager.yaml",
        "--storage.path=/alertmanager",
        "--cluster.listen-address=",
    ]
    assert service["volumes"] == [
        "./deploy/alertmanager-child.staging.yaml:/etc/alertmanager/alertmanager.yaml:ro",
        {
            "type": "bind",
            "source": "${CHILD_ALERT_SECRETS_DIR:-./.staging-secrets}/telegram_token",
            "target": "/run/secrets/telegram_token",
            "read_only": True,
            "bind": {"create_host_path": False},
        },
        {
            "type": "bind",
            "source": "${CHILD_ALERT_SECRETS_DIR:-./.staging-secrets}/telegram_chat_id",
            "target": "/run/secrets/telegram_chat_id",
            "read_only": True,
            "bind": {"create_host_path": False},
        },
        "alertmanager_staging_data:/alertmanager",
    ]
    assert set(compose["volumes"]) == {
        "postgres_staging_data",
        "redis_staging_data",
        "prometheus_staging_data",
        "alertmanager_staging_data",
    }
    for consumer in ("backend", "worker", "scheduler", "refinement-monitor"):
        assert services[consumer]["environment"]["CHILD_REPORT_ENABLED"] == "${CHILD_REPORT_ENABLED:-false}"
    for name, target in (("postgres", "/var/lib/postgresql/data"), ("redis", "/data")):
        assert services[name]["volumes"] == [f"{name}_staging_data:{target}"]


def test_prometheus_adds_child_rules_and_directory_probe_without_changing_scrapes() -> None:
    compose = load_yaml("docker-compose.staging.yml")
    prometheus = compose["services"]["prometheus"]
    assert prometheus["volumes"] == [
        "./deploy/prometheus.staging.yaml:/etc/prometheus/prometheus.yml:ro",
        "./deploy/prometheus-birth-data-refinement.rules.yaml:/etc/prometheus/rules/birth-data-refinement.yaml:ro",
        "./deploy/prometheus-subscriptions.rules.yaml:/etc/prometheus/rules/subscriptions.yaml:ro",
        "./deploy/prometheus-child.rules.yaml:/etc/prometheus/rules/child.yaml:ro",
        "${CHILD_ALERT_PROBE_DIR:-./.staging-alert-probes}:/etc/prometheus/child-alert-probes:ro",
        "prometheus_staging_data:/prometheus",
    ]
    assert "--web.external-url=https://staging.astrotype.ru/career-metrics/" in prometheus["command"]
    config = load_yaml("deploy/prometheus.staging.yaml")
    assert config["rule_files"] == ["/etc/prometheus/rules/*.yaml", "/etc/prometheus/child-alert-probes/*.yaml"]
    assert config["alerting"] == {"alertmanagers": [{"static_configs": [{"targets": ["alertmanager:9093"]}]}]}
    assert config["scrape_configs"] == [
        {"job_name": "otel-collector", "static_configs": [{"targets": ["otel-collector:9464"]}]}
    ]


def test_child_rules_use_observed_metrics_without_pii_labels_or_invented_signals() -> None:
    config = load_yaml("deploy/prometheus-child.rules.yaml")
    assert len(config["groups"]) == 1
    rules = {rule["alert"]: rule for rule in config["groups"][0]["rules"]}
    assert set(rules) == ALERT_NAMES
    failures = rules["ChildWorkerTerminalFailures"]
    assert " ".join(failures["expr"].split()) == (
        'sum(increase(child_worker_operations_total{operation="worker",'
        'outcome=~"narrative_failed|failed|age_update_failed|worker_failure"}[5m])) > 0 '
        'or sum(child_worker_operations_total{operation="worker",'
        'outcome=~"narrative_failed|failed|age_update_failed|worker_failure"} '
        'unless child_worker_operations_total{operation="worker",'
        'outcome=~"narrative_failed|failed|age_update_failed|worker_failure"} offset 5m) > 0'
    )
    assert failures["for"] == "1m"
    assert failures["annotations"] == {"summary": "STAGING E22 Child worker terminal failures detected"}
    latency = rules["ChildWorkerDurationHigh"]
    assert " ".join(latency["expr"].split()) == (
        "histogram_quantile(0.95, sum by (le) (rate(child_worker_duration_seconds_bucket[5m]))) > 120 "
        'and sum(rate(child_worker_duration_seconds_bucket{le="+Inf"}[5m])) > 0'
    )
    assert latency["for"] == "2m"
    assert latency["annotations"] == {"summary": "STAGING E22 Child worker duration p95 exceeds 120 seconds"}
    for rule in rules.values():
        assert rule["labels"] == {"environment": "staging", "feature": "child", "severity": "warning"}
        assert "{{" not in str(rule)
        assert not re.search(r"job=|exported_job=|provider|token|cost|stuck|vector\(", rule["expr"])


def test_ci_runs_native_alert_validators_without_delivery_credentials() -> None:
    workflow = load_yaml(".github/workflows/ci.yml")
    job = workflow["jobs"].get("validate-child-alerting")
    assert job is not None, "Native promtool/amtool checks must remain an exact-SHA CI gate"
    assert job["permissions"] == {"contents": "read"}
    assert "validate-child-alerting" in workflow["jobs"]["build"]["needs"]
    commands = "\n".join(step.get("run", "") for step in job["steps"])
    assert "prom/prometheus:v2.53.1" in commands
    assert "test rules prometheus-child-alerts.test.yaml" in commands
    assert "prom/alertmanager:v0.34.1" in commands
    assert "check-config /work/alertmanager-child.staging.yaml" in commands
    assert commands.count("--network=none") >= 2
    assert "synthetic-no-auth" in commands
    assert "secrets." not in str(job)


def test_promtool_cases_cover_zero_pending_firing_and_resolved_for_real_rules() -> None:
    config = load_yaml("deploy/prometheus-child-alerts.test.yaml")
    assert config["rule_files"] == ["prometheus-child.rules.yaml"]
    assert config["evaluation_interval"] == "1m"
    tests = {test["name"]: test for test in config["tests"]}
    assert set(tests) == {
        "zero-failures-and-zero-observations",
        "ready-and-nonworker-failures-do-not-alert",
        "healthy-observed-duration",
        "first-observed-nonzero-failure-counter",
        "terminal-narrative_failed",
        "terminal-failed",
        "terminal-age_update_failed",
        "terminal-worker_failure",
        "duration-high-then-resolved",
    }
    for case in tests.values():
        assert case["interval"] == "1m"
        assert case["input_series"]
        for expectation in case["alert_rule_test"]:
            assert expectation["alertname"] in ALERT_NAMES
    for outcome in ("narrative_failed", "failed", "age_update_failed", "worker_failure"):
        case = tests[f"terminal-{outcome}"]
        assert f'outcome="{outcome}"' in case["input_series"][0]["series"]
        expectations = case["alert_rule_test"]
        assert [item["eval_time"] for item in expectations] == ["0m", "1m", "2m", "8m"]
        assert [bool(item["exp_alerts"]) for item in expectations] == [False, False, True, False]
    latency = tests["duration-high-then-resolved"]["alert_rule_test"]
    assert [item["eval_time"] for item in latency] == ["0m", "2m", "3m", "12m"]
    assert [bool(item["exp_alerts"]) for item in latency] == [False, False, True, False]
