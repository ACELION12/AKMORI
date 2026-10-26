
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import get_current_user
from app.db.dependencies import get_db
from app.main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def override_database_dependency():
    previous_overrides = app.dependency_overrides.copy()

    def override_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = override_get_db

    yield

    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous_overrides)


@pytest.fixture
def authenticated_user():
    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_current_user] = lambda: MagicMock(
        id=1,
        is_active=True,
    )

    yield

    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous_overrides)



def test_create_organization(authenticated_user):
    organization = SimpleNamespace(
        id=1,
        name="AKMORI Labs",
        slug="akmori-labs",
        is_active=True,
        created_at=datetime(
            2026, 10, 26, 10, 0, tzinfo=timezone.utc
        ),
    )

    with patch(
        "app.api.organizations.create_organization",
        return_value=organization,
    ) as mock_create:
        response = client.post(
            "/organizations/",
            json={
                "name": "AKMORI Labs",
                "slug": "akmori-labs",
            },
        )

    assert response.status_code == 201
    assert response.json()["name"] == "AKMORI Labs"
    assert response.json()["slug"] == "akmori-labs"

    _, kwargs = mock_create.call_args
    assert kwargs["owner_id"] == 1



@pytest.mark.parametrize(
    "payload",
    [
        {"name": "A", "slug": "akmori"},
        {"name": "AKMORI Labs", "slug": "AKMORI"},
        {"name": "AKMORI Labs", "slug": "akmori labs"},
        {"name": "AKMORI Labs", "slug": "-akmori"},
    ],
)
def test_create_organization_rejects_invalid_input(
    authenticated_user,
    payload,
):
    with patch(
        "app.api.organizations.create_organization"
    ) as mock_create:
        response = client.post("/organizations/", json=payload)

    assert response.status_code == 422
    mock_create.assert_not_called()


def test_create_organization_rejects_duplicate_slug(
    authenticated_user,
):
    with patch(
        "app.api.organizations.create_organization",
        side_effect=ValueError(
            "An organization with this slug already exists."
        ),
    ):
        response = client.post(
            "/organizations/",
            json={
                "name": "AKMORI Labs",
                "slug": "akmori-labs",
            },
        )

    assert response.status_code == 409


def test_list_organizations(authenticated_user):
    organization = SimpleNamespace(
        id=1,
        name="AKMORI Labs",
        slug="akmori-labs",
        is_active=True,
        created_at=datetime(
            2026, 10, 26, 10, 0, tzinfo=timezone.utc
        ),
    )

    with patch(
        "app.api.organizations.list_organizations",
        return_value=[organization],
    ):
        response = client.get("/organizations/")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "AKMORI Labs"
    assert response.json()[0]["slug"] == "akmori-labs"



def test_list_organizations_passes_pagination(
    authenticated_user,
):
    with patch(
        "app.api.organizations.list_organizations",
        return_value=[],
    ) as mock_list:
        response = client.get(
            "/organizations/?skip=20&limit=10"
        )

    assert response.status_code == 200
    mock_list.assert_called_once()

    _, kwargs = mock_list.call_args
    assert kwargs["user_id"] == 1
    assert kwargs["skip"] == 20
    assert kwargs["limit"] == 10


def test_list_organizations_passes_authenticated_user_id(
    authenticated_user,
):
    with patch(
        "app.api.organizations.list_organizations",
        return_value=[],
    ) as mock_list:
        response = client.get("/organizations/")

    assert response.status_code == 200

    _, kwargs = mock_list.call_args
    assert kwargs["user_id"] == 1


@pytest.mark.parametrize(
    "query",
    ["?skip=-1", "?limit=0", "?limit=101"],
)
def test_list_organizations_rejects_invalid_pagination(
    authenticated_user,
    query,
):
    with patch(
        "app.api.organizations.list_organizations"
    ) as mock_list:
        response = client.get(f"/organizations/{query}")

    assert response.status_code == 422
    mock_list.assert_not_called()


def test_organizations_reject_missing_token():
    response = client.get("/organizations/")

    assert response.status_code == 401


def test_list_organizations_handles_database_error(
    authenticated_user,
):
    with patch(
        "app.api.organizations.list_organizations",
        side_effect=SQLAlchemyError("private database details"),
    ):
        response = client.get("/organizations/")

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Unable to retrieve organizations."
    )
    assert "private database details" not in response.text
