
from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.organization import Organization
from app.models.organization_membership import OrganizationMembership
from app.schemas.organization import OrganizationCreate
from app.services.organization_service import (
    create_organization,
    list_organizations,
)


def test_list_organizations_filters_by_user_membership():
    db = MagicMock()
    db.scalars.return_value.all.return_value = []

    result = list_organizations(
        db,
        user_id=7,
        skip=0,
        limit=20,
    )

    assert result == []

    statement = db.scalars.call_args.args[0]
    compiled = statement.compile(
        compile_kwargs={"literal_binds": True}
    )
    sql = str(compiled)

    assert "JOIN organization_memberships" in sql
    assert "organization_memberships.user_id = 7" in sql


def test_create_organization_assigns_owner():
    db = MagicMock()
    db.flush.side_effect = lambda: setattr(
        db.add.call_args.args[0],
        "id",
        12,
    )

    organization = Organization(
        id=12,
        name="AKMORI Labs",
        slug="akmori-labs",
    )
    organization.created_at = datetime.now(timezone.utc)

    with patch(
        "app.services.organization_service.Organization",
        return_value=organization,
    ):
        result = create_organization(
            db,
            OrganizationCreate(
                name="AKMORI Labs",
                slug="akmori-labs",
            ),
            owner_id=7,
        )

    assert result is organization

    added_objects = [
        item.args[0] for item in db.add.call_args_list
    ]
    membership = next(
        item
        for item in added_objects
        if isinstance(item, OrganizationMembership)
    )

    assert membership.organization_id == 12
    assert membership.user_id == 7
    assert membership.role == "owner"
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(organization)


def test_create_organization_rolls_back_on_integrity_error():
    db = MagicMock()
    db.flush.side_effect = IntegrityError(
        "INSERT",
        {},
        Exception("constraint violation"),
    )

    with pytest.raises(ValueError, match="Unable to create organization"):
        create_organization(
            db,
            OrganizationCreate(
                name="AKMORI Labs",
                slug="akmori-labs",
            ),
            owner_id=7,
        )

    db.rollback.assert_called_once()
    db.commit.assert_not_called()
