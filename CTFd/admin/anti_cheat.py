import datetime

from flask import redirect, render_template, request, url_for

from CTFd.admin import admin
from CTFd.models import AntiCheatEvents, db
from CTFd.utils.decorators import admins_only
from CTFd.utils.user import get_current_user


def _parse_reviewed(value):
    if value == "open":
        return False
    if value == "reviewed":
        return True
    return None


def _filtered_events():
    query = AntiCheatEvents.query

    event_type = request.args.get("type")
    if event_type:
        query = query.filter(AntiCheatEvents.type == event_type)

    severity = request.args.get("severity")
    if severity:
        query = query.filter(AntiCheatEvents.severity == severity)

    reviewed = _parse_reviewed(request.args.get("reviewed"))
    if reviewed is not None:
        query = query.filter(AntiCheatEvents.reviewed == reviewed)

    return query


@admin.route("/admin/anti-cheat", methods=["GET"])
@admins_only
def anti_cheat():
    page = abs(request.args.get("page", 1, type=int))

    base_query = AntiCheatEvents.query
    events = (
        _filtered_events()
        .order_by(AntiCheatEvents.created.desc())
        .paginate(page=page, per_page=50, error_out=False)
    )

    event_types = [
        event_type
        for (event_type,) in db.session.query(AntiCheatEvents.type)
        .distinct()
        .order_by(AntiCheatEvents.type.asc())
        .all()
    ]

    args = dict(request.args)
    args.pop("page", 1)

    return render_template(
        "admin/anti_cheat.html",
        events=events,
        event_types=event_types,
        selected_type=request.args.get("type", ""),
        selected_severity=request.args.get("severity", ""),
        selected_reviewed=request.args.get("reviewed", ""),
        total_count=base_query.count(),
        open_count=base_query.filter_by(reviewed=False).count(),
        high_count=base_query.filter_by(severity="high", reviewed=False).count(),
        medium_count=base_query.filter_by(severity="medium", reviewed=False).count(),
        prev_page=url_for(request.endpoint, page=events.prev_num, **args),
        next_page=url_for(request.endpoint, page=events.next_num, **args),
    )


@admin.route("/admin/anti-cheat/<int:event_id>/review", methods=["POST"])
@admins_only
def anti_cheat_review(event_id):
    event = AntiCheatEvents.query.filter_by(id=event_id).first_or_404()
    reviewed = request.form.get("reviewed") == "true"
    user = get_current_user()

    event.reviewed = reviewed
    if reviewed:
        event.reviewer_id = user.id if user else None
        event.reviewed_at = datetime.datetime.utcnow()
    else:
        event.reviewer_id = None
        event.reviewed_at = None
    db.session.commit()

    next_url = request.form.get("next")
    anti_cheat_path = url_for("admin.anti_cheat")
    if next_url and next_url.startswith(anti_cheat_path):
        return redirect(next_url)

    return redirect(anti_cheat_path)
