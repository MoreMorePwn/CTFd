from CTFd.constants.options import (
    AccountVisibilityTypes,
    ChallengeVisibilityTypes,
    RegistrationVisibilityTypes,
    ScoreVisibilityTypes,
    UserModeTypes,
)
from CTFd.constants.themes import DEFAULT_THEME

DEFAULTS = {
    # General Settings
    "ctf_name": "CTFd",
    "user_mode": UserModeTypes.USERS,
    # Visual/Style Settings
    "ctf_theme": DEFAULT_THEME,
    # Custom challenge submission metadata
    "ai_source_regex": r"^https://chat\.deepseek\.com/share/[A-Za-z0-9_-]+$",
    "solver_file_limit": 0,
    "solver_total_size_limit": 10485760,
    "grafana_url": "http://127.0.0.1:3000",
    # Visibility Settings
    "challenge_visibility": ChallengeVisibilityTypes.PRIVATE,
    "registration_visibility": RegistrationVisibilityTypes.PUBLIC,
    "score_visibility": ScoreVisibilityTypes.PUBLIC,
    "account_visibility": AccountVisibilityTypes.PUBLIC,
}
