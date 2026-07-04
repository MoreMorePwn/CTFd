import datetime

from flask import current_app, has_request_context, request

from CTFd.models import (
    AntiCheatEvents,
    ChallengeFiles,
    Fails,
    Solves,
    Submissions,
    SubmissionFiles,
    Tracking,
    db,
)
from CTFd.utils import get_config
from CTFd.utils.user import get_ip


RECENT_WINDOW = datetime.timedelta(hours=24)
FAST_AFTER_OPEN_SECONDS = 120
FAST_AFTER_DOWNLOAD_SECONDS = 120
BURST_SOLVES_SECONDS = 60
BURST_SOLVES_COUNT = 3
WRONG_BURST_SECONDS = 60
WRONG_BURST_COUNT = 8
MACHINE_SPEED_SECONDS = 2
MACHINE_SPEED_COUNT = 5
IP_CHURN_COUNT = 4
USER_AGENT_CHURN_COUNT = 4
BROWSER_FINGERPRINT_CHURN_COUNT = 4


def get_user_agent(req=None):
    if req is None:
        if not has_request_context():
            return None
        req = request

    user_agent = req.headers.get("User-Agent", "").strip()
    if not user_agent:
        return None
    return user_agent[:512]


def get_browser_fingerprint(req=None):
    if req is None:
        if not has_request_context():
            return None
        req = request

    fingerprint = (
        req.headers.get("X-CTFd-Browser-Fingerprint")
        or req.headers.get("X-Browser-Fingerprint")
        or ""
    )
    if not fingerprint:
        data = req.form
        if not data:
            data = req.get_json(silent=True) or {}
        fingerprint = data.get("browser_fingerprint", "")

    fingerprint = str(fingerprint).strip()
    if not fingerprint:
        return None
    return fingerprint[:128]


def _is_team_account(submission):
    return get_config("user_mode") == "teams" and submission.team_id is not None


def _account_label(submission):
    if _is_team_account(submission):
        return "team", submission.team_id
    return "user", submission.user_id


def _same_account(query, model, submission):
    if _is_team_account(submission):
        return query.filter(model.team_id == submission.team_id)
    return query.filter(model.user_id == submission.user_id)


def _different_account(query, model, submission):
    if _is_team_account(submission):
        return query.filter(model.team_id != submission.team_id)
    return query.filter(model.user_id != submission.user_id)


def _same_account_submission(other, submission):
    if _is_team_account(submission):
        return other.team_id == submission.team_id
    return other.user_id == submission.user_id


def _account_user_ids(submission):
    if _is_team_account(submission) and submission.team:
        member_ids = [member.id for member in submission.team.members]
        return member_ids or [submission.user_id]
    return [submission.user_id]


def _submission_time(submission):
    return submission.date or datetime.datetime.utcnow()


def _safe_details(value):
    if value is None:
        return ""
    value = str(value)
    if len(value) > 1000:
        return value[:997] + "..."
    return value


def record_event(
    event_type,
    severity,
    submission=None,
    details=None,
    user_id=None,
    team_id=None,
    challenge_id=None,
    submission_id=None,
    ip=None,
    user_agent=None,
    browser_fingerprint=None,
    commit=True,
):
    details = _safe_details(details)
    if submission is not None:
        user_id = submission.user_id
        team_id = submission.team_id
        challenge_id = submission.challenge_id
        submission_id = submission.id
        ip = submission.ip
        user_agent = submission.user_agent
        browser_fingerprint = submission.browser_fingerprint

    existing = AntiCheatEvents.query.filter_by(
        type=event_type,
        user_id=user_id,
        team_id=team_id,
        challenge_id=challenge_id,
        submission_id=submission_id,
    ).filter(AntiCheatEvents.details == details).first()
    if existing:
        return existing

    event = AntiCheatEvents(
        type=event_type,
        severity=severity,
        details=details,
        user_id=user_id,
        team_id=team_id,
        challenge_id=challenge_id,
        submission_id=submission_id,
        ip=ip,
        user_agent=user_agent,
        browser_fingerprint=browser_fingerprint,
    )
    db.session.add(event)
    if commit:
        db.session.commit()
    return event


def _record(submission, event_type, severity, details):
    return record_event(
        event_type=event_type,
        severity=severity,
        submission=submission,
        details=details,
        commit=False,
    )


def _detect_ai_source_reuse(submission):
    sources = set(submission.ai_sources)
    if not sources:
        return

    matches = []
    candidates = (
        Submissions.query.filter(Submissions.id != submission.id)
        .filter(Submissions.ai_source.isnot(None))
        .order_by(Submissions.date.desc())
        .limit(500)
        .all()
    )
    for candidate in candidates:
        if _same_account_submission(candidate, submission):
            continue
        overlap = sorted(sources.intersection(candidate.ai_sources))
        if overlap:
            account_type, account_id = _account_label(candidate)
            matches.append(
                "{} {} submission {}: {}".format(
                    account_type,
                    account_id,
                    candidate.id,
                    ", ".join(overlap[:3]),
                )
            )

    if matches:
        _record(
            submission,
            "ai_source_reuse",
            "medium",
            "AI Source was also submitted by {}".format("; ".join(matches[:5])),
        )


