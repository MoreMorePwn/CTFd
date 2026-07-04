from marshmallow import fields

from CTFd.models import AntiCheatEvents, ma
from CTFd.schemas.challenges import ChallengeSchema
from CTFd.schemas.submissions import SubmissionSchema
from CTFd.schemas.teams import TeamSchema
from CTFd.schemas.users import UserSchema
from CTFd.utils import string_types


class AntiCheatEventSchema(ma.ModelSchema):
    user = fields.Nested(UserSchema, only=["id", "name"])
    team = fields.Nested(TeamSchema, only=["id", "name"])
    challenge = fields.Nested(ChallengeSchema, only=["id", "name", "category"])
    submission = fields.Nested(
        SubmissionSchema,
        only=["id", "type", "date", "provided", "ai_source", "verified"],
    )
    reviewer = fields.Nested(UserSchema, only=["id", "name"])

    class Meta:
        model = AntiCheatEvents
        include_fk = True
        dump_only = ("id", "created")

    views = {
        "admin": [
            "id",
            "type",
            "severity",
            "details",
            "user_id",
            "user",
            "team_id",
            "team",
            "challenge_id",
            "challenge",
            "submission_id",
            "submission",
            "ip",
            "user_agent",
            "browser_fingerprint",
            "reviewed",
            "reviewer_id",
            "reviewer",
            "reviewed_at",
            "created",
        ]
    }

    def __init__(self, view=None, *args, **kwargs):
        if view:
            if isinstance(view, string_types):
                kwargs["only"] = self.views[view]
            elif isinstance(view, list):
                kwargs["only"] = view

        super(AntiCheatEventSchema, self).__init__(*args, **kwargs)
