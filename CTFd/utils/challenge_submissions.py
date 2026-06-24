import json
import os
import re

from CTFd.utils import get_config, uploads

DEFAULT_AI_SOURCE_REGEX = r"^https://chat\.deepseek\.com/share/[A-Za-z0-9_-]+$"
DEFAULT_SOLVER_TOTAL_SIZE_LIMIT = 10 * 1024 * 1024


def get_ai_sources(req):
    if req.is_json:
        data = req.get_json(silent=True) or {}
        sources = data.get("ai_sources", data.get("ai_source", []))
        if isinstance(sources, str):
            sources = [sources]
    else:
        sources = req.form.getlist("ai_source")

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


def get_solver_file_size(file_obj):
    stream = file_obj.stream
    position = stream.tell()
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(position)
    return size


def validate_challenge_submission_metadata(challenge, req):
    ai_sources = get_ai_sources(req)
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


def save_solver_files(submission_id, req):
    saved = []
    for file_obj in get_solver_files(req):
        saved.append(
            uploads.upload_file(
                file=file_obj,
                submission_id=submission_id,
                type="submission",
            )
        )
    return saved
