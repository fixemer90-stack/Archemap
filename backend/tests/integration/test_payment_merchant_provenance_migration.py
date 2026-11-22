"""Run only on an explicitly selected, empty disposable PostgreSQL database."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

_PREVIOUS = "b9c0d1e2f3a4"
_REVISION = "d1e2f3a4b5c6"
_REGISTRY = "f3a4b5c6d7e8"


async def test_payment_merchant_migration_keeps_legacy_unknown_and_rejects_rebinding() -> None:
    url = os.environ.get("TEST_PAYMENT_PROVENANCE_MIGRATION_DATABASE_URL")
    if not url:
        pytest.skip("explicit empty disposable payment migration database required")
    engine = create_async_engine(url)
    env = {**os.environ, "DATABASE_URL": url}

    def alembic(*args: str, succeeds: bool = True) -> str:
        result = subprocess.run(  # noqa: S603 - fixed interpreter/module and arguments
            [sys.executable, "-m", "alembic", *args],
            cwd=Path(__file__).resolve().parents[2],
            env=env,
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        assert (result.returncode == 0) is succeeds, result.stderr
        return result.stderr

    owner, legacy, bound, binding = (uuid4() for _ in range(4))
    try:
        async with engine.connect() as connection:
            name = await connection.scalar(text("SELECT current_database()"))
            assert isinstance(name, str) and name.endswith("_migration")
            assert await connection.scalar(text("SELECT current_schemas(false)")) == ["public"]
            assert not await connection.scalar(text("SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname='public')"))
        alembic("upgrade", _PREVIOUS)
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO users (id, email, name, hashed_password, is_active, is_verified, is_superuser) "
                    "VALUES (:owner, 'migration@example.invalid', '', 'unused', true, false, false)"
                ),
                {"owner": owner},
            )
            await connection.execute(
                text(
                    "INSERT INTO payments (id, user_id, provider, amount, status, paid_at) "
                    "VALUES (:legacy, :owner, 'yookassa', 999, 'succeeded', now())"
                ),
                {"legacy": legacy, "owner": owner},
            )
        alembic("upgrade", _REVISION)
        async with engine.begin() as connection:
            result = await connection.execute(
                text(
                    "SELECT merchant_binding_id, payment_mode, merchant_account_id, status, paid_at IS NOT NULL "
                    "FROM payments WHERE id = :legacy"
                ),
                {"legacy": legacy},
            )
            assert tuple(result.one()) == (None, None, None, "succeeded", True)
            await connection.execute(
                text(
                    "INSERT INTO payments (id, user_id, provider, amount, merchant_binding_id, "
                    "payment_mode, merchant_account_id) VALUES (:bound, :owner, 'yookassa', 999, "
                    ":binding, 'test', 'synthetic-shop')"
                ),
                {"bound": bound, "owner": owner, "binding": binding},
            )

        for sql, match, args in (
            ("UPDATE payments SET payment_mode = 'live' WHERE id = :id", "immutable", {"id": bound}),
            ("UPDATE payments SET merchant_account_id = 'other' WHERE id = :id", "immutable", {"id": bound}),
            (
                "UPDATE payments SET merchant_binding_id = :id WHERE id = :row",
                "immutable",
                {"id": uuid4(), "row": bound},
            ),
            (
                "UPDATE payments SET merchant_binding_id = :binding, payment_mode = 'live', "
                "merchant_account_id = 'synthetic-shop' WHERE id = :legacy",
                "immutable",
                {"legacy": legacy, "binding": binding},
            ),
            (
                "INSERT INTO payments (id, user_id, provider, amount, merchant_binding_id) "
                "VALUES (:id, :owner, 'yookassa', 999, :binding)",
                "ck_payments_merchant_provenance",
                {"id": uuid4(), "owner": owner, "binding": binding},
            ),
        ):
            with pytest.raises(DBAPIError, match=match):
                async with engine.begin() as connection:
                    await connection.execute(text(sql), args)

        assert "refusing downgrade" in alembic("downgrade", _PREVIOUS, succeeds=False)
        async with engine.begin() as connection:
            assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == _REVISION
            await connection.execute(text("DELETE FROM payments WHERE id = :bound"), {"bound": bound})
        alembic("downgrade", _PREVIOUS)
        alembic("upgrade", _REVISION)
        async with engine.connect() as connection:
            assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == _REVISION
            result = await connection.execute(text("SELECT id, payment_mode, status FROM payments"))
            assert [tuple(row) for row in result] == [(legacy, None, "succeeded")]

        insert_bound = text(
            "INSERT INTO payments (id, user_id, provider, amount, merchant_binding_id, payment_mode, "
            "merchant_account_id) VALUES (:payment, :owner, 'yookassa', 999, :binding, 'test', :account)"
        )
        conflicting = uuid4()
        async with engine.begin() as connection:
            for payment, account in ((bound, "synthetic-shop"), (conflicting, "other-shop")):
                await connection.execute(
                    insert_bound, {"payment": payment, "owner": owner, "binding": binding, "account": account}
                )
        assert "conflicting historical YooKassa binding provenance" in alembic("upgrade", _REGISTRY, succeeds=False)
        async with engine.begin() as connection:
            await connection.execute(text("DELETE FROM payments WHERE id = :id"), {"id": conflicting})
        alembic("upgrade", _REGISTRY)
        async with engine.begin() as connection:
            await connection.execute(text("DELETE FROM payments WHERE id = :id"), {"id": bound})
            registry = await connection.execute(
                text("SELECT id, payment_mode, merchant_account_id FROM yookassa_merchant_bindings")
            )
            assert [tuple(row) for row in registry] == [(binding, "test", "synthetic-shop")]
        with pytest.raises(DBAPIError, match="fk_payments_yookassa_binding"):
            async with engine.begin() as connection:
                await connection.execute(
                    insert_bound, {"payment": conflicting, "owner": owner, "binding": binding, "account": "other-shop"}
                )
        for statement in (
            "UPDATE yookassa_merchant_bindings SET payment_mode = 'live'",
            "DELETE FROM yookassa_merchant_bindings",
            "TRUNCATE yookassa_merchant_bindings CASCADE",
        ):
            with pytest.raises(DBAPIError, match="binding provenance is immutable"):
                async with engine.begin() as connection:
                    await connection.execute(text(statement))
        assert "registered YooKassa binding provenance exists" in alembic("downgrade", _REVISION, succeeds=False)
    finally:
        await engine.dispose()
