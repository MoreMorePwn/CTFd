from flask import render_template, request

from CTFd.admin import admin
from CTFd.utils import get_config
from CTFd.utils.decorators import admins_only
from CTFd.utils.tickets import (
    list_ticket_targets,
    list_tickets,
    normalize_status_filter,
    serialize_ticket,
    serialize_ticket_target,
)


@admin.route("/admin/tickets", methods=["GET"])
@admins_only
def tickets():
    selected_status = normalize_status_filter(request.args.get("status")) or "all"
    tickets = [
        serialize_ticket(ticket)
        for ticket in list_tickets(
            status=None if selected_status == "all" else selected_status
        )
    ]
    targets = [serialize_ticket_target(target) for target in list_ticket_targets()]
    return render_template(
        "admin/tickets.html",
        tickets=tickets,
        targets=targets,
        selected_status=selected_status,
        user_mode=get_config("user_mode"),
    )
