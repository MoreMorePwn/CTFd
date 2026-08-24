import datetime
import json
import math
import re
from collections import defaultdict
from io import BytesIO
from pathlib import Path

from flask import current_app

from CTFd.models import (
    Awards,
    Brackets,
    Challenges,
    PostRevokeCalcAccounts,
    PostRevokeCalcAwards,
    PostRevokeCalcSolves,
    Solves,
    Teams,
    Users,
    db,
)
from CTFd.plugins.challenges.decay import DECAY_FUNCTIONS
from CTFd.utils import config as ctf_config
from CTFd.utils import get_config


ACCOUNT_TYPE_TEAMS = "team"
ACCOUNT_TYPE_USERS = "user"
POST_REVOKE_TABLES = {
    "post_revoke_calc_accounts",
    "post_revoke_calc_solves",
    "post_revoke_calc_awards",
}


def is_team_mode():
    return get_config("user_mode") == "teams"


def get_account_type():
    return ACCOUNT_TYPE_TEAMS if is_team_mode() else ACCOUNT_TYPE_USERS


def get_account_model():
    return Teams if is_team_mode() else Users


def get_account_id_field(model=None):
    if model is None:
        model = get_account_model()
    return Solves.team_id if model is Teams else Solves.user_id


def get_award_account_id_field(model=None):
    if model is None:
        model = get_account_model()
    return Awards.team_id if model is Teams else Awards.user_id


def normalize_bracket_id(value):
    if value in (None, "", "all"):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def clamp_percentage(value):
    if value in (None, ""):
        return 100.0
    try:
        percentage = float(value)
    except (TypeError, ValueError):
        raise ValueError("Percentage must be a number")
    if percentage < 0 or percentage > 100:
        raise ValueError("Percentage must be between 0 and 100")
    return percentage


def score_value(value):
    value = float(value or 0)
    rounded = round(value, 2)
    if rounded == int(rounded):
        return int(rounded)
    return rounded


def format_score(value):
    value = score_value(value)
    if isinstance(value, int):
        return str(value)
    return f"{value:.2f}".rstrip("0").rstrip(".")


def get_brackets_for_current_mode():
    bracket_type = "teams" if is_team_mode() else "users"
    return Brackets.query.filter_by(type=bracket_type).order_by(Brackets.name.asc()).all()


def _account_query(bracket_id=None):
    model = get_account_model()
    query = model.query.filter(model.hidden == False)
    if bracket_id is not None:
        query = query.filter(model.bracket_id == bracket_id)
    return query.order_by(model.name.asc())


def _load_account_states(account_type):
    return {
        state.account_id: state
        for state in PostRevokeCalcAccounts.query.filter_by(
            account_type=account_type
        ).all()
    }


def _load_solve_states():
    return {state.solve_id: state for state in PostRevokeCalcSolves.query.all()}


def _load_award_states():
    return {state.award_id: state for state in PostRevokeCalcAwards.query.all()}


def get_account_state(account_type, account_id, create=False):
    state = PostRevokeCalcAccounts.query.filter_by(
        account_type=account_type,
        account_id=account_id,
    ).first()
    if state is None and create:
        state = PostRevokeCalcAccounts(
            account_type=account_type,
            account_id=account_id,
            manual_banned=False,
            note="",
        )
        db.session.add(state)
    return state


def get_solve_state(solve_id, create=False):
    state = PostRevokeCalcSolves.query.filter_by(solve_id=solve_id).first()
    if state is None and create:
        state = PostRevokeCalcSolves(solve_id=solve_id, percentage=100.0, revoked=False)
        db.session.add(state)
    return state


def get_award_state(award_id, create=False):
    state = PostRevokeCalcAwards.query.filter_by(award_id=award_id).first()
    if state is None and create:
        state = PostRevokeCalcAwards(award_id=award_id, percentage=100.0, revoked=False)
        db.session.add(state)
    return state


