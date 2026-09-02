import datetime
import json
from copy import deepcopy
from urllib.parse import urlparse

import requests
from flask import current_app, url_for
from requests import RequestException

from CTFd.cache import clear_config
from CTFd.models import AnnouncerBotLogs, Challenges, Solves, Teams, Users, db
from CTFd.utils import get_config, set_config
from CTFd.utils.config import is_teams_mode

ANNOUNCER_DEFAULTS = {
    "webhook_url": "",
    "bot_name": "First Blood Bot",
    "bot_profile_image_url": "",
    "bot_thumbnail_image_url": "",
    "first_blood_title": "First Blood",
    "second_blood_title": "Second Blood",
    "third_blood_title": "Third Blood",
    "solve_title": "Solved",
    "footer": "",
    "embed_color": "#ed1c24",
    "announce_first_blood": True,
    "announce_second_blood": True,
    "announce_third_blood": True,
    "announce_solve": False,
}

CONFIG_KEYS = {
    "webhook_url": "announcer_bot_webhook_url",
    "bot_name": "announcer_bot_name",
    "bot_profile_image_url": "announcer_bot_profile_image_url",
    "bot_thumbnail_image_url": "announcer_bot_thumbnail_image_url",
    "first_blood_title": "announcer_bot_first_blood_title",
    "second_blood_title": "announcer_bot_second_blood_title",
    "third_blood_title": "announcer_bot_third_blood_title",
    "solve_title": "announcer_bot_solve_title",
    "footer": "announcer_bot_footer",
    "embed_color": "announcer_bot_embed_color",
    "announce_first_blood": "announcer_bot_announce_first_blood",
    "announce_second_blood": "announcer_bot_announce_second_blood",
    "announce_third_blood": "announcer_bot_announce_third_blood",
    "announce_solve": "announcer_bot_announce_solve",
}

TITLE_KEYS = {
    "first_blood": "first_blood_title",
    "second_blood": "second_blood_title",
    "third_blood": "third_blood_title",
    "solve": "solve_title",
}

ENABLE_KEYS = {
    "first_blood": "announce_first_blood",
    "second_blood": "announce_second_blood",
    "third_blood": "announce_third_blood",
    "solve": "announce_solve",
}

EVENT_RANKS = {
    "first_blood": 1,
    "second_blood": 2,
    "third_blood": 3,
    "solve": 4,
}

IMAGE_EXTENSIONS = (
    ".apng",
    ".avif",
    ".gif",
    ".jpeg",
    ".jpg",
    ".png",
    ".svg",
    ".webp",
)
DISCORD_WEBHOOK_HOSTS = {
    "discord.com",
    "discordapp.com",
    "canary.discord.com",
    "ptb.discord.com",
}


class SafeFormatDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def normalize_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("1", "true", "yes", "on")
    return bool(value)


def normalize_color(value):
    value = (value or ANNOUNCER_DEFAULTS["embed_color"]).strip()
    if not value.startswith("#"):
        value = "#" + value
    if len(value) != 7:
        return ANNOUNCER_DEFAULTS["embed_color"]
    try:
        int(value[1:], 16)
    except ValueError:
        return ANNOUNCER_DEFAULTS["embed_color"]
    return value.lower()


def validate_http_url(value, label, image=False):
    if not value:
        return None

    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return f"{label} must be an HTTP or HTTPS URL."

    if image and not parsed.path.lower().endswith(IMAGE_EXTENSIONS):
        return f"{label} must point to an image URL."

    return None


def validate_discord_webhook_url(value):
    if not value:
        return None

    parsed = urlparse(value)
    if parsed.scheme != "https":
        return "Discord webhook link must use HTTPS."
    if parsed.netloc.lower() not in DISCORD_WEBHOOK_HOSTS:
        return "Discord webhook link must be a Discord webhook URL."
    if not parsed.path.startswith("/api/webhooks/"):
        return "Discord webhook link must be a Discord webhook URL."

    return None


def color_to_decimal(value):
    return int(normalize_color(value).lstrip("#"), 16)


def merge_announcer_settings(data=None):
    data = data or {}
    settings = get_announcer_settings(include_webhook=True)

    for public_key in CONFIG_KEYS:
        if public_key not in data:
            continue

        value = data.get(public_key)
        if public_key.startswith("announce_"):
            settings[public_key] = normalize_bool(value)
        elif public_key == "embed_color":
            settings[public_key] = normalize_color(value)
        elif value is None:
            settings[public_key] = ""
        else:
            settings[public_key] = str(value).strip()

    if "template" in data:
        settings["template"] = data.get("template")

    settings["webhook_configured"] = bool(settings.get("webhook_url"))
    return settings


