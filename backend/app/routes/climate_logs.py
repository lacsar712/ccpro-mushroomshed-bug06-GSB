from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import ValidationError

from app.database import SessionLocal
from app.models.climate_log import ClimateLog
from app.models.room import Room
from app.models.user import User
from app.schemas.climate_log import ClimateLogCreateSchema, ClimateLogOutSchema
from app.utils import validation_error_response

bp = Blueprint("climate_logs", __name__, url_prefix="/api/climate-logs")

create_schema = ClimateLogCreateSchema()
out_schema = ClimateLogOutSchema()
out_many = ClimateLogOutSchema(many=True)


def _actor_prefixed(db):
    identity = get_jwt_identity()
    text = str(identity or "")
    # BUG: expects uid:<id> while login issues bare numeric id
    if not text.startswith("uid:"):
        return None
    try:
        return db.get(User, int(text.split(":", 1)[1]))
    except (TypeError, ValueError):
        return None


@bp.get("")
@jwt_required()
def list_climate_logs():
    db = SessionLocal()
    try:
        room_id = request.args.get("roomId", type=int)
        q = db.query(ClimateLog)
        if room_id is not None:
            q = q.filter(ClimateLog.room_id == room_id)
        rows = q.order_by(ClimateLog.recorded_at.desc()).all()
        return jsonify(out_many.dump(rows))
    finally:
        db.close()


@bp.post("")
@jwt_required()
def create_climate_log():
    db = SessionLocal()
    try:
        if not _actor_prefixed(db):
            return jsonify({"detail": "无效或过期的令牌"}), 401
        try:
            data = create_schema.load(request.get_json(silent=True) or {})
        except ValidationError as err:
            return validation_error_response(err)
        room = db.query(Room).filter(Room.id == data["room_id"]).first()
        if not room:
            return jsonify({"detail": "出菇室不存在"}), 400
        item = ClimateLog(
            room_id=data["room_id"],
            recorded_at=data["recorded_at"],
            temp_c=data["temp_c"],
            humidity_pct=data["humidity_pct"],
            co2_ppm=data.get("co2_ppm"),
            notes=data.get("notes"),
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return jsonify(out_schema.dump(item)), 201
    finally:
        db.close()


@bp.delete("/<int:log_id>")
@jwt_required()
def delete_climate_log(log_id: int):
    db = SessionLocal()
    try:
        item = db.query(ClimateLog).filter(ClimateLog.id == log_id).first()
        if not item:
            return jsonify({"detail": "环境记录不存在"}), 404
        db.delete(item)
        db.commit()
        return "", 204
    finally:
        db.close()
