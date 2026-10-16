from __future__ import annotations

from datetime import date, time

from app.modules.child.birth_data import child_birth_data_hash


def test_child_birth_data_hash_is_canonical_and_covers_persisted_correction_fields() -> None:
    canonical = child_birth_data_hash(
        birth_date=date(2021, 1, 3),
        birth_time=time(10, 30),
        birth_time_confidence="exact",
        birth_place="Moscow",
        latitude=55.7558,
        longitude=37.6173,
        timezone="Europe/Moscow",
    )

    assert canonical == "4bf5f1a67bcb57ae8a71242ded359bfe134db511639b6d3e774247ac783ab685"
    assert len(canonical) == 64
    assert (
        child_birth_data_hash(
            birth_date=date(2021, 1, 4),
            birth_time=time(10, 30),
            birth_time_confidence="exact",
            birth_place="Moscow",
            latitude=55.7558,
            longitude=37.6173,
            timezone="Europe/Moscow",
        )
        != canonical
    )
    assert (
        child_birth_data_hash(
            birth_date=date(2021, 1, 3),
            birth_time=time(10, 31),
            birth_time_confidence="exact",
            birth_place="Moscow",
            latitude=55.7558,
            longitude=37.6173,
            timezone="Europe/Moscow",
        )
        != canonical
    )
    assert (
        child_birth_data_hash(
            birth_date=date(2021, 1, 3),
            birth_time=time(10, 30),
            birth_time_confidence="approximate",
            birth_place="Moscow",
            latitude=55.7558,
            longitude=37.6173,
            timezone="Europe/Moscow",
        )
        != canonical
    )
    assert (
        child_birth_data_hash(
            birth_date=date(2021, 1, 3),
            birth_time=time(10, 30),
            birth_time_confidence="exact",
            birth_place="Kazan",
            latitude=55.7558,
            longitude=37.6173,
            timezone="Europe/Moscow",
        )
        != canonical
    )
    assert (
        child_birth_data_hash(
            birth_date=date(2021, 1, 3),
            birth_time=time(10, 30),
            birth_time_confidence="exact",
            birth_place="Moscow",
            latitude=55.7559,
            longitude=37.6173,
            timezone="Europe/Moscow",
        )
        != canonical
    )
    assert (
        child_birth_data_hash(
            birth_date=date(2021, 1, 3),
            birth_time=time(10, 30),
            birth_time_confidence="exact",
            birth_place="Moscow",
            latitude=55.7558,
            longitude=37.6174,
            timezone="Europe/Moscow",
        )
        != canonical
    )
    assert (
        child_birth_data_hash(
            birth_date=date(2021, 1, 3),
            birth_time=time(10, 30),
            birth_time_confidence="exact",
            birth_place="Moscow",
            latitude=55.7558,
            longitude=37.6173,
            timezone="Europe/Samara",
        )
        != canonical
    )
