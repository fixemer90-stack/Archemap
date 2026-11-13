"""CI fixtures must not weaken the maintenance private-ancestor boundary."""

from pathlib import Path


def test_backend_ci_uses_runner_owned_temp_for_private_maintenance_fixtures() -> None:
    root = Path(__file__).resolve().parents[4]
    workflow = (root / ".github/workflows/ci.yml").read_text()
    backend = workflow.split("\n  test-backend:\n", 1)[1].split("\n  test-frontend:\n", 1)[0]
    assert "      TMPDIR: ${{ runner.temp }}\n" in backend
    assert "run: pytest tests/unit" in backend
    assert "run: pytest tests/integration" in backend
