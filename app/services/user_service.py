
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate


def _is_duplicate_email_error(exc: IntegrityError) -> bool:
    """Identify PostgreSQL violations of the users email index/constraint."""
    original_error = exc.orig
    diagnostic = getattr(original_error, "diag", None)
    constraint_name = getattr(diagnostic, "constraint_name", None)

    return constraint_name in {
        "ix_users_email",
        "uq_users_email",
        "users_email_key",
    }


def create_user(db: Session, user_data: UserCreate) -> User:
    email = str(user_data.email)

    existing_user = db.scalar(
        select(User).where(User.email == email)
    )
    if existing_user:
        raise ValueError("A user with this email already exists.")

    user = User(
        full_name=user_data.full_name,
        email=email,
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()

        if _is_duplicate_email_error(exc):
            raise ValueError(
                "A user with this email already exists."
            ) from exc

        raise

    return user


def get_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def list_users(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 20,
) -> list[User]:
    statement = (
        select(User)
        .order_by(User.id)
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())
