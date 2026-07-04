import datetime
import hashlib

from CTFd.models import (
    AntiCheatEvents,
    ChallengeFiles,
    Solves,
    SubmissionFiles,
    Tracking,
    db,
)
from CTFd.utils.anti_cheat import analyze_submission
from tests.helpers import create_ctfd, destroy_ctfd, gen_challenge, gen_user


def _solve(user, challenge, when, ip, user_agent, browser_fingerprint, ai_source=None):
    solve = Solves(
        user_id=user.id,
        challenge_id=challenge.id,
        ip=ip,
        user_agent=user_agent,
        browser_fingerprint=browser_fingerprint,
        provided="flag",
        ai_source=ai_source,
        date=when,
    )
    db.session.add(solve)
    db.session.flush()
    return solve


def test_anti_cheat_detects_reuse_and_missing_activity():
    app = create_ctfd()
    try:
        with app.app_context():
            now = datetime.datetime.utcnow().replace(microsecond=0)
            user_a = gen_user(db, name="anti-a", email="anti-a@examplectf.com")
            user_b = gen_user(db, name="anti-b", email="anti-b@examplectf.com")
            challenge = gen_challenge(db, name="anti-cheat-challenge")
            challenge_file = ChallengeFiles(
                challenge_id=challenge.id,
                location="anti-cheat/test.bin",
                sha1sum=hashlib.sha1(b"challenge").hexdigest(),
            )
            db.session.add(challenge_file)
            db.session.commit()

            shared_ai_source = "https://chat.deepseek.com/share/anti-cheat-test"
            shared_solver_hash = hashlib.sha1(b"solver").hexdigest()
            user_agent = "AntiCheatTest/1.0"
            browser_fingerprint = "anti-cheat-browser-fingerprint"

            db.session.add(
                Tracking(
                    type="challenges.open",
                    user_id=user_a.id,
                    target=challenge.id,
                    ip="198.51.100.1",
                    user_agent=user_agent,
                    browser_fingerprint=browser_fingerprint,
                    date=now - datetime.timedelta(seconds=20),
                )
            )
            db.session.add(
                Tracking(
                    type="files.download",
                    user_id=user_a.id,
                    target=challenge_file.id,
                    ip="198.51.100.1",
                    user_agent=user_agent,
                    browser_fingerprint=browser_fingerprint,
                    date=now - datetime.timedelta(seconds=10),
                )
            )

            solve_a = _solve(
                user_a,
                challenge,
                now,
                "198.51.100.1",
                user_agent,
                browser_fingerprint,
                ai_source=shared_ai_source,
            )
            db.session.add(
                SubmissionFiles(
                    submission_id=solve_a.id,
                    location="submissions/anti-a.py",
                    sha1sum=shared_solver_hash,
                )
            )
            db.session.commit()
            analyze_submission(solve_a)

            solve_b = _solve(
                user_b,
                challenge,
                now + datetime.timedelta(seconds=5),
                "198.51.100.1",
                user_agent,
                browser_fingerprint,
                ai_source=shared_ai_source,
            )
            db.session.add(
                SubmissionFiles(
                    submission_id=solve_b.id,
                    location="submissions/anti-b.py",
                    sha1sum=shared_solver_hash,
                )
            )
            db.session.commit()
            analyze_submission(solve_b)

            event_types = {
                event.type
                for event in AntiCheatEvents.query.filter_by(
                    submission_id=solve_b.id
                ).all()
            }

            assert "ai_source_reuse" in event_types
            assert "solver_file_reuse" in event_types
            assert "solve_without_open" in event_types
            assert "solve_without_download" in event_types
            assert "shared_submission_ip" in event_types
            assert "shared_user_agent" in event_types
            assert "shared_browser_fingerprint" in event_types
    finally:
        destroy_ctfd(app)
