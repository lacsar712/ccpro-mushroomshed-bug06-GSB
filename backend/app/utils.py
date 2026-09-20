from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError

from app.models.user import User


def get_current_user(db):
    """Resolve the JWT identity to the current User.

    Login issues tokens with identity=str(user.id); every endpoint must
    resolve that identity the same way so one token maps to one person
    across /me and all write endpoints.
    """
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None
    return db.get(User, user_id)


def validation_error_response(err: ValidationError):
    messages = []
    for field, msgs in err.messages.items():
        if isinstance(msgs, list):
            for m in msgs:
                messages.append(f"{field}: {m}" if field != "_schema" else str(m))
        else:
            messages.append(f"{field}: {msgs}")
    detail = "; ".join(messages) if messages else "请求参数校验失败"
    return jsonify({"detail": detail}), 400
