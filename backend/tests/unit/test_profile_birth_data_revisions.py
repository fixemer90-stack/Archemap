"""Contracts for durable birth-data revisions and the account cooldown."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import Table, UniqueConstraint, inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex

from app.modules.profiles.models import ProfileBirthDataRevision
from app.modules.profiles.refinement import (
    BirthDataCooldownError,
    BirthDataCooldownPolicy,
    BirthDataSnapshot,
)

ROOT = Path(__file__).resolve().parents[2]


def _snapshot(**overrides: object) -> BirthDataSnapshot:
    values: dict[str, object] = {
        "birth_time": time(14, 30),
        "birth_time_accuracy": "exact",
        "birth_place": "Moscow, Russia",
        "latitude": 55.7558,
        "longitude": 37.6173,
        "timezone": "Europe/Moscow",
    }
    values.update(overrides)
    return BirthDataSnapshot(**values)  # type: ignore[arg-type]


def test_revision_model_preserves_full_snapshots_lineage_and_idempotency() -> None:
    mapper = inspect(ProfileBirthDataRevision)
    columns = {column.key: column for column in mapper.columns}
    table = cast(Table, ProfileBirthDataRevision.__table__)

    assert set(columns) == {
        "id",
        "user_id",
        "profile_id",
        "previous_snapshot",
        "new_snapshot",
        "changed_fields",
        "status",
        "generation_id",
        "chart_id",
        "report_id",
        "error_code",
        "idempotency_key",
        "request_hash",
        "created_at",
        "updated_at",
    }
    for required in (
        "previous_snapshot",
        "new_snapshot",
        "changed_fields",
        "generation_id",
        "idempotency_key",
        "request_hash",
    ):
        assert columns[required].nullable is False
    assert columns["chart_id"].nullable is True
    assert columns["report_id"].nullable is True

    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert ("user_id", "idempotency_key") in unique_columns
    assert ("generation_id",) in unique_columns


def test_revision_history_indexes_keep_created_at_descending() -> None:
    table = cast(Table, ProfileBirthDataRevision.__table__)
    dialect = postgresql.dialect()  # type: ignore[no-untyped-call]
    compiled_indexes = {str(index.name): str(CreateIndex(index).compile(dialect=dialect)) for index in table.indexes}

    assert compiled_indexes["ix_profile_birth_data_revisions_user_created_at"].endswith("(user_id, created_at DESC)")
    assert compiled_indexes["ix_profile_birth_data_revisions_profile_created_at"].endswith(
        "(profile_id, created_at DESC)"
    )


def test_revision_history_links_use_restrict_to_preserve_history() -> None:
    foreign_keys = {
        column.name: next(iter(column.foreign_keys)).ondelete
        for column in ProfileBirthDataRevision.__table__.columns
        if column.foreign_keys
    }

    assert foreign_keys["user_id"] == "RESTRICT"
    assert foreign_keys["profile_id"] == "RESTRICT"
    assert foreign_keys["generation_id"] == "RESTRICT"


def test_snapshot_changed_fields_are_stable_and_domain_scoped() -> None:
    previous = _snapshot()
    updated = _snapshot(
        birth_time=time(15, 5),
        birth_place="Saint Petersburg, Russia",
        latitude=59.9343,
        longitude=30.3351,
        timezone="Europe/Moscow",
    )

    assert previous.changed_fields(updated) == [
        "birth_time",
        "birth_place",
        "latitude",
        "longitude",
    ]
    assert previous.to_dict()["birth_time"] == "14:30:00"
    assert previous.changed_fields(previous) == []


def test_cooldown_rejects_before_boundary_and_exposes_next_available_at() -> None:
    created_at = datetime(2026, 9, 27, 9, 0, tzinfo=UTC)
    now = created_at + timedelta(hours=23, minutes=59)

    with pytest.raises(BirthDataCooldownError) as exc_info:
        BirthDataCooldownPolicy.ensure_available(last_successful_at=created_at, now=now)

    assert exc_info.value.next_available_at == created_at + timedelta(hours=24)
    assert exc_info.value.retry_after_seconds == 60


def test_cooldown_allows_request_exactly_at_boundary() -> None:
    created_at = datetime(2026, 9, 27, 9, 0, tzinfo=UTC)

    BirthDataCooldownPolicy.ensure_available(
        last_successful_at=created_at,
        now=created_at + timedelta(hours=24),
    )


def test_revision_migration_is_additive_immutable_and_targets_current_head() -> None:
    migration_files = sorted((ROOT / "alembic" / "versions").glob("*_add_profile_birth_data_revisions.py"))

    assert len(migration_files) == 1
    migration_text = migration_files[0].read_text(encoding="utf-8")
    assert 'down_revision: str | None = "b7c8d9e0f1a2"' in migration_text
    assert 'op.create_table(\n        "profile_birth_data_revisions"' in migration_text
    assert '"user_id", "idempotency_key"' in migration_text
    assert 'ondelete="RESTRICT"' in migration_text
    assert "prevent_profile_birth_data_revision_fact_changes" in migration_text

    upgrade_text = migration_text.split("def downgrade()", maxsplit=1)[0]
    for destructive_operation in ("drop_table", "drop_column", "alter_column", "truncate"):
        assert destructive_operation not in upgrade_text.lower()
