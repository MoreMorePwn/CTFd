from flask import request
from flask_restx import Namespace, Resource

from CTFd.models import Tickets
from CTFd.utils import get_config
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.utils.tickets import (
    TicketValidationError,
    create_ticket,
    list_ticket_targets,
    list_tickets,
    pending_tickets_for_user,
    serialize_pending_ticket,
    serialize_ticket,
    serialize_ticket_target,
    update_ticket_status,
)
from CTFd.utils.user import get_current_user

tickets_namespace = Namespace("tickets", description="Endpoint to manage Tickets")


def _request_data():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return {}
    return data


def _validation_error(message):
    return {"success": False, "errors": {"ticket": [message]}}


@tickets_namespace.route("")
class TicketList(Resource):
    @admins_only
    def get(self):
        tickets = list_tickets(status=request.args.get("status"))
        return {
            "success": True,
            "data": [serialize_ticket(ticket) for ticket in tickets],
        }

    @admins_only
    def post(self):
        data = _request_data()
        user = get_current_user()
        try:
            ticket = create_ticket(
                target_id=data.get("target_id"),
                title=data.get("title"),
                message=data.get("message"),
                notification_type=data.get("notification_type") or data.get("type"),
                sound=data.get("sound", True),
                created_by_id=user.id if user else None,
            )
        except TicketValidationError as e:
            return _validation_error(str(e)), 400

        return {"success": True, "data": serialize_ticket(ticket)}


@tickets_namespace.route("/targets")
class TicketTargetList(Resource):
    @admins_only
    def get(self):
        targets = list_ticket_targets(query=request.args.get("q"))
        return {
            "success": True,
            "data": [serialize_ticket_target(target) for target in targets],
            "meta": {"mode": get_config("user_mode")},
        }


@tickets_namespace.route("/pending")
class TicketPendingList(Resource):
    @authed_only
    def get(self):
        user = get_current_user()
        tickets = pending_tickets_for_user(user=user)
        return {
            "success": True,
            "data": [serialize_pending_ticket(ticket) for ticket in tickets],
        }


@tickets_namespace.route("/<int:ticket_id>")
@tickets_namespace.param("ticket_id", "A Ticket ID")
class TicketDetail(Resource):
    @admins_only
    def patch(self, ticket_id):
        ticket = Tickets.query.filter_by(id=ticket_id).first_or_404()
        data = _request_data()
        user = get_current_user()
        try:
            update_ticket_status(
                ticket=ticket,
                status=data.get("status"),
                resolve_note=data.get("resolve_note"),
                updated_by_id=user.id if user else None,
            )
        except TicketValidationError as e:
            return _validation_error(str(e)), 400

        return {"success": True, "data": serialize_ticket(ticket)}
