from typing import List

from flask import request
from flask_restx import Namespace, Resource

from CTFd.api.v1.helpers.request import validate_args
from CTFd.api.v1.helpers.schemas import sqlalchemy_to_pydantic
from CTFd.api.v1.schemas import (
    APIDetailedSuccessResponse,
    PaginatedAPIListSuccessResponse,
)
from CTFd.cache import cache, clear_challenges, clear_standings
from CTFd.constants import RawEnum
from CTFd.models import Fails, Solves, Submissions, db
from CTFd.schemas.submissions import SubmissionSchema
from CTFd.utils.challenge_submissions import delete_solver_files_for_submission
from CTFd.utils.decorators import admins_only
from CTFd.utils.helpers.models import build_model_filters

submissions_namespace = Namespace(
    "submissions", description="Endpoint to retrieve Submission"
)

SubmissionModel = sqlalchemy_to_pydantic(Submissions)
TransientSubmissionModel = sqlalchemy_to_pydantic(Submissions, exclude=["id"])


class SubmissionDetailedSuccessResponse(APIDetailedSuccessResponse):
    data: SubmissionModel


class SubmissionListSuccessResponse(PaginatedAPIListSuccessResponse):
    data: List[SubmissionModel]


def _get_verified_value(req):
    if "verified" not in req:
        return None, None

    verified = req.get("verified")
    if not isinstance(verified, bool):
        return None, {"verified": ["Verified must be true or false"]}
    return verified, None


submissions_namespace.schema_model(
    "SubmissionDetailedSuccessResponse", SubmissionDetailedSuccessResponse.apidoc()
)

submissions_namespace.schema_model(
    "SubmissionListSuccessResponse", SubmissionListSuccessResponse.apidoc()
)


@submissions_namespace.route("")
class SubmissionsList(Resource):
    @admins_only
    @submissions_namespace.doc(
        description="Endpoint to get submission objects in bulk",
        responses={
            200: ("Success", "SubmissionListSuccessResponse"),
            400: (
                "An error occured processing the provided or stored data",
                "APISimpleErrorResponse",
            ),
        },
    )
    @validate_args(
        {
            "challenge_id": (int, None),
            "user_id": (int, None),
            "team_id": (int, None),
            "ip": (str, None),
            "provided": (str, None),
            "type": (str, None),
            "q": (str, None),
            "field": (
                RawEnum(
                    "SubmissionFields",
                    {
                        "challenge_id": "challenge_id",
                        "user_id": "user_id",
                        "team_id": "team_id",
                        "ip": "ip",
                        "provided": "provided",
                        "type": "type",
                    },
                ),
                None,
            ),
        },
        location="query",
    )
    def get(self, query_args):
        q = query_args.pop("q", None)
        field = str(query_args.pop("field", None))
        filters = build_model_filters(model=Submissions, query=q, field=field)

        args = query_args
        schema = SubmissionSchema(many=True)

        submissions = (
            Submissions.query.filter_by(**args)
            .filter(*filters)
            .paginate(max_per_page=100, error_out=False)
        )

        response = schema.dump(submissions.items)

        if response.errors:
            return {"success": False, "errors": response.errors}, 400

        return {
            "meta": {
                "pagination": {
                    "page": submissions.page,
                    "next": submissions.next_num,
                    "prev": submissions.prev_num,
                    "pages": submissions.pages,
                    "per_page": submissions.per_page,
                    "total": submissions.total,
                }
            },
            "success": True,
            "data": response.data,
        }

    @admins_only
    @submissions_namespace.doc(
        description="Endpoint to create a submission object. Users should interact with the attempt endpoint to submit flags.",
        responses={
            200: ("Success", "SubmissionListSuccessResponse"),
            400: (
                "An error occured processing the provided or stored data",
                "APISimpleErrorResponse",
            ),
        },
    )
    @validate_args(TransientSubmissionModel, location="json")
    def post(self, json_args):
        req = json_args
        Model = Submissions.get_child(type=req.get("type"))
        schema = SubmissionSchema(instance=Model())
        response = schema.load(req)
        if response.errors:
            return {"success": False, "errors": response.errors}, 400

        db.session.add(response.data)
        db.session.commit()

        response = schema.dump(response.data)
        db.session.close()

        # Delete standings cache
        clear_standings()
        # Delete challenges cache
        clear_challenges()

        return {"success": True, "data": response.data}


