
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.db.dependencies import get_db
from sqlalchemy.exc import IntegrityError

from app.services.user_service import create_user
from app.schemas.user import UserCreate

import pytest


client = TestClient(app)


def override_get_db():
    yield MagicMock()


@pytest.fixture(autouse=True)
def override_database_dependency():
    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db

    yield

    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous_overrides)


def test_create_user():
    with patch("app.api.users.create_user") as mock_create_user:
        mock_create_user.return_value = MagicMock(
            id=1,
            full_name="Test User",
            email="test@example.com",
            is_active=True,
        )

        response = client.post(
            "/users/",
            json={
                "full_name": "Test User",
                "email": "test@example.com",
            },
        )

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "full_name": "Test User",
        "email": "test@example.com",
        "is_active": True,
    }


def test_create_user_rejects_invalid_email():
    with patch("app.api.users.create_user") as mock_create_user:
        response = client.post(
            "/users/",
            json={
                "full_name": "Test User",
                "email": "not-an-email",
            },
        )

    assert response.status_code == 422
    mock_create_user.assert_not_called()


def test_create_user_rejects_duplicate_email():
    with patch("app.api.users.create_user") as mock_create_user:
        mock_create_user.side_effect = ValueError(
            "A user with this email already exists."
        )

        response = client.post(
            "/users/",
            json={
                "full_name": "Test User",
                "email": "test@example.com",
            },
        )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "A user with this email already exists."
    }

def test_create_user_rolls_back_on_integrity_error():
    db = MagicMock()
    user_data = UserCreate(
        full_name="Test User",
        email="test@example.com",
    )

    db.scalar.return_value = None
    db.commit.side_effect = IntegrityError(
        "INSERT",
        {},
        Exception("Unique constraint violation"),
    )

    try:
        create_user(db, user_data)
        assert False, "Expected ValueError was not raised"
    except ValueError as exc:
        assert str(exc) == "A user with this email already exists."

    db.rollback.assert_called_once()
