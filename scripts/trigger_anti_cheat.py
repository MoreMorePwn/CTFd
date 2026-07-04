#!/usr/bin/env python3
import datetime
import hashlib
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from CTFd import create_app  # noqa: E402
from CTFd.models import (  # noqa: E402
    AntiCheatEvents,
    ChallengeFiles,
    Challenges,
    Fails,
    Solves,
    SubmissionFiles,
    Teams,
    Tracking,
    Users,
    db,
)
from CTFd.utils import get_config  # noqa: E402
from CTFd.utils.anti_cheat import analyze_submission  # noqa: E402


def create_user(stamp, slug):
    user = Users(
        name=f"anti-cheat-{slug}-{stamp}",
        email=f"anti-cheat-{slug}-{stamp}@examplectf.com",
        password="password",
        type="user",
        verified=True,
    )
    db.session.add(user)
    db.session.flush()
    return user


def create_team(stamp, slug, user):
    team = Teams(
        name=f"anti-cheat-{slug}-{stamp}",
        email=f"anti-cheat-{slug}-{stamp}@teams.examplectf.com",
        password="password",
    )
    db.session.add(team)
    db.session.flush()
    user.team_id = team.id
    team.captain_id = user.id
    db.session.flush()
    return team


def create_challenge(stamp, slug, with_file=False):
    challenge = Challenges(
        name=f"anti-cheat-{slug}-{stamp}",
        description="Anti-cheat detector trigger fixture.",
        category="anti-cheat",
        value=100,
        type="standard",
        state="visible",
        logic="any",
    )
    db.session.add(challenge)
    db.session.flush()

    challenge_file = None
    if with_file:
        challenge_file = ChallengeFiles(
            challenge_id=challenge.id,
            location=f"anti-cheat/{stamp}/{slug}.txt",
            sha1sum=hashlib.sha1(f"{stamp}:{slug}".encode()).hexdigest(),
        )
        db.session.add(challenge_file)
        db.session.flush()

    return challenge, challenge_file


def submission_kwargs(
    user, team, challenge, when, ip, user_agent, browser_fingerprint, provided
):
    return {
        "user_id": user.id,
        "team_id": team.id if team else None,
        "challenge_id": challenge.id,
        "date": when,
        "ip": ip,
        "user_agent": user_agent,
        "browser_fingerprint": browser_fingerprint,
        "provided": provided,
    }


def create_solve(
    user,
    team,
    challenge,
    when,
    ip,
    user_agent,
    browser_fingerprint,
    provided,
    ai_source=None,
):
    solve = Solves(
        **submission_kwargs(
            user,
            team,
            challenge,
            when,
            ip,
            user_agent,
            browser_fingerprint,
            provided,
        ),
        ai_source=ai_source,
    )
    db.session.add(solve)
    db.session.flush()
    return solve


def create_fail(user, team, challenge, when, ip, user_agent, browser_fingerprint, provided):
    fail = Fails(
        **submission_kwargs(
            user,
            team,
            challenge,
            when,
            ip,
            user_agent,
            browser_fingerprint,
            provided,
        )
    )
    db.session.add(fail)
    db.session.flush()
    return fail


def add_solver_file(submission, stamp, slug, sha1sum):
    solver_file = SubmissionFiles(
        submission_id=submission.id,
        location=f"submissions/anti-cheat/{stamp}/{slug}.py",
        sha1sum=sha1sum,
    )
    db.session.add(solver_file)
    db.session.flush()
    return solver_file


def track(event_type, user, target, when, ip, user_agent, browser_fingerprint):
    db.session.add(
        Tracking(
            type=event_type,
            user_id=user.id,
            target=target,
            date=when,
            ip=ip,
            user_agent=user_agent,
            browser_fingerprint=browser_fingerprint,
        )
    )
    db.session.flush()


