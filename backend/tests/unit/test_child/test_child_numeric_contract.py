from __future__ import annotations

from decimal import Decimal

import pytest

from app.modules.child.repository import _numbers_close


@pytest.mark.parametrize("value,expected", [(0.123456, 0.123457), (0.531206, 0.531207), (0.000001, 0.000002)])
def test_persisted_decimal_tolerance_is_not_narrowed_by_binary_float(value: float, expected: float) -> None:
    assert abs(Decimal(str(value)) - Decimal(str(expected))) == Decimal("0.000001")
    assert _numbers_close(value, expected, tolerance=1e-6)
    assert not _numbers_close(value, expected + 1e-6, tolerance=1e-6)