def build_announcer_template(settings=None):
    settings = settings or get_announcer_settings(include_webhook=False)
    color = color_to_decimal(settings.get("embed_color"))
    return {
        "username": "{bot_name}",
        "avatar_url": "{bot_profile_image_url}",
        "allowed_mentions": {"parse": []},
        "content": "**{title}**",
        "embeds": [
            {
                "title": "{title}",
                "description": "{account_name} has solved {challenge_name}!",
                "color": color,
                "fields": [
                    {
                        "name": "Team / User",
                        "value": "{account_name}",
                        "inline": True,
                    },
                    {
                        "name": "Challenge",
                        "value": "{challenge_name}",
                        "inline": True,
                    },
                    {"name": "Category", "value": "{category}", "inline": True},
                    {"name": "Timestamp", "value": "{timestamp}", "inline": False},
                ],
                "thumbnail": {"url": "{bot_thumbnail_image_url}"},
                "footer": {"text": "{footer}"},
                "timestamp": "{iso_timestamp}",
            }
        ],
    }


def get_announcer_settings(include_webhook=False):
    settings = {}
    for public_key, config_key in CONFIG_KEYS.items():
        default = ANNOUNCER_DEFAULTS[public_key]
        value = get_config(config_key, default=default)
        if public_key.startswith("announce_"):
            value = normalize_bool(value)
        elif public_key == "embed_color":
            value = normalize_color(value)
        elif value is None:
            value = ""
        settings[public_key] = value

    webhook_url = settings.pop("webhook_url")
    settings["webhook_configured"] = bool(webhook_url)
    if include_webhook:
        settings["webhook_url"] = webhook_url

    template = get_config("announcer_bot_template")
    if not template:
        template = json.dumps(build_announcer_template(settings), indent=2)
    settings["template"] = template
    return settings


def validate_announcer_template(template):
    if not isinstance(template, str) or not template.strip():
        return None, "Announcement JSON template is required."
    try:
        payload = json.loads(template)
    except ValueError as e:
        return None, f"Announcement JSON template is invalid JSON: {e}"
    if not isinstance(payload, dict):
        return None, "Announcement JSON template must be a JSON object."
    if not any(payload.get(key) for key in ("content", "embeds", "components", "poll")):
        return (
            None,
            "Announcement JSON template must include content, embeds, components, or poll.",
        )
    return payload, None


def save_announcer_settings(data):
    data = data or {}
    errors = {}

    template = data.get("template")
    if template is not None:
        _payload, error = validate_announcer_template(template)
        if error:
            errors["template"] = [error]

    if "webhook_url" in data:
        error = validate_discord_webhook_url(
            str(data.get("webhook_url") or "").strip()
        )
        if error:
            errors["webhook_url"] = [error]

    for field, label in (
        ("bot_profile_image_url", "Bot profile image link"),
        ("bot_thumbnail_image_url", "Bot thumbnail image link"),
    ):
        if field in data:
            error = validate_http_url(
                str(data.get(field) or "").strip(), label, image=True
            )
            if error:
                errors[field] = [error]

    if errors:
        return False, errors

    for public_key, config_key in CONFIG_KEYS.items():
        if public_key == "webhook_url" and "webhook_url" not in data:
            continue
        if public_key not in data:
            continue

        value = data.get(public_key)
        if public_key.startswith("announce_"):
            value = "true" if normalize_bool(value) else "false"
        elif public_key == "embed_color":
            value = normalize_color(value)
        elif value is None:
            value = ""
        else:
            value = str(value).strip()
        set_config(config_key, value)

    if template is not None:
        set_config("announcer_bot_template", template)

    clear_config()
    return True, {}


def serialize_announcer_log(log):
    return {
        "id": log.id,
        "event_type": log.event_type,
        "title": log.title,
        "account_name": log.account_name,
        "user_id": log.user_id,
        "team_id": log.team_id,
        "challenge_id": log.challenge_id,
        "challenge_name": log.challenge_name,
        "response_status": log.response_status,
        "response_body": log.response_body,
        "success": log.success,
        "error": log.error,
        "created": log.created.isoformat() if log.created else None,
    }


def list_announcer_logs():
    return [
        serialize_announcer_log(log)
        for log in AnnouncerBotLogs.query.order_by(AnnouncerBotLogs.id.desc()).all()
    ]


def render_template_value(value, context):
    if isinstance(value, str):
        return value.format_map(SafeFormatDict(context))
    if isinstance(value, list):
        return [render_template_value(item, context) for item in value]
    if isinstance(value, dict):
        return {
            key: render_template_value(item, context)
            for key, item in value.items()
        }
    return value


