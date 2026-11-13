"""Publishing code must not deploy to unavailable infrastructure."""

from pathlib import Path

import yaml


def test_registry_workflow_requires_explicit_manual_dispatch_for_deployment() -> None:
    root = Path(__file__).resolve().parents[3]
    workflow = yaml.safe_load((root / ".github/workflows/build-push-deploy.yml").read_text())
    for name in ("deploy-staging", "deploy-production"):
        assert workflow["jobs"][name].get("if") == "github.event_name == 'workflow_dispatch'"