def update_account_state(account_id, manual_banned=None, note=None):
    account_type = get_account_type()
    account = get_account_model().query.filter_by(id=account_id).first_or_404()
    state = get_account_state(account_type, account.id, create=True)
    if manual_banned is not None:
        state.manual_banned = bool(manual_banned)
    if note is not None:
        state.note = str(note)
    db.session.commit()
    return state


def update_solve_state(solve_id, percentage=None, revoked=None, note=None):
    Solves.query.filter_by(id=solve_id).first_or_404()
    state = get_solve_state(solve_id, create=True)
    if percentage is not None:
        state.percentage = clamp_percentage(percentage)
        if state.percentage == 0:
            state.revoked = True
    if revoked is not None:
        state.revoked = bool(revoked)
        if state.revoked:
            state.percentage = 0.0
        elif state.percentage == 0:
            state.percentage = 100.0
    if note is not None:
        state.note = str(note)
    db.session.commit()
    return state


def update_award_state(award_id, percentage=None, revoked=None, note=None):
    Awards.query.filter_by(id=award_id).first_or_404()
    state = get_award_state(award_id, create=True)
    if percentage is not None:
        state.percentage = clamp_percentage(percentage)
        if state.percentage == 0:
            state.revoked = True
    if revoked is not None:
        state.revoked = bool(revoked)
        if state.revoked:
            state.percentage = 0.0
        elif state.percentage == 0:
            state.percentage = 100.0
    if note is not None:
        state.note = str(note)
    db.session.commit()
    return state


def _effective_account_banned(account, state):
    return bool(account.banned or (state and state.manual_banned))


def _state_percentage(state):
    if state is None:
        return 100.0
    return clamp_percentage(state.percentage)


def _state_revoked(state):
    if state is None:
        return False
    return bool(state.revoked or clamp_percentage(state.percentage) == 0)


def _simulated_dynamic_value(challenge, solve_count):
    if challenge.function not in DECAY_FUNCTIONS:
        return float(challenge.value or 0)

    initial = float(challenge.initial or challenge.value or 0)
    minimum = float(challenge.minimum or 0)
    decay = float(challenge.decay or 1)
    adjusted_count = solve_count - 1 if solve_count else 0

    if challenge.function == "linear":
        value = initial - (decay * adjusted_count)
    else:
        if decay == 0:
            decay = 1
        value = (((minimum - initial) / (decay**2)) * (adjusted_count**2)) + initial

    value = math.ceil(value)
    if value < minimum:
        value = minimum
    return float(value)


def _date_for_sort(items):
    if not items:
        return datetime.datetime.max
    dates = [item.date for item in items if item.date]
    return max(dates) if dates else datetime.datetime.max