def prune_empty_values(value):
    if isinstance(value, list):
        return [
            item
            for item in (prune_empty_values(item) for item in value)
            if item not in ("", None, {}, [])
        ]
    if isinstance(value, dict):
        pruned = {}
        for key, item in value.items():
            cleaned = prune_empty_values(item)
            if cleaned in ("", None, {}, []):
                continue
            pruned[key] = cleaned
        return pruned
    return value


def get_solve_account(solve):
    if is_teams_mode():
        return solve.team
    return solve.user


def solve_is_eligible(solve):
    if not solve or not solve.user or not solve.challenge:
        return False
    if solve.user.hidden or solve.user.banned:
        return False
    if solve.challenge.state != "visible":
        return False
    if is_teams_mode():
        return bool(solve.team and not solve.team.hidden and not solve.team.banned)
    return True


def eligible_solves_for_challenge(challenge_id):
    query = (
        Solves.query.join(Users, Solves.user_id == Users.id)
        .filter(Solves.challenge_id == challenge_id)
        .filter(Users.hidden == False, Users.banned == False)
    )
    if is_teams_mode():
        query = (
            query.join(Teams, Solves.team_id == Teams.id)
            .filter(Solves.team_id.isnot(None))
            .filter(Teams.hidden == False, Teams.banned == False)
        )
    return query.order_by(Solves.date.asc(), Solves.id.asc())


def get_solve_rank(solve):
    if not solve_is_eligible(solve):
        return None
    ids = [row.id for row in eligible_solves_for_challenge(solve.challenge_id).all()]
    try:
        return ids.index(solve.id) + 1
    except ValueError:
        return None


def event_type_for_rank(rank, settings):
    if rank == 1:
        event_type = "first_blood"
    elif rank == 2:
        event_type = "second_blood"
    elif rank == 3:
        event_type = "third_blood"
    elif rank and rank > 3:
        event_type = "solve"
    else:
        return None

    if not settings.get(ENABLE_KEYS[event_type]):
        return None
    return event_type


