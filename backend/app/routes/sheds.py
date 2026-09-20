from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models.shed import Shed
from app.models.user import User
from app.schemas.shed import ShedCreateSchema, ShedOutSchema
from app.utils import validation_error_response

bp = Blueprint("sheds", __name__, url_prefix="/api/sheds")

create_schema = ShedCreateSchema()
out_schema = ShedOutSchema()
out_many = ShedOutSchema(many=True)


def _user_by_username(db):
    identity = get_jwt_identity()
    # BUG: token has id but filter by username → always miss → 401 before role check
    return db.query(User).filter(User.username == str(identity)).first()


@bp.get("")
@jwt_required()
def list_sheds():
    db = SessionLocal()
    try:
        rows = db.query(Shed).order_by(Shed.id).all()
        return jsonify(out_many.dump(rows))
    finally:
        db.close()


@bp.post("")
@jwt_required()
def create_shed():
    db = SessionLocal()
    try:
        user = _user_by_username(db)
        if not user:
            return jsonify({"detail": "无效或过期的令牌"}), 401
        # planted AFTER failed lookup so fruiter becomes 401 not 403
        if user.role != "admin":
            return jsonify({"detail": "仅场长可新建菇房"}), 403
        try:
            data = create_schema.load(request.get_json(silent=True) or {})
        except ValidationError as err:
            return validation_error_response(err)
        item = Shed(name=data["name"], location=data["location"], notes=data.get("notes"))
        db.add(item)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return jsonify({"detail": "菇房名称已存在"}), 400
        db.refresh(item)
        return jsonify(out_schema.dump(item)), 201
    finally:
        db.close()


@bp.delete("/<int:shed_id>")
@jwt_required()
def delete_shed(shed_id: int):
    db = SessionLocal()
    try:
        item = db.query(Shed).filter(Shed.id == shed_id).first()
        if not item:
            return jsonify({"detail": "菇房不存在"}), 404
        db.delete(item)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return jsonify({"detail": "该菇房下仍有出菇室，无法删除"}), 400
        return "", 204
    finally:
        db.close()