def calculate_post_revoke(bracket_id=None, sort_by="pre"):
    bracket_id = normalize_bracket_id(bracket_id)
    account_type = get_account_type()
    account_model = get_account_model()
    solve_account_field = get_account_id_field(account_model)
    award_account_field = get_award_account_id_field(account_model)

    accounts = _account_query(bracket_id=bracket_id).all()
    account_map = {account.id: account for account in accounts}
    account_ids = list(account_map.keys())
    account_states = _load_account_states(account_type)
    solve_states = _load_solve_states()
    award_states = _load_award_states()

    solves = []
    awards = []
    if account_ids:
        solves = (
            Solves.query.filter(solve_account_field.in_(account_ids))
            .join(Challenges)
            .order_by(Solves.date.asc(), Solves.id.asc())
            .all()
        )
        awards = (
            Awards.query.filter(award_account_field.in_(account_ids))
            .order_by(Awards.date.asc(), Awards.id.asc())
            .all()
        )

    solves_by_account = defaultdict(list)
    awards_by_account = defaultdict(list)
    solves_by_challenge = defaultdict(list)
    challenge_map = {}

    for solve in solves:
        account_id = solve.team_id if is_team_mode() else solve.user_id
        if account_id not in account_map:
            continue
        solves_by_account[account_id].append(solve)
        solves_by_challenge[solve.challenge_id].append(solve)
        challenge_map[solve.challenge_id] = solve.challenge

    for award in awards:
        account_id = award.team_id if is_team_mode() else award.user_id
        if account_id in account_map:
            awards_by_account[account_id].append(award)

    effective_banned = {
        account_id: _effective_account_banned(account, account_states.get(account_id))
        for account_id, account in account_map.items()
    }

    simulated_challenge_values = {}
    for challenge_id, challenge_solves in solves_by_challenge.items():
        valid_accounts = set()
        for solve in challenge_solves:
            account_id = solve.team_id if is_team_mode() else solve.user_id
            if effective_banned.get(account_id):
                continue
            state = solve_states.get(solve.id)
            if _state_revoked(state):
                continue
            valid_accounts.add(account_id)

        challenge = challenge_map[challenge_id]
        simulated_challenge_values[challenge_id] = _simulated_dynamic_value(
            challenge,
            len(valid_accounts),
        )

    rows = []
    detail_map = {}
    for account in accounts:
        state = account_states.get(account.id)
        account_solves = solves_by_account.get(account.id, [])
        account_awards = awards_by_account.get(account.id, [])

        pre_score = sum(float(solve.challenge.value or 0) for solve in account_solves)
        pre_score += sum(float(award.value or 0) for award in account_awards)

        solve_details = []
        award_details = []
        post_score = 0.0
        calc_banned = effective_banned.get(account.id, False)

        for solve in account_solves:
            solve_state = solve_states.get(solve.id)
            percentage = _state_percentage(solve_state)
            revoked = _state_revoked(solve_state)
            challenge_value = simulated_challenge_values.get(
                solve.challenge_id,
                float(solve.challenge.value or 0),
            )
            post_value = 0.0
            if calc_banned is False and revoked is False:
                post_value = challenge_value * (percentage / 100)
                post_score += post_value

            solve_details.append(
                {
                    "id": solve.id,
                    "challenge_id": solve.challenge_id,
                    "challenge_name": solve.challenge.name,
                    "original_score": score_value(solve.challenge.value),
                    "post_challenge_score": score_value(challenge_value),
                    "post_score": score_value(post_value),
                    "percentage": percentage,
                    "revoked": revoked,
                    "note": solve_state.note if solve_state else "",
                    "date": solve.date.isoformat() if solve.date else None,
                }
            )

        for award in account_awards:
            award_state = award_states.get(award.id)
            percentage = _state_percentage(award_state)
            revoked = _state_revoked(award_state)
            post_value = 0.0
            if calc_banned is False and revoked is False:
                post_value = float(award.value or 0) * (percentage / 100)
                post_score += post_value

            award_details.append(
                {
                    "id": award.id,
                    "name": award.name or "Award",
                    "category": award.category or "",
                    "description": award.description or "",
                    "original_score": score_value(award.value),
                    "post_score": score_value(post_value),
                    "percentage": percentage,
                    "revoked": revoked,
                    "note": award_state.note if award_state else "",
                    "date": award.date.isoformat() if award.date else None,
                }
            )

        if pre_score == 0 and post_score == 0 and not state:
            continue

        row = {
            "account_id": account.id,
            "account_type": account_type,
            "name": account.name,
            "bracket_id": account.bracket_id,
            "bracket": account.bracket.name if account.bracket else "",
            "pre_score": score_value(pre_score),
            "post_score": score_value(0 if calc_banned else post_score),
            "real_banned": bool(account.banned),
            "manual_banned": bool(state.manual_banned) if state else False,
            "calc_banned": bool(calc_banned),
            "note": state.note if state else "",
            "last_activity": _date_for_sort(account_solves + account_awards),
            "solve_count": len(account_solves),
            "award_count": len(account_awards),
        }
        rows.append(row)
        detail_map[account.id] = {
            "account": row,
            "solves": solve_details,
            "awards": award_details,
        }

    post_ranked = sorted(
        rows,
        key=lambda row: (
            -float(row["post_score"] or 0),
            -float(row["pre_score"] or 0),
            row["last_activity"],
            row["name"].lower(),
        ),
    )
    for rank, row in enumerate(post_ranked, start=1):
        row["rank"] = rank

    if sort_by == "post":
        sorted_rows = post_ranked
    elif sort_by == "name":
        sorted_rows = sorted(rows, key=lambda row: row["name"].lower())
    else:
        sorted_rows = sorted(
            rows,
            key=lambda row: (
                -float(row["pre_score"] or 0),
                row["last_activity"],
                row["name"].lower(),
            ),
        )

    for row in rows:
        row["pre_score_display"] = format_score(row["pre_score"])
        row["post_score_display"] = format_score(row["post_score"])
        last_activity = row.get("last_activity")
        row["last_activity"] = (
            last_activity.isoformat()
            if last_activity and last_activity != datetime.datetime.max
            else None
        )

    return {
        "mode": get_config("user_mode"),
        "account_type": account_type,
        "rows": sorted_rows,
        "details": detail_map,
        "bracket_id": bracket_id,
        "brackets": get_brackets_for_current_mode(),
    }


