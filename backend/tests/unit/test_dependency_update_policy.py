"""Keep the pip updater's SQLAlchemy compatibility hold actionable."""

import re
import tomllib
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[2]


def _sqlalchemy_pin() -> str:
    project = tomllib.loads((_BACKEND / "pyproject.toml").read_text())
    requirement = next(item for item in project["project"]["dependencies"] if item.lower().startswith("sqlalchemy["))
    match = re.fullmatch(r"sqlalchemy\[asyncio\]==(2\.0\.\d+)", requirement)
    assert match is not None, (
        "The pip updater needs an explicit current SQLAlchemy 2.0 version "
        "to apply its routine minor/major update-type hold; an unlocked range "
        "has no current version."
    )
    return match.group(1)


def test_sqlalchemy_routine_update_hold_has_an_explicit_current_version() -> None:
    _sqlalchemy_pin()


def test_sqlalchemy_lock_matches_the_explicit_manifest_pin() -> None:
    lock = tomllib.loads((_BACKEND / "uv.lock").read_text())
    locked = [item["version"] for item in lock["package"] if item["name"] == "sqlalchemy"]
    assert locked == [_sqlalchemy_pin()]
