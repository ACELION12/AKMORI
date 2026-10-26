
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import jwt
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.db.dependencies import get_db
from app.main import app
from app.services.auth_service import (
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
    create_access_token,
    get_user_id_from_token,
)

client = TestClient(app)


def test_login_success():
    user = MagicMock(id=1)

    with (
        patch("app.api.auth.authenticate_user", return_value=user),
        patch(
            "app.api.auth.create_access_token",
            return_value="test-access-token",
        ),
    ):
        response = client.post(
            "/auth/login",
            data={
                "username": "test@example.com",
                "password": "StrongPass123!",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "test-access-token",
        "token_type": "bearer",
    }


def test_login_rejects_invalid_credentials():
    with patch("app.api.auth.authenticate_user", return_value=None):
        response = client.post(
            "/auth/login",
            data={
                "username": "test@example.com",
                "password": "WrongPassword123!",
            },
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password."


def test_missing_token_rejected():
    response = client.get("/users/me")

    assert response.status_code == 401


def test_invalid_token_rejected():
    response = client.get(
        "/users/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_expired_token_rejected():
    expired_payload = {
        "sub": "1",
        "iat": datetime.now(timezone.utc) - timedelta(minutes=10),
        "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
    }
    token = jwt.encode(
        expired_payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

    assert get_user_id_from_token(token) is None

    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_valid_token_returns_current_user():
    user = MagicMock(
        id=1,
        full_name="Test User",
        email="test@example.com",
        is_active=True,
    )
    token = create_access_token(user)

    db = MagicMock()
    db.get.return_value = user

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: db

    try:
        response = client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)

    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["email"] == "test@example.com"
    assert "hashed_password" not in response.json()


def test_inactive_user_rejected():
    user = MagicMock(is_active=False)

    with patch(
        "app.api.dependencies.get_user_id_from_token",
        return_value=1,
    ):
        db = MagicMock()
        db.get.return_value = user

        previous_overrides = app.dependency_overrides.copy()
        app.dependency_overrides[get_db] = lambda: db

        try:
            response = client.get(
                "/users/me",
                headers={"Authorization": "Bearer valid-shaped-token"},
            )
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(previous_overrides)

    assert response.status_code == 401
