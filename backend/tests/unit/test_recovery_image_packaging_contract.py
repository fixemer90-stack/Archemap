"""Recovery images must include runtime assets and use Node 24 in every stage."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("directory", ["rules", "scripts"])
def test_backend_runtime_image_copies_recovery_assets_under_app(directory: str) -> None:
    instructions = [
        line.split()
        for line in (ROOT / "backend/Dockerfile").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    assert [instruction for instruction in instructions if instruction[0] == "FROM"] == [
        ["FROM", "python:3.12-slim-bookworm", "AS", "runtime"]
    ]
    assert [instruction for instruction in instructions if instruction[0] == "WORKDIR"] == [["WORKDIR", "/app"]]
    assert ["COPY", directory, f"./{directory}"] in instructions
    assert (ROOT / "backend" / directory).is_dir()


@pytest.mark.parametrize("stage", ["deps", "builder", "runner"])
def test_frontend_image_uses_node_24_in_each_stage(stage: str) -> None:
    stages = [
        line.split()
        for line in (ROOT / "frontend/Dockerfile").read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("FROM ")
    ]

    assert [instruction[-1] for instruction in stages] == ["deps", "builder", "runner"]
    assert ["FROM", "node:24-alpine", "AS", stage] in stages
