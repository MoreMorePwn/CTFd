from typing import List

from flask import abort, request, session
from flask_restx import Namespace, Resource

from CTFd.api.v1.helpers.request import validate_args
from CTFd.api.v1.helpers.schemas import sqlalchemy_to_pydantic
from CTFd.api.v1.schemas import APIDetailedSuccessResponse, APIListSuccessResponse
from CTFd.constants import RawEnum
from CTFd.models import (
    ChallengeComments,
    Comments,
    PageComments,
    TeamComments,
    UserComments,
    db,
)
from CTFd.schemas.comments import CommentSchema
from CTFd.utils.admin_permissions import current_user_can_access_admin_permission
from CTFd.utils.decorators import admins_only
from CTFd.utils.helpers.models import build_model_filters

comments_namespace = Namespace("comments", description="Endpoint to retrieve Comments")


CommentModel = sqlalchemy_to_pydantic(Comments)


class CommentDetailedSuccessResponse(APIDetailedSuccessResponse):
    data: CommentModel


class CommentListSuccessResponse(APIListSuccessResponse):
    data: List[CommentModel]


comments_namespace.schema_model(
    "CommentDetailedSuccessResponse", CommentDetailedSuccessResponse.apidoc()
)

comments_namespace.schema_model(
    "CommentListSuccessResponse", CommentListSuccessResponse.apidoc()
)


def get_comment_model(data):
    model = Comments
    if "challenge_id" in data:
        model = ChallengeComments
    elif "user_id" in data:
        model = UserComments
    elif "team_id" in data:
        model = TeamComments
    elif "page_id" in data:
        model = PageComments
    else:
        model = Comments
    return model


def get_comment_type(data):
    if "challenge_id" in data:
        return "challenge"
    if "user_id" in data:
        return "user"
    if "team_id" in data:
        return "team"
    if "page_id" in data:
        return "page"
    return data.get("type", "standard")


def _allowed_comment_types():
    if current_user_can_access_admin_permission("comments"):
        return None

    allowed = set()
    if current_user_can_access_admin_permission("challenges"):
        allowed.add("challenge")
    if current_user_can_access_admin_permission("pages"):
        allowed.add("page")
    return allowed


def _ensure_comment_type_allowed(comment_type):
    allowed_types = _allowed_comment_types()
    if allowed_types is None:
        return
    if comment_type not in allowed_types:
        abort(403)


@comments_namespace.route("")
class CommentList(Resource):
    @admins_only
    @comments_namespace.doc(
        description="Endpoint to list Comment objects in bulk",
        responses={
            200: ("Success", "CommentListSuccessResponse"),
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
            "page_id": (int, None),
            "q": (str, None),
            "field": (RawEnum("CommentFields", {"content": "content"}), None),
        },
        location="query",
    )
    def get(self, query_args):
        q = query_args.pop("q", None)
        field = str(query_args.pop("field", None))
        requested_type = get_comment_type(query_args)
        allowed_types = _allowed_comment_types()
        if allowed_types is not None and requested_type != "standard":
            _ensure_comment_type_allowed(requested_type)
        CommentModel = get_comment_model(data=query_args)
        filters = build_model_filters(model=CommentModel, query=q, field=field)
        if allowed_types is not None and requested_type == "standard":
            filters.append(CommentModel.type.in_(allowed_types))

        comments = (
            CommentModel.query.filter_by(**query_args)
            .filter(*filters)
            .order_by(CommentModel.id.desc())
            .paginate(max_per_page=100, error_out=False)
        )
        schema = CommentSchema(many=True)
        response = schema.dump(comments.items)

        if response.errors:
            return {"success": False, "errors": response.errors}, 400

        return {
            "meta": {
                "pagination": {
                    "page": comments.page,
                    "next": comments.next_num,
                    "prev": comments.prev_num,
                    "pages": comments.pages,
                    "per_page": comments.per_page,
                    "total": comments.total,
                }
            },
            "success": True,
            "data": response.data,
        }

    @admins_only
    @comments_namespace.doc(
        description="Endpoint to create a Comment object",
        responses={
            200: ("Success", "CommentDetailedSuccessResponse"),
            400: (
                "An error occured processing the provided or stored data",
                "APISimpleErrorResponse",
            ),
        },
    )
    def post(self):
        req = request.get_json() or {}
        requested_type = get_comment_type(req)
        _ensure_comment_type_allowed(requested_type)
        req["type"] = requested_type

        # Always force author IDs to be the actual user
        req["author_id"] = session["id"]
        CommentModel = get_comment_model(data=req)

        m = CommentModel(**req)
        db.session.add(m)
        db.session.commit()

        schema = CommentSchema()

        response = schema.dump(m)
        db.session.close()

        return {"success": True, "data": response.data}


@comments_namespace.route("/<comment_id>")
class Comment(Resource):
    @admins_only
    @comments_namespace.doc(
        description="Endpoint to delete a specific Comment object",
        responses={200: ("Success", "APISimpleSuccessResponse")},
    )
    def delete(self, comment_id):
        comment = Comments.query.filter_by(id=comment_id).first_or_404()
        _ensure_comment_type_allowed(comment.type)
        db.session.delete(comment)
        db.session.commit()
        db.session.close()

        return {"success": True}
