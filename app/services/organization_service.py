
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.organization_membership import OrganizationMembership
from app.schemas.organization import OrganizationCreate


def create_organization(
    db: Session,
    organization_data: OrganizationCreate,
    owner_id: int,
) -> Organization:
    organization = Organization(
        name=organization_data.name.strip(),
        slug=organization_data.slug,
    )

    try:
        db.add(organization)
        db.flush()

        membership = OrganizationMembership(
            organization_id=organization.id,
            user_id=owner_id,
            role="owner",
        )
        db.add(membership)

        db.commit()
        db.refresh(organization)

    except IntegrityError as exc:
        db.rollback()
        raise ValueError(
            "Unable to create organization. Check the slug and user."
        ) from exc

    return organization



def list_organizations(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 20,
) -> list[Organization]:
    statement = (
        select(Organization)
        .join(
            OrganizationMembership,
            OrganizationMembership.organization_id == Organization.id,
        )
        .where(OrganizationMembership.user_id == user_id)
        .order_by(Organization.id)
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(statement).all())

