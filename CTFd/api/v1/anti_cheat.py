import datetime

from flask import request
from flask_restx import Namespace, Resource

from CTFd.models import AntiCheatEvents, db
from CTFd.schemas.anti_cheat import AntiCheatEventSchema
from CTFd.utils.decorators import admins_only
from CTFd.utils.user import get_current_user

anti_cheat_namespace = Namespace(
    "anti-cheat", description="Endpoint to retrieve Anti-Cheat Events"
)


def _parse_bool(value):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if str(value).lower() in ("1", "true", "yes"):
        return True
    if str(value).lower() in ("0", "false", "no"):
        return False
    return None


def _filtered_events():
    query = AntiCheatEvents.query
    for field in (
        "type",
        "severity",
        "user_id",
        "team_id",
        "challenge_id",
        "browser_fingerprint",
    ):
        value = request.args.get(field)
        if value not in (None, ""):
            query = query.filter(getattr(AntiCheatEvents, field) == value)

    reviewed = _parse_bool(request.args.get("reviewed"))
    if reviewed is not None:
        query = query.filter(AntiCheatEvents.reviewed == reviewed)

    return query


@anti_cheat_namespace.route("")
class AntiCheatEventList(Resource):
    @admins_only
    def get(self):
        events = (
            _filtered_events()
            .order_by(AntiCheatEvents.created.desc())
            .paginate(max_per_page=100, error_out=False)
        )
        schema = AntiCheatEventSchema("admin", many=True)
        response = schema.dump(events.items)
        if response.errors:
            return {"success": False, "errors": response.errors}, 400

        return {
            "meta": {
                "pagination": {
                    "page": events.page,
                    "next": events.next_num,
                    "prev": events.prev_num,
                    "pages": events.pages,
                    "per_page": events.per_page,
                    "total": events.total,
                }
            },
            "success": True,
            "data": response.data,
        }


@anti_cheat_namespace.route("/<event_id>")
@anti_cheat_namespace.param("event_id", "An Anti-Cheat Event ID")
class AntiCheatEventDetail(Resource):
    @admins_only
    def get(self, event_id):
        event = AntiCheatEvents.query.filter_by(id=event_id).first_or_404()
        response = AntiCheatEventSchema("admin").dump(event)
        if response.errors:
            return {"success": False, "errors": response.errors}, 400
        return {"success": True, "data": response.data}

    @admins_only
    def patch(self, event_id):
        event = AntiCheatEvents.query.filter_by(id=event_id).first_or_404()
        req = request.get_json() or {}
        reviewed = _parse_bool(req.get("reviewed"))
        if reviewed is None:
            return {
                "success": False,
                "errors": {"reviewed": ["Reviewed must be true or false"]},
            }, 400

        user = get_current_user()
        event.reviewed = reviewed
        if reviewed:
            event.reviewer_id = user.id if user else None
            event.reviewed_at = datetime.datetime.utcnow()
        else:
            event.reviewer_id = None
            event.reviewed_at = None
        db.session.commit()

        response = AntiCheatEventSchema("admin").dump(event)
        if response.errors:
            return {"success": False, "errors": response.errors}, 400
        return {"success": True, "data": response.data}