@submissions_namespace.route("/<submission_id>")
@submissions_namespace.param("submission_id", "A Submission ID")
class Submission(Resource):
    @admins_only
    @submissions_namespace.doc(
        description="Endpoint to get a submission object",
        responses={
            200: ("Success", "SubmissionDetailedSuccessResponse"),
            400: (
                "An error occured processing the provided or stored data",
                "APISimpleErrorResponse",
            ),
        },
    )
    def get(self, submission_id):
        submission = Submissions.query.filter_by(id=submission_id).first_or_404()
        schema = SubmissionSchema()
        response = schema.dump(submission)

        if response.errors:
            return {"success": False, "errors": response.errors}, 400

        return {"success": True, "data": response.data}

    @admins_only
    @submissions_namespace.doc(
        description="Endpoint to edit a submission object",
        responses={
            200: ("Success", "SubmissionDetailedSuccessResponse"),
            400: (
                "An error occured processing the provided or stored data",
                "APISimpleErrorResponse",
            ),
        },
    )
    def patch(self, submission_id):
        submission = Submissions.query.filter_by(id=submission_id).first_or_404()

        req = request.get_json() or {}
        verified, verified_error = _get_verified_value(req)
        if verified_error:
            return {"success": False, "errors": verified_error}, 400

        submission_type = req.get("type")

        if submission_type == "correct":
            existing_solve = Solves.query.filter_by(
                challenge_id=submission.challenge_id,
                user_id=submission.user_id,
                team_id=submission.team_id if submission.team_id else None,
            ).first()

            # If a solve for this user / team pair exists, don't create a new solve
            if existing_solve:
                return {
                    "success": False,
                    "errors": {"type": ["Solve already exists for this submission"]},
                }, 400

            solve = Solves(
                user_id=submission.user_id,
                challenge_id=submission.challenge_id,
                team_id=submission.team_id,
                ip=submission.ip,
                provided=submission.provided,
                ai_source=submission.ai_source,
                verified=submission.verified,
                date=submission.date,
            )
            db.session.add(solve)
            submission.type = "discard"
            db.session.commit()

            # Delete standings cache
            clear_standings()
            clear_challenges()

            submission = solve

        elif submission_type == "incorrect":
            submission_id = submission.id
            existing_solve = Solves.query.filter_by(id=submission_id).first()

            if existing_solve:
                delete_solver_files_for_submission(existing_solve, commit=False)
                db.session.delete(existing_solve)

            submission.type = "incorrect"
            db.session.commit()

            if existing_solve:
                clear_standings()
                clear_challenges()

            submission = Fails.query.filter_by(id=submission_id).first()

        if verified is not None:
            submission.verified = verified
            db.session.commit()

        schema = SubmissionSchema()
        response = schema.dump(submission)

        if response.errors:
            return {"success": False, "errors": response.errors}, 400

        return {"success": True, "data": response.data}

    @admins_only
    @submissions_namespace.doc(
        description="Endpoint to delete a submission object",
        responses={
            200: ("Success", "APISimpleSuccessResponse"),
            400: (
                "An error occured processing the provided or stored data",
                "APISimpleErrorResponse",
            ),
        },
    )
    def delete(self, submission_id):
        submission = Submissions.query.filter_by(id=submission_id).first_or_404()
        account_id = submission.account_id
        challenge_id = submission.challenge_id
        delete_solver_files_for_submission(submission, commit=False)
        db.session.delete(submission)
        db.session.commit()
        db.session.close()

        # Clear out the user's recent attempt count
        # This is a little lossy but I don't think it matters in practice
        acc_kpm_key = f"account_kpm_{account_id}_{challenge_id}"
        cache.expire(acc_kpm_key, 0)

        # Delete standings cache
        clear_standings()
        clear_challenges()

        return {"success": True}
