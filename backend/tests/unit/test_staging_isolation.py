"""Staging edge and no-payment defaults must not inherit production authority."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
CONSUMERS = ("backend", "worker", "scheduler", "refinement-monitor")
PAYMENT_KEYS = (
    "YOOKASSA_SHOP_ID",
    "YOOKASSA_SECRET_KEY",
    "YOOKASSA_WEBHOOK_SECRET",
    "STRIPE_SECRET_KEY",
    "STRIPE_PUBLISHABLE_KEY",
    "STRIPE_WEBHOOK_SECRET",
)


def test_only_gateway_shares_edge_and_proxy_aliases_are_private() -> None:
    compose: dict[str, Any] = yaml.safe_load((ROOT / "docker-compose.staging.yml").read_text())
    services = compose["services"]
    assert [name for name, service in services.items() if "edge" in service.get("networks", {})] == ["gateway"]
    assert compose["networks"]["edge"] == {"external": True, "name": "astrotype_edge"}
    assert set(services["gateway"]["networks"]) == {"default", "edge"}
    caddy = (ROOT / "deploy/Caddyfile.staging").read_text()
    for name, port in (("backend", 8000), ("frontend", 3000)):
        alias = f"staging-{name}"
        assert alias in services[name]["networks"]["default"]["aliases"]
        assert f"{alias}:{port}" in caddy
    assert all(not service.get("ports") for service in services.values())


def test_all_staging_consumers_override_inherited_payment_credentials() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.staging.yml").read_text())
    for name in CONSUMERS:
        environment = compose["services"][name]["environment"]
        for key in PAYMENT_KEYS:
            assert environment.get(key) == "${STAGING_" + key + ":-}"


@pytest.fixture
def compose_directory(tmp_path: Path) -> Iterator[Path]:
    directory = tmp_path / "compose isolation"
    directory.mkdir()
    try:
        yield directory
    finally:
        shutil.rmtree(directory)


@pytest.mark.parametrize("isolated_credentials", [False, True])
def test_real_compose_render_isolates_edge_and_inherited_credentials(
    compose_directory: Path, isolated_credentials: bool
) -> None:
    # Copy exact source, never load the operator's ignored .env.staging or .env.
    docker = shutil.which("docker.exe") or shutil.which("docker")
    if docker is None:
        pytest.skip("Docker Compose CLI is not installed")
    directory = compose_directory
    compose_path = directory / "docker-compose.staging.yml"
    compose_path.write_bytes((ROOT / compose_path.name).read_bytes())
    env_path = directory / ".env.staging"
    env_path.write_text(
        "POSTGRES_PASSWORD=synthetic-placeholder\n"
        + "".join(f"{key}=inherited-must-not-survive\n" for key in PAYMENT_KEYS)
        + (
            "".join(f"STAGING_{key}=isolated-placeholder-{key}\n" for key in PAYMENT_KEYS)
            if isolated_credentials
            else ""
        )
    )
    environment = {
        key: value
        for key, value in os.environ.items()
        if key not in PAYMENT_KEYS and not key.startswith(("STAGING_", "COMPOSE_", "POSTGRES_"))
    }

    def cli_path(path: Path) -> str:
        if not docker.endswith(".exe"):
            return str(path)
        wslpath = shutil.which("wslpath")
        assert wslpath is not None
        return subprocess.check_output([wslpath, "-w", str(path)], text=True).strip()  # noqa: S603

    command = [docker, "compose", "--env-file", cli_path(env_path), "-f", cli_path(compose_path)]
    subprocess.run([*command, "config", "--quiet"], check=True, capture_output=True, env=environment)  # noqa: S603
    result = subprocess.run(  # noqa: S603
        [*command, "config", "--format", "json"], check=True, capture_output=True, text=True, env=environment
    )
    rendered = json.loads(result.stdout)
    services = rendered["services"]
    assert [name for name, service in services.items() if "edge" in service["networks"]] == ["gateway"]
    assert all(not service.get("ports") for service in services.values())
    for name in ("backend", "frontend"):
        assert f"staging-{name}" in services[name]["networks"]["default"]["aliases"]
    for name in CONSUMERS:
        for key in PAYMENT_KEYS:
            expected = f"isolated-placeholder-{key}" if isolated_credentials else ""
            assert services[name]["environment"][key] == expected
