import json
import os
import re

from werkzeug.utils import secure_filename

from CTFd.models import db
from CTFd.utils import get_config, uploads

DEFAULT_AI_SOURCE_REGEX = r"^https://chat\.deepseek\.com/share/[A-Za-z0-9_-]+$"
DEFAULT_SOLVER_TOTAL_SIZE_LIMIT = 10 * 1024 * 1024


class SubmissionMetadataError(ValueError):
    pass


def get_ai_sources(req):
    if req.is_json:
        data = req.get_json(silent=True) or {}
        sources = data.get("ai_sources", data.get("ai_source", []))
    else:
        sources = req.form.getlist("ai_source")

    if sources is None:
        sources = []
    elif isinstance(sources, str):
        sources = [sources]
    elif not isinstance(sources, (list, tuple)):
        raise SubmissionMetadataError("AI Source must be a string.")

    for source in sources:
        if not isinstance(source, str):
            raise SubmissionMetadataError("AI Source must be a string.")

    return [source.strip() for source in sources if source and source.strip()]


def serialize_ai_sources(req):
    sources = get_ai_sources(req)
    if not sources:
        return None
    return json.dumps(sources)


def get_solver_files(req):
    if req.is_json:
        return []
    return [f for f in req.files.getlist("solver") if f and f.filename]


def get_invalid_solver_filenames(req):
    invalid = []
    for file_obj in get_solver_files(req):
        if not secure_filename(file_obj.filename or ""):
            invalid.append(file_obj.filename)
    return invalid


def get_solver_file_size(file_obj):
    stream = file_obj.stream
    position = stream.tell()
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(position)
    return size


def validate_challenge_submission_metadata(challenge, req):
    try:
        ai_sources = get_ai_sources(req)
    except SubmissionMetadataError as e:
        return str(e)

    solver_files = get_solver_files(req)

    if challenge.require_ai_source and not ai_sources:
        return "AI Source is required for this challenge."

    configured_regex = get_config("ai_source_regex", DEFAULT_AI_SOURCE_REGEX)
    configured_regex = configured_regex.strip() if configured_regex else ""
    if configured_regex and ai_sources:
        try:
            ai_source_pattern = re.compile(configured_regex)
        except re.error:
            return "The configured AI Source regex is invalid."

        for source in ai_sources:
            if ai_source_pattern.fullmatch(source) is None:
                return "Please check again your AI Source."

    if challenge.require_solver and not solver_files:
        return "Solver / Script is required for this challenge."

    if get_invalid_solver_filenames(req):
        return "Solver / Script filename is invalid."

    file_limit = int(get_config("solver_file_limit", 0) or 0)
    if file_limit and len(solver_files) > file_limit:
        return f"Solver / Script accepts at most {file_limit} file(s)."

    total_size_limit = int(
        get_config("solver_total_size_limit", DEFAULT_SOLVER_TOTAL_SIZE_LIMIT) or 0
    )
    total_size = sum(get_solver_file_size(file_obj) for file_obj in solver_files)
    if total_size_limit and total_size > total_size_limit:
        return "Solver / Script files exceed the total size limit."

    return None


def delete_solver_file_locations(files):
    uploader = uploads.get_uploader()
    for file_obj in files:
        if getattr(file_obj, "location", None):
            uploader.delete(file_obj.location)


def save_solver_files(submission_id, req, commit=True):
    invalid_filenames = get_invalid_solver_filenames(req)
    if invalid_filenames:
        raise SubmissionMetadataError("Solver / Script filename is invalid.")

    saved = []
    try:
        for file_obj in get_solver_files(req):
            saved.append(
                uploads.upload_file(
                    file=file_obj,
                    submission_id=submission_id,
                    type="submission",
                    commit=commit,
                )
            )
    except Exception:
        delete_solver_file_locations(saved)
        raise
    return saved


def delete_solver_files_for_submission(submission, commit=True):
    uploader = uploads.get_uploader()
    for solver_file in list(submission.solver_files):
        uploader.delete(filename=solver_file.location)
        db.session.delete(solver_file)

    if commit:
        db.session.commit()
