import secrets

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models import Prodi, User

# Used only to equalize bcrypt work for unknown accounts; never an account credential.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(24))


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))
    valid = verify_password(password, user.password_hash if user else _DUMMY_HASH)
    if not user or not valid or not user.aktif:
        return None
    prodi = db.get(Prodi, user.prodi_id)
    if prodi is None or not prodi.aktif:
        return None
    return user


def revoke_all_tokens(db: Session, user: User) -> None:
    # Atomic increment also invalidates tokens issued by other browser sessions.
    db.execute(update(User).where(User.id == user.id).values(token_version=User.token_version + 1))
    db.commit()
