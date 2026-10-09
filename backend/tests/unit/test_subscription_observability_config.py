"""E6.S15 deployment wiring for subscription alerts."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def test_subscription_alert_rules_are_mounted_and_reference_bounded_metrics() -> None:
    rules_path = ROOT / "deploy/prometheus-subscriptions.rules.yaml"
    rules = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    alerts = {rule["alert"]: rule for group in rules["groups"] for rule in group["rules"]}

    assert "SubscriptionRenewalFailures" in alerts
    assert "SubscriptionWebhookReconciliationFailures" in alerts
    assert "subscription_operation_failures_total" in alerts["SubscriptionRenewalFailures"]["expr"]
    assert "subscription_operation_failures_total" in alerts["SubscriptionWebhookReconciliationFailures"]["expr"]
    assert "S15-subscription-observability-admin.md" in alerts["SubscriptionRenewalFailures"]["annotations"]["runbook"]

    compose = (ROOT / "docker-compose.staging.yml").read_text(encoding="utf-8")
    assert "prometheus-subscriptions.rules.yaml:/etc/prometheus/rules/subscriptions.yaml:ro" in compose