def get_account_detail(account_id, bracket_id=None):
    data = calculate_post_revoke(bracket_id=bracket_id)
    try:
        account_id = int(account_id)
    except (TypeError, ValueError):
        return None
    return data["details"].get(account_id)


def export_state_data():
    def serialize_datetime(value):
        return value.isoformat() if value else None

    return {
        "version": 1,
        "created": datetime.datetime.utcnow().isoformat(),
        "ctf_name": ctf_config.ctf_name(),
        "accounts": [
            {
                "id": row.id,
                "account_type": row.account_type,
                "account_id": row.account_id,
                "manual_banned": bool(row.manual_banned),
                "note": row.note,
                "created": serialize_datetime(row.created),
                "updated": serialize_datetime(row.updated),
            }
            for row in PostRevokeCalcAccounts.query.order_by(
                PostRevokeCalcAccounts.id.asc()
            )
        ],
        "solves": [
            {
                "id": row.id,
                "solve_id": row.solve_id,
                "percentage": row.percentage,
                "revoked": bool(row.revoked),
                "note": row.note,
                "created": serialize_datetime(row.created),
                "updated": serialize_datetime(row.updated),
            }
            for row in PostRevokeCalcSolves.query.order_by(PostRevokeCalcSolves.id.asc())
        ],
        "awards": [
            {
                "id": row.id,
                "award_id": row.award_id,
                "percentage": row.percentage,
                "revoked": bool(row.revoked),
                "note": row.note,
                "created": serialize_datetime(row.created),
                "updated": serialize_datetime(row.updated),
            }
            for row in PostRevokeCalcAwards.query.order_by(PostRevokeCalcAwards.id.asc())
        ],
    }


def backup_state_before_reset():
    export_dir = Path(current_app.root_path).parent / ".export" / "post_revoke_calc"
    export_dir.mkdir(parents=True, exist_ok=True)

    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", ctf_config.ctf_name()).strip("_")
    if not safe_name:
        safe_name = "ctfd"
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    target = export_dir / f"{safe_name}.post_revoke_calc.{timestamp}.json"
    target.write_text(json.dumps(export_state_data(), indent=2, sort_keys=True))
    return target


def reset_state_with_backup():
    backup_path = backup_state_before_reset()
    PostRevokeCalcAwards.query.delete()
    PostRevokeCalcSolves.query.delete()
    PostRevokeCalcAccounts.query.delete()
    db.session.commit()
    return backup_path


