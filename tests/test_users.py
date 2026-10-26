
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.dependencies import get_db
from app.main import app
from app.schemas.user import UserCreate
from app.services.user_service import create_user, password_hash


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
                "password": "StrongPass123!",
            },
        )

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "full_name": "Test User",
        "email": "test@example.com",
        "is_active": True,
    }
    assert "password" not in response.json()
    assert "hashed_password" not in response.json()


def test_create_user_rejects_invalid_email():
    with patch("app.api.users.create_user") as mock_create_user:
        response = client.post(
            "/users/",
            json={
                "full_name": "Test User",
                "email": "not-an-email",
                "password": "StrongPass123!",
            },
        )

    assert response.status_code == 422
    mock_create_user.assert_not_called()


def test_create_user_rejects_short_password():
    with patch("app.api.users.create_user") as mock_create_user:
        response = client.post(
            "/users/",
            json={
                "full_name": "Test User",
                "email": "test@example.com",
                "password": "short",
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
                "password": "StrongPass123!",
            },
        )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "A user with this email already exists."
    }


def test_create_user_rolls_back_on_unrelated_integrity_error():
    db = MagicMock()
    user_data = UserCreate(
        full_name="Test User",
        email="test@example.com",
        password="StrongPass123!",
    )

    db.scalar.return_value = None
    db.commit.side_effect = IntegrityError(
        "INSERT",
        {},
        Exception("Unrelated constraint violation"),
    )

    with pytest.raises(IntegrityError):
        create_user(db, user_data)

    db.rollback.assert_called_once()


def test_create_user_stores_password_hash():
    db = MagicMock()
    db.scalar.return_value = None
    user_data = UserCreate(
        full_name="Test User",
        email="test@example.com",
        password="StrongPass123!",
    )

    created_user = create_user(db, user_data)

    assert created_user.hashed_password != "StrongPass123!"
    assert password_hash.verify(
        "StrongPass123!",
        created_user.hashed_password,
    )
    db.add.assert_called_once_with(created_user)
    db.commit.assert_called_once()


def test_get_user():
    with patch("app.api.users.get_user") as mock_get_user:
        mock_get_user.return_value = MagicMock(
            id=1,
            full_name="Test User",
            email="test@example.com",
            is_active=True,
        )

        response = client.get("/users/1")

    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["email"] == "test@example.com"
    assert "hashed_password" not in response.json()


def test_get_user_not_found():
    with patch("app.api.users.get_user", return_value=None):
        response = client.get("/users/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found."


def test_list_users():
    with patch("app.api.users.list_users") as mock_list_users:
        mock_list_users.return_value = [
            MagicMock(
                id=1,
                full_name="Test User",
                email="test@example.com",
                is_active=True,
            )
        ]

        response = client.get("/users/")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert "hashed_password" not in response.text
    mock_list_users.assert_called_once()


def test_list_users_passes_pagination():
    with patch("app.api.users.list_users") as mock_list_users:
        mock_list_users.return_value = []

        response = client.get("/users/?skip=20&limit=10")

    assert response.status_code == 200
    mock_list_users.assert_called_once()
    assert mock_list_users.call_args.kwargs == {
        "skip": 20,
        "limit": 10,
    }


@pytest.mark.parametrize(
    "query",
    ["?skip=-1", "?limit=0", "?limit=101"],
)
def test_list_users_rejects_invalid_pagination(query):
    with patch("app.api.users.list_users") as mock_list_users:
        response = client.get(f"/users/{query}")

    assert response.status_code == 422
    mock_list_users.assert_not_called()


def test_list_users_handles_database_error():
    with patch(
        "app.api.users.list_users",
        side_effect=SQLAlchemyError("internal database details"),
    ):
        response = client.get("/users/")

    assert response.status_code == 500
    assert response.json()["detail"] == "Unable to retrieve users."
    assert "internal database details" not in response.text
