"""Coordinate guards: (0,0) birth coordinates must be rejected everywhere."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.modules.auth.schemas import CompleteProfileRequest, RegisterRequest
from app.modules.profiles.schemas import CreateProfileRequest, UpdateProfileRequest


def _register_body(*, latitude: float = 55.75, longitude: float = 37.62) -> dict[str, object]:
    return {
        "email": "user@example.com",
        "password": "password123",
        "name": "Тест",
        "birth_date": "2000-01-01",
        "birth_time": "12:00:00",
        "birth_time_accuracy": "exact",
        "birth_place": "Москва, Россия",
        "latitude": latitude,
        "longitude": longitude,
        "timezone": "Europe/Moscow",
    }


def _complete_body(*, latitude: float = 55.75, longitude: float = 37.62) -> dict[str, object]:
    body = _register_body(latitude=latitude, longitude=longitude)
    body.pop("email")
    body.pop("password")
    return body


def _create_body(*, latitude: float = 55.75, longitude: float = 37.62) -> dict[str, object]:
    return {
        "name": "Тест",
        "birth_date": "2000-01-01",
        "birth_time": "12:00:00",
        "birth_time_accuracy": "exact",
        "birth_place": "Москва, Россия",
        "latitude": latitude,
        "longitude": longitude,
        "timezone": "Europe/Moscow",
    }


class TestRegisterRequestCoordinates:
    def test_accepts_real_coordinates(self) -> None:
        request = RegisterRequest.model_validate(_register_body())
        assert request.latitude == 55.75

    def test_rejects_zero_zero(self) -> None:
        with pytest.raises(ValidationError, match="Выберите место рождения"):
            RegisterRequest.model_validate(_register_body(latitude=0, longitude=0))

    def test_accepts_zero_latitude_with_real_longitude(self) -> None:
        request = RegisterRequest.model_validate(_register_body(latitude=0, longitude=37.62))
        assert request.latitude == 0.0


class TestCompleteProfileRequestCoordinates:
    def test_accepts_real_coordinates(self) -> None:
        request = CompleteProfileRequest.model_validate(_complete_body())
        assert request.latitude == 55.75

    def test_rejects_zero_zero(self) -> None:
        with pytest.raises(ValidationError, match="Выберите место рождения"):
            CompleteProfileRequest.model_validate(_complete_body(latitude=0, longitude=0))


class TestCreateProfileRequestCoordinates:
    def test_accepts_real_coordinates(self) -> None:
        request = CreateProfileRequest.model_validate(_create_body())
        assert request.latitude == 55.75

    def test_rejects_zero_zero(self) -> None:
        with pytest.raises(ValidationError, match="Выберите место рождения"):
            CreateProfileRequest.model_validate(_create_body(latitude=0, longitude=0))


class TestUpdateProfileRequestCoordinates:
    def test_accepts_partial_update_without_coordinates(self) -> None:
        request = UpdateProfileRequest.model_validate({"name": "Новое имя"})
        assert request.name == "Новое имя"

    def test_rejects_zero_zero(self) -> None:
        with pytest.raises(ValidationError, match="Выберите место рождения"):
            UpdateProfileRequest.model_validate({"latitude": 0, "longitude": 0})

    def test_accepts_real_coordinates(self) -> None:
        request = UpdateProfileRequest.model_validate({"latitude": 55.75, "longitude": 37.62})
        assert request.latitude == 55.75

    def test_rejects_latitude_without_longitude(self) -> None:
        with pytest.raises(ValidationError, match="вместе"):
            UpdateProfileRequest.model_validate({"latitude": 55.75})