def _detect_solver_reuse(submission):
    solver_files = list(submission.solver_files or [])
    if not solver_files:
        return

    matches = []
    for solver_file in solver_files:
        if not solver_file.sha1sum:
            continue
        reused_files = (
            SubmissionFiles.query.join(
                Submissions, SubmissionFiles.submission_id == Submissions.id
            )
            .filter(SubmissionFiles.sha1sum == solver_file.sha1sum)
            .filter(SubmissionFiles.submission_id != submission.id)
            .order_by(Submissions.date.desc())
            .limit(20)
            .all()
        )
        for reused_file in reused_files:
            other = reused_file.submission
            if other is None or _same_account_submission(other, submission):
                continue
            account_type, account_id = _account_label(other)
            matches.append(
                "{} {} submission {} file {}".format(
                    account_type, account_id, other.id, reused_file.id
                )
            )

    if matches:
        _record(
            submission,
            "solver_file_reuse",
            "high",
            "Solver file hash was also submitted by {}".format("; ".join(matches[:5])),
        )


def _detect_solve_timing(submission):
    if submission.type != "correct":
        return

    solved_at = _submission_time(submission)
    user_ids = _account_user_ids(submission)

    open_track = (
        Tracking.query.filter_by(type="challenges.open", target=submission.challenge_id)
        .filter(Tracking.user_id.in_(user_ids))
        .filter(Tracking.date <= solved_at)
        .order_by(Tracking.date.asc())
        .first()
    )
    if open_track is None:
        _record(
            submission,
            "solve_without_open",
            "medium",
            "Solved without a recorded challenge open event for this account.",
        )
    else:
        elapsed = (solved_at - open_track.date).total_seconds()
        if elapsed <= FAST_AFTER_OPEN_SECONDS:
            _record(
                submission,
                "fast_solve_after_open",
                "medium",
                "Solved {:.1f}s after the first recorded challenge open.".format(elapsed),
            )

    file_ids = [
        file_id
        for (file_id,) in ChallengeFiles.query.with_entities(ChallengeFiles.id)
        .filter_by(challenge_id=submission.challenge_id)
        .all()
    ]
    if not file_ids:
        return

    download_track = (
        Tracking.query.filter_by(type="files.download")
        .filter(Tracking.target.in_(file_ids))
        .filter(Tracking.user_id.in_(user_ids))
        .filter(Tracking.date <= solved_at)
        .order_by(Tracking.date.asc())
        .first()
    )
    if download_track is None:
        _record(
            submission,
            "solve_without_download",
            "medium",
            "Solved a challenge with files without a recorded file download.",
        )
    else:
        elapsed = (solved_at - download_track.date).total_seconds()
        if elapsed <= FAST_AFTER_DOWNLOAD_SECONDS:
            _record(
                submission,
                "fast_solve_after_download",
                "medium",
                "Solved {:.1f}s after the first recorded challenge file download.".format(
                    elapsed
                ),
            )


def _detect_burst_solves(submission):
    if submission.type != "correct":
        return

    since = _submission_time(submission) - datetime.timedelta(seconds=BURST_SOLVES_SECONDS)
    solves = _same_account(Solves.query, Solves, submission).filter(Solves.date >= since)
    count = solves.count()
    if count >= BURST_SOLVES_COUNT:
        _record(
            submission,
            "burst_solves",
            "medium",
            "{} solves were recorded for this account in {} seconds.".format(
                count, BURST_SOLVES_SECONDS
            ),
        )


def _detect_wrong_submission_patterns(submission):
    if submission.type != "incorrect":
        return

    submitted_at = _submission_time(submission)
    since = submitted_at - datetime.timedelta(seconds=WRONG_BURST_SECONDS)
    wrongs = (
        _same_account(Fails.query, Fails, submission)
        .filter(Fails.challenge_id == submission.challenge_id)
        .filter(Fails.date >= since)
        .order_by(Fails.date.asc())
        .all()
    )

    if len(wrongs) >= WRONG_BURST_COUNT:
        _record(
            submission,
            "wrong_submission_burst",
            "medium",
            "{} wrong submissions were recorded on this challenge in {} seconds.".format(
                len(wrongs), WRONG_BURST_SECONDS
            ),
        )

    fast_intervals = 0
    previous = None
    for wrong in wrongs:
        if previous is not None:
            elapsed = (wrong.date - previous.date).total_seconds()
            if elapsed <= MACHINE_SPEED_SECONDS:
                fast_intervals += 1
        previous = wrong
    if fast_intervals >= MACHINE_SPEED_COUNT:
        _record(
            submission,
            "machine_speed_wrong_submissions",
            "high",
            "{} consecutive wrong-submission intervals were under {} seconds.".format(
                fast_intervals, MACHINE_SPEED_SECONDS
            ),
        )

    if submission.provided:
        shared_wrong = (
            _different_account(Fails.query, Fails, submission)
            .filter(Fails.challenge_id == submission.challenge_id)
            .filter(Fails.provided == submission.provided)
            .order_by(Fails.date.desc())
            .first()
        )
        if shared_wrong:
            account_type, account_id = _account_label(shared_wrong)
            _record(
                submission,
                "shared_wrong_answer",
                "medium",
                "Same wrong answer was also submitted by {} {} in submission {}.".format(
                    account_type, account_id, shared_wrong.id
                ),
            )


