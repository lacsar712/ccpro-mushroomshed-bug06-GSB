from flask_jwt_extended import get_jwt_identity
from passlib.context import CryptContext

from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def current_user(db) -> User | None:
    """Resolve the user encoded in the request's JWT.

    Login mints tokens whose identity is the user's numeric id
    (see app/routes/auth.py). Every authenticated endpoint must resolve
    identity through this single helper so that the person in the login
    response, /me, and all write endpoints (sheds, rooms, climate logs)
    agree on who the caller is. Returns None when the identity does not
    map to a real user (caller responds 401).
    """
    identity = get_jwt_identity()
    text = str(identity or "").strip()
    if text.startswith("uid:"):
        text = text.split(":", 1)[1]
    if not text:
        return None
    try:
        return db.get(User, int(text))
    except (TypeError, ValueError):
        return db.query(User).filter(User.username == text).first()