def run():
    app = create_app()
    with app.app_context():
        stamp = str(time.time_ns())
        started_at = datetime.datetime.utcnow()
        now = started_at.replace(microsecond=0)
        user_mode = get_config("user_mode")

        alpha = create_user(stamp, "alpha")
        beta = create_user(stamp, "beta")
        alpha_team = beta_team = None
        if user_mode == "teams":
            alpha_team = create_team(stamp, "alpha", alpha)
            beta_team = create_team(stamp, "beta", beta)

        main_challenge, main_file = create_challenge(stamp, "main", with_file=True)
        context_challenge, _ = create_challenge(stamp, "context")
        burst_challenges = [
            create_challenge(stamp, f"burst-{index}")[0] for index in range(1, 4)
        ]

        shared_ai_source = "https://chat.deepseek.com/share/anti-cheat-demo"
        shared_solver_sha1 = hashlib.sha1(f"shared-solver:{stamp}".encode()).hexdigest()
        alpha_ip = "198.51.100.10"
        beta_ip = "198.51.100.10"
        shared_ua = "AntiCheatTrigger/1.0"
        shared_fingerprint = f"anti-cheat-fingerprint-{stamp}"

        track(
            "challenges.open",
            alpha,
            main_challenge.id,
            now - datetime.timedelta(seconds=30),
            alpha_ip,
            shared_ua,
            shared_fingerprint,
        )
        track(
            "files.download",
            alpha,
            main_file.id,
            now - datetime.timedelta(seconds=15),
            alpha_ip,
            shared_ua,
            shared_fingerprint,
        )

        alpha_solve = create_solve(
            alpha,
            alpha_team,
            main_challenge,
            now,
            alpha_ip,
            shared_ua,
            shared_fingerprint,
            "flag{alpha}",
            ai_source=shared_ai_source,
        )
        add_solver_file(alpha_solve, stamp, "alpha", shared_solver_sha1)
        db.session.commit()
        analyze_submission(alpha_solve)

        beta_solve = create_solve(
            beta,
            beta_team,
            main_challenge,
            now + datetime.timedelta(seconds=10),
            beta_ip,
            shared_ua,
            shared_fingerprint,
            "flag{beta}",
            ai_source=shared_ai_source,
        )
        add_solver_file(beta_solve, stamp, "beta", shared_solver_sha1)
        db.session.commit()
        analyze_submission(beta_solve)

        for index, challenge in enumerate(burst_challenges):
            solve = create_solve(
                alpha,
                alpha_team,
                challenge,
                now + datetime.timedelta(seconds=20 + index * 5),
                alpha_ip,
                shared_ua,
                shared_fingerprint,
                f"flag{{burst-{index}}}",
            )
            db.session.commit()
            analyze_submission(solve)

        shared_wrong = create_fail(
            alpha,
            alpha_team,
            main_challenge,
            now + datetime.timedelta(seconds=40),
            alpha_ip,
            shared_ua,
            shared_fingerprint,
            "shared-wrong-answer",
        )
        db.session.commit()
        analyze_submission(shared_wrong)

        last_wrong = None
        for index in range(8):
            last_wrong = create_fail(
                beta,
                beta_team,
                main_challenge,
                now + datetime.timedelta(seconds=45 + index),
                beta_ip,
                shared_ua,
                shared_fingerprint,
                "shared-wrong-answer",
            )
            db.session.commit()
        analyze_submission(last_wrong)

        last_context = None
        for index in range(4):
            last_context = create_fail(
                beta,
                beta_team,
                context_challenge,
                now + datetime.timedelta(seconds=70 + index),
                f"203.0.113.{index + 10}",
                f"AntiCheatTrigger/{index}",
                f"anti-cheat-context-{index}",
                f"context-{index}",
            )
            db.session.commit()
        analyze_submission(last_context)

        events = (
            AntiCheatEvents.query.filter(AntiCheatEvents.created >= started_at)
            .order_by(AntiCheatEvents.id.asc())
            .all()
        )

        print(f"Created anti-cheat demo stamp: {stamp}")
        print(f"User mode: {user_mode}")
        print(f"Generated events: {len(events)}")
        for event in events:
            account = f"team={event.team_id}" if event.team_id else f"user={event.user_id}"
            print(
                "#{id} {severity} {type} {account} challenge={challenge} "
                "submission={submission} details={details}".format(
                    id=event.id,
                    severity=event.severity,
                    type=event.type,
                    account=account,
                    challenge=event.challenge_id,
                    submission=event.submission_id,
                    details=event.details,
                )
            )


if __name__ == "__main__":
    run()
