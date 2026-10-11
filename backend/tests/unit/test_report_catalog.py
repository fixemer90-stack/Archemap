from __future__ import annotations

import pytest

from app.core.exceptions import ValidationError
from app.modules.catalog.service import REPORT_CATALOG, AccessClass, CatalogService


def test_report_catalog_has_exactly_one_basic_report() -> None:
    basic_reports = [item for item in REPORT_CATALOG.values() if item.access_class is AccessClass.BASIC]

    assert [item.report_type for item in basic_reports] == ["basic_natal"]


def test_every_specialized_report_is_plus_only() -> None:
    catalog = CatalogService()

    for report_type in ("career", "love", "child"):
        assert catalog.get_report(report_type).access_class is AccessClass.PLUS_ONLY


def test_report_aliases_are_non_destructive_and_fail_closed() -> None:
    catalog = CatalogService()

    assert catalog.resolve_report_type("basic_natal") == "basic_natal"
    assert catalog.resolve_report_type("self") == "basic_natal"
    assert catalog.resolve_report_type("self_full") == "basic_natal"
    assert catalog.resolve_report_type("career_full") == "career"

    with pytest.raises(ValidationError, match="Unknown report type"):
        catalog.resolve_report_type("future_report")


def test_commercial_and_storage_identifiers_have_one_mapping() -> None:
    catalog = CatalogService()
    basic = catalog.get_report("basic_natal")
    career = catalog.get_report("career")

    assert basic.storage_identifiers == ("self",)
    assert basic.commercial_skus == ("self_full",)
    assert basic.entitlement_product is None
    assert career.storage_identifiers == ("career",)
    assert career.commercial_skus == ("career_full",)
    assert career.entitlement_product == "career"
