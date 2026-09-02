from flask import request
from flask_restx import Namespace, Resource

from CTFd.utils.announcer_bot import (
    build_announcer_template,
    get_announcer_settings,
    list_announcer_logs,
    save_announcer_settings,
)
from CTFd.utils.decorators import admins_only

announcer_bot_namespace = Namespace(
    "announcer-bot", description="Endpoint to manage announcer bot settings"
)


@announcer_bot_namespace.route("")
class AnnouncerBotConfig(Resource):
    @admins_only
    def get(self):
        return {"success": True, "data": get_announcer_settings(include_webhook=False)}

    @admins_only
    def patch(self):
        success, errors = save_announcer_settings(request.get_json() or {})
        if not success:
            return {"success": False, "errors": errors}, 400
        return {"success": True, "data": get_announcer_settings(include_webhook=False)}


@announcer_bot_namespace.route("/template")
class AnnouncerBotTemplate(Resource):
    @admins_only
    def post(self):
        settings = get_announcer_settings(include_webhook=False)
        settings.update(request.get_json() or {})
        return {"success": True, "data": build_announcer_template(settings)}


@announcer_bot_namespace.route("/logs")
class AnnouncerBotLogs(Resource):
    @admins_only
    def get(self):
        return {"success": True, "data": list_announcer_logs()}