def utc_isoformat(value):
    if not value:
        value = datetime.datetime.utcnow()
    if value.tzinfo is None:
        value = value.replace(tzinfo=datetime.timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


def unix_timestamp(value):
    if value.tzinfo is None:
        value = value.replace(tzinfo=datetime.timezone.utc)
    return int(value.timestamp())


def build_announcement_context(solve, event_type, rank, settings):
    account = get_solve_account(solve)
    account_name = account.name if account else solve.user.name
    challenge = solve.challenge or Challenges.query.get(solve.challenge_id)
    timestamp = unix_timestamp(solve.date)
    challenge_url = ""
    try:
        challenge_url = url_for(
            "challenges.listing",
            _external=True,
            _anchor=challenge.name if challenge else "",
        )
    except RuntimeError:
        pass

    title = settings.get(TITLE_KEYS[event_type]) or ANNOUNCER_DEFAULTS[
        TITLE_KEYS[event_type]
    ]
    return {
        "title": title,
        "event_type": event_type,
        "solve_rank": rank,
        "rank": rank,
        "account_name": account_name,
        "team": solve.team.name if solve.team else "",
        "team_name": solve.team.name if solve.team else "",
        "user": solve.user.name if solve.user else "",
        "user_name": solve.user.name if solve.user else "",
        "challenge": challenge.name if challenge else "",
        "challenge_name": challenge.name if challenge else "",
        "category": challenge.category if challenge else "",
        "timestamp": f"<t:{timestamp}:F>",
        "relative_timestamp": f"<t:{timestamp}:R>",
        "unix_timestamp": timestamp,
        "iso_timestamp": utc_isoformat(solve.date),
        "challenge_url": challenge_url,
        "bot_name": settings.get("bot_name") or ANNOUNCER_DEFAULTS["bot_name"],
        "bot_profile_image_url": settings.get("bot_profile_image_url", ""),
        "bot_thumbnail_image_url": settings.get("bot_thumbnail_image_url", ""),
        "footer": settings.get("footer", ""),
    }


def build_test_announcement_context(event_type, rank, settings):
    now = datetime.datetime.now(datetime.timezone.utc)
    timestamp = unix_timestamp(now)
    title = settings.get(TITLE_KEYS[event_type]) or ANNOUNCER_DEFAULTS[
        TITLE_KEYS[event_type]
    ]
    return {
        "title": title,
        "event_type": event_type,
        "solve_rank": rank,
        "rank": rank,
        "account_name": "Sussybaka",
        "team": "Sussybaka",
        "team_name": "Sussybaka",
        "user": "Sussybaka",
        "user_name": "Sussybaka",
        "challenge": "Example",
        "challenge_name": "Example",
        "category": "Testing",
        "timestamp": f"<t:{timestamp}:F>",
        "relative_timestamp": f"<t:{timestamp}:R>",
        "unix_timestamp": timestamp,
        "iso_timestamp": utc_isoformat(now),
        "challenge_url": "",
        "bot_name": settings.get("bot_name") or ANNOUNCER_DEFAULTS["bot_name"],
        "bot_profile_image_url": settings.get("bot_profile_image_url", ""),
        "bot_thumbnail_image_url": settings.get("bot_thumbnail_image_url", ""),
        "footer": settings.get("footer", ""),
    }


def log_announcement(
    solve,
    event_type,
    title,
    account_name,
    payload=None,
    success=False,
    response_status=None,
    response_body=None,
    error=None,
    challenge_name=None,
):
    log = AnnouncerBotLogs(
        event_type=event_type,
        title=title,
        account_name=account_name,
        user_id=solve.user_id if solve else None,
        team_id=solve.team_id if solve else None,
        challenge_id=solve.challenge_id if solve else None,
        challenge_name=(
            challenge_name
            if challenge_name is not None
            else solve.challenge.name
            if solve and solve.challenge
            else None
        ),
        payload=json.dumps(payload, separators=(",", ":")) if payload else None,
        response_status=response_status,
        response_body=response_body,
        success=success,
        error=error,
    )
    db.session.add(log)
    db.session.commit()
    return log


def send_webhook(webhook_url, payload):
    response = requests.post(
        webhook_url,
        json=payload,
        params={"wait": "true"},
        timeout=current_app.config.get("ANNOUNCER_BOT_TIMEOUT", 5),
    )
    return response


def dispatch_announcement(webhook_url, template_text, context, solve=None):
    template, error = validate_announcer_template(template_text)

    if error:
        return log_announcement(
            solve=solve,
            event_type=context["event_type"],
            title=context["title"],
            account_name=context["account_name"],
            success=False,
            error=error,
            challenge_name=context.get("challenge_name"),
        )

    payload = render_template_value(deepcopy(template), context)
    payload = prune_empty_values(payload)
    payload["allowed_mentions"] = {"parse": []}

    try:
        response = send_webhook(webhook_url, payload)
        success = 200 <= response.status_code < 300
        return log_announcement(
            solve=solve,
            event_type=context["event_type"],
            title=context["title"],
            account_name=context["account_name"],
            payload=payload,
            success=success,
            response_status=response.status_code,
            response_body=(response.text or "")[:2000],
            error=None if success else "Discord webhook returned an error.",
            challenge_name=context.get("challenge_name"),
        )
    except RequestException as e:
        return log_announcement(
            solve=solve,
            event_type=context["event_type"],
            title=context["title"],
            account_name=context["account_name"],
            payload=payload,
            success=False,
            error=str(e),
            challenge_name=context.get("challenge_name"),
        )


def announce_solve(solve):
    settings = get_announcer_settings(include_webhook=True)
    webhook_url = settings.get("webhook_url")
    if not webhook_url:
        return None

    rank = get_solve_rank(solve)
    event_type = event_type_for_rank(rank, settings)
    if not event_type:
        return None

    template_text = settings.get("template")
    context = build_announcement_context(solve, event_type, rank, settings)
    return dispatch_announcement(webhook_url, template_text, context, solve=solve)


def send_test_announcements(data=None):
    settings = merge_announcer_settings(data)
    webhook_url = settings.get("webhook_url")
    if not webhook_url:
        return False, {"webhook_url": ["Discord webhook link is required."]}, []

    webhook_error = validate_discord_webhook_url(webhook_url)
    if webhook_error:
        return False, {"webhook_url": [webhook_error]}, []

    template_text = settings.get("template")
    _template, template_error = validate_announcer_template(template_text)
    if template_error:
        return False, {"template": [template_error]}, []

    event_types = [
        event_type
        for event_type in ("first_blood", "second_blood", "third_blood", "solve")
        if settings.get(ENABLE_KEYS[event_type])
    ]
    if not event_types:
        return False, {"options": ["Enable at least one announcement option."]}, []

    logs = []
    for event_type in event_types:
        rank = EVENT_RANKS[event_type]
        context = build_test_announcement_context(event_type, rank, settings)
        logs.append(dispatch_announcement(webhook_url, template_text, context))

    return True, {}, [serialize_announcer_log(log) for log in logs]