def build_pdf(bracket_id=None):
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
    )

    data = calculate_post_revoke(bracket_id=bracket_id, sort_by="post")
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "PostRevokeTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=18,
        leading=22,
        spaceAfter=8,
    )
    heading_style = ParagraphStyle(
        "PostRevokeHeading",
        parent=styles["Heading2"],
        fontSize=12,
        leading=14,
        spaceBefore=8,
        spaceAfter=6,
    )
    small_style = ParagraphStyle(
        "PostRevokeSmall",
        parent=styles["BodyText"],
        fontSize=7,
        leading=9,
    )
    normal_style = ParagraphStyle(
        "PostRevokeNormal",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10,
    )

    def p(value, style=normal_style):
        text = "" if value is None else str(value)
        text = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br/>")
        )
        return Paragraph(text, style)

    story = [
        Paragraph("Post-Revoke Calculation", title_style),
        Paragraph(ctf_config.ctf_name(), heading_style),
        Paragraph(
            "Generated at {} UTC{}".format(
                datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                " with bracket filter" if data["bracket_id"] else "",
            ),
            small_style,
        ),
        Spacer(1, 6),
    ]

    summary_rows = [
        [
            p("Rank"),
            p("Name"),
            p("Bracket"),
            p("Pre Score"),
            p("Post Score"),
            p("Banned"),
            p("Note"),
        ]
    ]
    for row in data["rows"]:
        summary_rows.append(
            [
                p(row["rank"]),
                p(row["name"]),
                p(row["bracket"] or "-"),
                p(row["pre_score_display"]),
                p(row["post_score_display"]),
                p("Yes" if row["calc_banned"] else "No"),
                p(row["note"] or ""),
            ]
        )

    table = Table(
        summary_rows,
        repeatRows=1,
        colWidths=[14 * mm, 45 * mm, 35 * mm, 22 * mm, 24 * mm, 20 * mm, 105 * mm],
    )
    table.setStyle(_pdf_table_style())
    story.append(table)

    for row in data["rows"]:
        detail = data["details"][row["account_id"]]
        story.append(PageBreak())
        story.append(Paragraph(row["name"], heading_style))
        story.append(
            Paragraph(
                "Rank {} | Pre {} | Post {} | Banned {}".format(
                    row["rank"],
                    row["pre_score_display"],
                    row["post_score_display"],
                    "Yes" if row["calc_banned"] else "No",
                ),
                small_style,
            )
        )
        if row["note"]:
            story.append(Paragraph("Account note: {}".format(row["note"]), small_style))
        story.append(Spacer(1, 6))

        story.append(Paragraph("Solves", heading_style))
        solve_rows = [[p("Challenge"), p("Original"), p("Calc"), p("%"), p("Revoked"), p("Note")]]
        if detail["solves"]:
            for solve in detail["solves"]:
                solve_rows.append(
                    [
                        p(solve["challenge_name"]),
                        p(format_score(solve["original_score"])),
                        p(format_score(solve["post_score"])),
                        p(solve["percentage"]),
                        p("Yes" if solve["revoked"] else "No"),
                        p(solve["note"] or ""),
                    ]
                )
        else:
            solve_rows.append([p("No solves"), p(""), p(""), p(""), p(""), p("")])
        solve_table = Table(
            solve_rows,
            repeatRows=1,
            colWidths=[70 * mm, 22 * mm, 22 * mm, 18 * mm, 22 * mm, 110 * mm],
        )
        solve_table.setStyle(_pdf_table_style())
        story.append(solve_table)
        story.append(Spacer(1, 8))

        story.append(Paragraph("Awards", heading_style))
        award_rows = [[p("Award"), p("Original"), p("Calc"), p("%"), p("Revoked"), p("Note")]]
        if detail["awards"]:
            for award in detail["awards"]:
                award_rows.append(
                    [
                        p(award["name"]),
                        p(format_score(award["original_score"])),
                        p(format_score(award["post_score"])),
                        p(award["percentage"]),
                        p("Yes" if award["revoked"] else "No"),
                        p(award["note"] or ""),
                    ]
                )
        else:
            award_rows.append([p("No awards"), p(""), p(""), p(""), p(""), p("")])
        award_table = Table(
            award_rows,
            repeatRows=1,
            colWidths=[70 * mm, 22 * mm, 22 * mm, 18 * mm, 22 * mm, 110 * mm],
        )
        award_table.setStyle(_pdf_table_style())
        story.append(award_table)

    doc.build(story)
    buffer.seek(0)
    return buffer


def _pdf_table_style():
    from reportlab.lib import colors
    from reportlab.platypus import TableStyle

    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
    )
