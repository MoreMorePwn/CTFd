import datetime

from CTFd.models import Teams, Tickets, Users, db
from CTFd.utils import get_config

TICKET_STATUS_PENDING = "pending"
TICKET_STATUS_ONGOING = "ongoing"
TICKET_STATUS_RESOLVED = "resolved"
TICKET_STATUSES = {
    TICKET_STATUS_PENDING,
    TICKET_STATUS_ONGOING,
    TICKET_STATUS_RESOLVED,
}
TICKET_NOTIFICATION_TYPES = {"toast", "alert"}


class TicketValidationError(ValueError):
    pass


def is_team_mode():
    return get_config("user_mode") == "teams"


def normalize_status_filter(status):
    if status in (None, "", "all"):
        return None
    if status == "resolve":
        return TICKET_STATUS_RESOLVED
    if status in TICKET_STATUSES:
        return status
    return None


def normalize_notification_type(value):
    if value in TICKET_NOTIFICATION_TYPES:
        return value
    return "toast"


def _target_model():
    return Teams if is_team_mode() else Users


def _target_field_name():
    return "team_id" if is_team_mode() else "user_id"


def _strip_required(value, field):
    value = (value or "").strip()
    if not value:
        raise TicketValidationError("{} is required".format(field))
    return value


def _serialize_datetime(value):
    return value.isoformat() if value else None


def serialize_ticket_target(target):
    return {
        "id": target.id,
        "name": target.name,
        "email": target.email or "",
        "affiliation": target.affiliation or "",
        "hidden": bool(target.hidden),
        "banned": bool(target.banned),
        "bracket": target.bracket.name if target.bracket else "",
    }


def serialize_ticket(ticket):
    target = ticket.team if ticket.team_id else ticket.user
    target_name = target.name if target else "-"
    target_type = "team" if ticket.team_id else "user"
    return {
        "id": ticket.id,
        "title": ticket.title,
        "message": ticket.message,
        "html": str(ticket.html),
        "status": ticket.status,
        "notification_type": ticket.notification_type,
        "sound": bool(ticket.sound),
        "resolve_note": ticket.resolve_note or "",
        "target_id": ticket.team_id or ticket.user_id,
        "target_type": target_type,
        "target_name": target_name,
        "created_by": ticket.created_by.name if ticket.created_by else "",
        "updated_by": ticket.updated_by.name if ticket.updated_by else "",
        "resolved_by": ticket.resolved_by.name if ticket.resolved_by else "",
        "created": _serialize_datetime(ticket.created),
        "updated": _serialize_datetime(ticket.updated),
        "ongoing_at": _serialize_datetime(ticket.ongoing_at),
        "resolved_at": _serialize_datetime(ticket.resolved_at),
    }


def serialize_pending_ticket(ticket):
    return {
        "id": ticket.id,
        "title": ticket.title,
        "content": ticket.message,
        "html": str(ticket.html),
        "type": ticket.notification_type,
        "sound": bool(ticket.sound),
    }


def serialize_ticket_event(ticket):
    data = serialize_pending_ticket(ticket)
    data.update(
        {
            "target_id": ticket.team_id or ticket.user_id,
            "target_type": "team" if ticket.team_id else "user",
        }
    )
    return data


def list_ticket_targets(query=None):
    model = _target_model()
    targets = model.query.order_by(model.name.asc()).all()
    if query:
        query = query.lower()
        targets = [
            target
            for target in targets
            if query in (target.name or "").lower()
            or query in (target.email or "").lower()
            or query in (target.affiliation or "").lower()
        ]
    return targets


def list_tickets(status=None):
    status = normalize_status_filter(status)
    query = Tickets.query
    if status:
        query = query.filter_by(status=status)
    return query.order_by(Tickets.id.desc()).all()


def create_ticket(
    target_id,
    title,
    message,
    notification_type="toast",
    sound=True,
    created_by_id=None,
):
    target = _target_model().query.filter_by(id=target_id).first()
    if target is None:
        raise TicketValidationError("User or team not found")

    ticket = Tickets(
        title=_strip_required(title, "Title"),
        message=_strip_required(message, "Message"),
        status=TICKET_STATUS_PENDING,
        notification_type=normalize_notification_type(notification_type),
        sound=bool(sound),
        created_by_id=created_by_id,
        updated_by_id=created_by_id,
        created=datetime.datetime.utcnow(),
        updated=datetime.datetime.utcnow(),
    )
    setattr(ticket, _target_field_name(), target.id)
    db.session.add(ticket)
    db.session.commit()
    return ticket


def update_ticket_status(ticket, status, resolve_note=None, updated_by_id=None):
    status = normalize_status_filter(status)
    if status not in (TICKET_STATUS_ONGOING, TICKET_STATUS_RESOLVED):
        raise TicketValidationError("Invalid ticket status")

    if ticket.status == TICKET_STATUS_RESOLVED:
        raise TicketValidationError("Resolved tickets cannot be changed")

    now = datetime.datetime.utcnow()
    if status == TICKET_STATUS_ONGOING:
        if ticket.status != TICKET_STATUS_PENDING:
            raise TicketValidationError("Only pending tickets can become ongoing")
        ticket.status = TICKET_STATUS_ONGOING
        ticket.ongoing_at = now
        ticket.updated_by_id = updated_by_id
        ticket.updated = now
    elif status == TICKET_STATUS_RESOLVED:
        if ticket.status != TICKET_STATUS_ONGOING:
            raise TicketValidationError("Only ongoing tickets can be resolved")
        ticket.resolve_note = _strip_required(resolve_note, "Resolve note")
        ticket.status = TICKET_STATUS_RESOLVED
        ticket.resolved_at = now
        ticket.resolved_by_id = updated_by_id
        ticket.updated_by_id = updated_by_id
        ticket.updated = now

    db.session.commit()
    return ticket


def pending_tickets_for_user(user):
    if user is None:
        return []

    if is_team_mode():
        if not user.team_id:
            return []
        return (
            Tickets.query.filter_by(
                team_id=user.team_id,
                status=TICKET_STATUS_PENDING,
            )
            .order_by(Tickets.id.asc())
            .all()
        )

    return (
        Tickets.query.filter_by(user_id=user.id, status=TICKET_STATUS_PENDING)
        .order_by(Tickets.id.asc())
        .all()
    )
