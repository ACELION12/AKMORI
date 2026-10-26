import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
)

if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is not configured.")

password_hash = PasswordHash.recommended()


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> User | None:
    user = db.scalar(select(User).where(User.email == email))

    if user is None or not user.is_active:
        return None

    if not password_hash.verify(password, user.hashed_password):
        return None

    return user


def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user.id),
        "iat": now,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def get_user_id_from_token(token: str) -> int | None:
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )
        subject = payload.get("sub")

        if not isinstance(subject, str):
            return None

        user_id = int(subject)
        return user_id if user_id > 0 else None

    except (jwt.InvalidTokenError, ValueError, TypeError):
        return None