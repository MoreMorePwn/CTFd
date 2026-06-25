from typing import List

from flask import abort, request
from flask_restx import Namespace, Resource

from CTFd.api.v1.helpers.request import validate_args
from CTFd.api.v1.helpers.schemas import sqlalchemy_to_pydantic
from CTFd.api.v1.schemas import APIDetailedSuccessResponse, APIListSuccessResponse
from CTFd.constants import RawEnum
from CTFd.models import Files, db
from CTFd.schemas.files import FileSchema
from CTFd.utils import uploads
from CTFd.utils.admin_permissions import current_user_can_access_admin_permission
from CTFd.utils.decorators import admins_only
from CTFd.utils.helpers.models import build_model_filters

files_namespace = Namespace("files", description="Endpoint to retrieve Files")

FileModel = sqlalchemy_to_pydantic(Files)


class FileDetailedSuccessResponse(APIDetailedSuccessResponse):
    data: FileModel


class FileListSuccessResponse(APIListSuccessResponse):
    data: List[FileModel]


files_namespace.schema_model(
    "FileDetailedSuccessResponse", FileDetailedSuccessResponse.apidoc()
)

files_namespace.schema_model(
    "FileListSuccessResponse", FileListSuccessResponse.apidoc()
)


def _allowed_file_types():
    if current_user_can_access_admin_permission("files"):
        return None

    allowed = set()
    if current_user_can_access_admin_permission("challenges"):
        allowed.add("challenge")
    if current_user_can_access_admin_permission("pages"):
        allowed.add("page")
    return allowed


def _requested_file_type(args):
    if args.get("type"):
        return args["type"]
    if args.get("challenge_id") or args.get("challenge"):
        return "challenge"
    if args.get("page_id") or args.get("page"):
        return "page"
    if args.get("solution_id") or args.get("solution"):
        return "solution"
    return "standard"


def _ensure_file_type_allowed(file_type):
    allowed_types = _allowed_file_types()
    if allowed_types is None:
        return
    if file_type not in allowed_types:
        abort(403)


@files_namespace.route("")
class FilesList(Resource):
    @admins_only
    @files_namespace.doc(
        description="Endpoint to get file objects in bulk",
        responses={
            200: ("Success", "FileListSuccessResponse"),
            400: (
                "An error occured processing the provided or stored data",
                "APISimpleErrorResponse",
            ),
        },
    )
    @validate_args(
        {
            "type": (str, None),
            "location": (str, None),
            "q": (str, None),
            "field": (
                RawEnum("FileFields", {"type": "type", "location": "location"}),
                None,
            ),
        },
        location="query",
    )
    def get(self, query_args):
        q = query_args.pop("q", None)
        field = str(query_args.pop("field", None))
        filters = build_model_filters(model=Files, query=q, field=field)
        allowed_types = _allowed_file_types()
        requested_type = query_args.get("type")

        if allowed_types is not None:
            if requested_type:
                _ensure_file_type_allowed(requested_type)
            else:
                filters.append(Files.type.in_(allowed_types))

        files = Files.query.filter_by(**query_args).filter(*filters).all()
        schema = FileSchema(many=True)
        response = schema.dump(files)

        if response.errors:
            return {"success": False, "errors": response.errors}, 400

        return {"success": True, "data": response.data}

    @admins_only
    @files_namespace.doc(
        description="Endpoint to get file objects in bulk",
        responses={
            200: ("Success", "FileDetailedSuccessResponse"),
            400: (
                "An error occured processing the provided or stored data",
                "APISimpleErrorResponse",
            ),
        },
        params={
            "file": {
                "in": "formData",
                "type": "file",
                "required": True,
                "description": "The file to upload",
            }
        },
    )
    @validate_args(
        {
            "challenge_id": (int, None),
            "challenge": (int, None),
            "page_id": (int, None),
            "page": (int, None),
            "solution_id": (int, None),
            "solution": (int, None),
            "type": (str, None),
            "location": (str, None),
        },
        location="form",
    )
    def post(self, form_args):
        requested_type = _requested_file_type(form_args)
        _ensure_file_type_allowed(requested_type)
        form_args["type"] = requested_type

        files = request.files.getlist("file")
        location = form_args.get("location")
        # challenge_id
        # page_id

        # Handle situation where users attempt to upload multiple files with a single location
        if len(files) > 1 and location:
            return {
                "success": False,
                "errors": {
                    "location": ["Location cannot be specified with multiple files"]
                },
            }, 400

        objs = []
        for f in files:
            # uploads.upload_file(file=f, chalid=req.get('challenge'))
            try:
                obj = uploads.upload_file(file=f, **form_args)
            except ValueError as e:
                return {
                    "success": False,
                    "errors": {"location": [str(e)]},
                }, 400
            objs.append(obj)

        schema = FileSchema(many=True)
        response = schema.dump(objs)

        if response.errors:
            return {"success": False, "errors": response.errors}, 400

        return {"success": True, "data": response.data}


@files_namespace.route("/<file_id>")
class FilesDetail(Resource):
    @admins_only
    @files_namespace.doc(
        description="Endpoint to get a specific file object",
        responses={
            200: ("Success", "FileDetailedSuccessResponse"),
            400: (
                "An error occured processing the provided or stored data",
                "APISimpleErrorResponse",
            ),
        },
    )
    def get(self, file_id):
        f = Files.query.filter_by(id=file_id).first_or_404()
        _ensure_file_type_allowed(f.type)
        schema = FileSchema()
        response = schema.dump(f)

        if response.errors:
            return {"success": False, "errors": response.errors}, 400

        return {"success": True, "data": response.data}

    @admins_only
    @files_namespace.doc(
        description="Endpoint to delete a file object",
        responses={200: ("Success", "APISimpleSuccessResponse")},
    )
    def delete(self, file_id):
        f = Files.query.filter_by(id=file_id).first_or_404()
        _ensure_file_type_allowed(f.type)

        uploads.delete_file(file_id=f.id)
        db.session.delete(f)
        db.session.commit()
        db.session.close()

        return {"success": True}
