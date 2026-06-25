import json

from flask import has_request_context, request, session

from CTFd.models import Users

ASSISTANT_TYPE = "assistant"
FULL_ADMIN_TYPE = "admin"

ASSISTANT_PERMISSION_DEFINITIONS = [
    ("statistics", "Statistics"),
    ("notifications", "Notifications"),
    ("pages", "Pages"),
    ("users", "Users"),
    ("teams", "Teams"),
    ("scoreboard", "Scoreboard"),
    ("challenges", "Challenges"),
    ("submissions", "Submissions"),
    ("awards", "Awards"),
    ("comments", "Comments"),
    ("files", "Files"),
    ("config", "Config"),
    ("import_export", "Import / Export"),
    ("plugins", "Plugins"),
    ("monitor", "Monitor"),
]

ASSISTANT_PERMISSION_KEYS = {
    permission for permission, _label in ASSISTANT_PERMISSION_DEFINITIONS
}

ADMIN_ENDPOINT_PERMISSIONS = {
    "admin.statistics": {"statistics"},
    "admin.notifications": {"notifications"},
    "admin.pages_listing": {"pages"},
    "admin.pages_new": {"pages"},
    "admin.pages_preview": {"pages"},
    "admin.pages_detail": {"pages"},
    "admin.users_listing": {"users"},
    "admin.users_new": {"users"},
    "admin.users_detail": {"users"},
    "admin.teams_listing": {"teams"},
    "admin.teams_new": {"teams"},
    "admin.teams_detail": {"teams"},
    "admin.scoreboard_listing": {"scoreboard"},
    "admin.challenges_listing": {"challenges"},
    "admin.challenges_detail": {"challenges"},
    "admin.challenges_preview": {"challenges"},
    "admin.challenges_new": {"challenges"},
    "admin.submissions_listing": {"submissions"},
    "admin.config": {"config"},
    "admin.import_ctf": {"import_export"},
    "admin.export_ctf": {"import_export"},
    "admin.import_csv": {"import_export"},
    "admin.export_csv": {"import_export"},
    "admin.plugin": {"plugins"},
    "admin.monitor": {"monitor"},
}

API_PATH_PERMISSIONS = [
    ("/api/v1/statistics", {"statistics"}),
    ("/api/v1/notifications", {"notifications"}),
    ("/api/v1/pages", {"pages"}),
    ("/api/v1/users", {"users"}),
    ("/api/v1/teams", {"teams"}),
    ("/api/v1/scoreboard", {"scoreboard"}),
    ("/api/v1/challenges", {"challenges"}),
    ("/api/v1/flags", {"challenges"}),
    ("/api/v1/hints", {"challenges"}),
    ("/api/v1/tags", {"challenges"}),
    ("/api/v1/topics", {"challenges"}),
    ("/api/v1/unlocks", {"challenges"}),
    ("/api/v1/solutions", {"challenges"}),
    ("/api/v1/submissions", {"submissions"}),
    ("/api/v1/awards", {"awards", "users", "teams"}),
    ("/api/v1/comments", {"comments", "users", "teams", "challenges", "pages"}),
    ("/api/v1/files", {"files", "challenges", "pages"}),
    ("/api/v1/configs", {"config"}),
    ("/api/v1/brackets", {"config", "users", "teams"}),
    ("/api/v1/exports", {"import_export"}),
    ("/api/v1/tokens", {"users"}),
]


def normalize_assistant_permissions(value):
    if value in (None, ""):
        return []

    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            value = [value]

    if not isinstance(value, (list, tuple, set)):
        return []

    permissions = []
    for permission in value:
        if permission in ASSISTANT_PERMISSION_KEYS and permission not in permissions:
            permissions.append(permission)
    return permissions


def serialize_assistant_permissions(value):
    permissions = normalize_assistant_permissions(value)
    if not permissions:
        return None
    return json.dumps(permissions)


def get_assistant_permission_definitions():
    return ASSISTANT_PERMISSION_DEFINITIONS


def user_is_full_admin(user):
    return bool(user and user.type == FULL_ADMIN_TYPE)


def user_is_assistant(user):
    return bool(user and user.type == ASSISTANT_TYPE)


def get_current_permission_user():
    if not has_request_context():
        return None

    user_id = session.get("id")
    if user_id:
        return Users.query.filter_by(id=user_id).first()
    return None


def user_has_assistant_permission(user, permission):
    if user_is_full_admin(user):
        return True
    if user_is_assistant(user):
        return permission in normalize_assistant_permissions(user.assistant_permissions)
    return False


def _path_matches(path, prefix):
    return path == prefix or path.startswith(prefix + "/")


def get_current_admin_permission_candidates():
    if not has_request_context():
        return set()

    endpoint = request.endpoint
    if endpoint in ADMIN_ENDPOINT_PERMISSIONS:
        return ADMIN_ENDPOINT_PERMISSIONS[endpoint]

    path = request.path
    for prefix, permissions in API_PATH_PERMISSIONS:
        if _path_matches(path, prefix):
            return permissions

    return set()


def user_can_access_current_admin_request(user):
    if user_is_full_admin(user):
        return True

    if not user_is_assistant(user):
        return False

    if has_request_context() and request.endpoint == "admin.view":
        return bool(normalize_assistant_permissions(user.assistant_permissions))

    candidates = get_current_admin_permission_candidates()
    if not candidates:
        return False

    user_permissions = set(normalize_assistant_permissions(user.assistant_permissions))
    return bool(user_permissions.intersection(candidates))


def current_user_can_access_admin_permission(permission):
    user = get_current_permission_user()
    return user_has_assistant_permission(user, permission)


def current_user_can_access_current_admin_request():
    return user_can_access_current_admin_request(get_current_permission_user())


def first_allowed_admin_endpoint(user):
    if user_is_full_admin(user):
        return "admin.statistics"

    permissions = normalize_assistant_permissions(
        getattr(user, "assistant_permissions", None)
    )
    for permission, endpoint in [
        ("statistics", "admin.statistics"),
        ("notifications", "admin.notifications"),
        ("pages", "admin.pages_listing"),
        ("users", "admin.users_listing"),
        ("teams", "admin.teams_listing"),
        ("scoreboard", "admin.scoreboard_listing"),
        ("challenges", "admin.challenges_listing"),
        ("submissions", "admin.submissions_listing"),
        ("config", "admin.config"),
        ("import_export", "admin.import_ctf"),
        ("monitor", "admin.monitor"),
    ]:
        if permission in permissions:
            return endpoint
    return None