def _detect_identity_context(submission):
    submitted_at = _submission_time(submission)
    since = submitted_at - RECENT_WINDOW

    if submission.ip:
        shared_ip = (
            _different_account(Submissions.query, Submissions, submission)
            .filter(Submissions.ip == submission.ip)
            .filter(Submissions.date >= since)
            .order_by(Submissions.date.desc())
            .first()
        )
        if shared_ip:
            account_type, account_id = _account_label(shared_ip)
            _record(
                submission,
                "shared_submission_ip",
                "low",
                "IP {} was also used by {} {} in submission {}.".format(
                    submission.ip, account_type, account_id, shared_ip.id
                ),
            )

        account_ips = {
            ip
            for (ip,) in _same_account(
                Submissions.query.with_entities(Submissions.ip), Submissions, submission
            )
            .filter(Submissions.date >= since)
            .filter(Submissions.ip.isnot(None))
            .all()
            if ip
        }
        if len(account_ips) >= IP_CHURN_COUNT:
            _record(
                submission,
                "ip_churn",
                "low",
                "{} distinct IPs were used by this account in the last 24 hours.".format(
                    len(account_ips)
                ),
            )

    if submission.user_agent:
        shared_user_agent = (
            _different_account(Submissions.query, Submissions, submission)
            .filter(Submissions.user_agent == submission.user_agent)
            .filter(Submissions.date >= since)
            .order_by(Submissions.date.desc())
            .first()
        )
        if shared_user_agent:
            account_type, account_id = _account_label(shared_user_agent)
            _record(
                submission,
                "shared_user_agent",
                "low",
                "User-Agent was also used by {} {} in submission {}.".format(
                    account_type, account_id, shared_user_agent.id
                ),
            )

        account_user_agents = {
            user_agent
            for (user_agent,) in _same_account(
                Submissions.query.with_entities(Submissions.user_agent),
                Submissions,
                submission,
            )
            .filter(Submissions.date >= since)
            .filter(Submissions.user_agent.isnot(None))
            .all()
            if user_agent
        }
        if len(account_user_agents) >= USER_AGENT_CHURN_COUNT:
            _record(
                submission,
                "user_agent_churn",
                "low",
                "{} distinct User-Agents were used by this account in the last 24 hours.".format(
                    len(account_user_agents)
                ),
            )

    if submission.browser_fingerprint:
        shared_browser = (
            _different_account(Submissions.query, Submissions, submission)
            .filter(Submissions.browser_fingerprint == submission.browser_fingerprint)
            .filter(Submissions.date >= since)
            .order_by(Submissions.date.desc())
            .first()
        )
        if shared_browser:
            account_type, account_id = _account_label(shared_browser)
            _record(
                submission,
                "shared_browser_fingerprint",
                "medium",
                "Browser fingerprint was also used by {} {} in submission {}.".format(
                    account_type, account_id, shared_browser.id
                ),
            )

        account_fingerprints = {
            fingerprint
            for (fingerprint,) in _same_account(
                Submissions.query.with_entities(Submissions.browser_fingerprint),
                Submissions,
                submission,
            )
            .filter(Submissions.date >= since)
            .filter(Submissions.browser_fingerprint.isnot(None))
            .all()
            if fingerprint
        }
        if len(account_fingerprints) >= BROWSER_FINGERPRINT_CHURN_COUNT:
            _record(
                submission,
                "browser_fingerprint_churn",
                "low",
                "{} distinct browser fingerprints were used by this account in the last 24 hours.".format(
                    len(account_fingerprints)
                ),
            )


def analyze_submission(submission):
    try:
        db.session.add(submission)
        _detect_ai_source_reuse(submission)
        _detect_solver_reuse(submission)
        _detect_solve_timing(submission)
        _detect_burst_solves(submission)
        _detect_wrong_submission_patterns(submission)
        _detect_identity_context(submission)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Anti-cheat analysis failed")


def track_challenge_file_download(file_obj, user=None, req=None):
    if user is None or getattr(user, "type", None) in ("admin", "assistant"):
        return

    try:
        event = Tracking(
            type="files.download",
            ip=get_ip(req=req),
            user_agent=get_user_agent(req=req),
            browser_fingerprint=get_browser_fingerprint(req=req),
            user_id=user.id,
            target=file_obj.id,
        )
        db.session.add(event)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Anti-cheat file download tracking failed")
