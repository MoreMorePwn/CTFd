# -*- coding: utf-8 -*-

from CTFd.models import PostRevokeCalcAccounts, Users
from CTFd.utils.post_revoke_calc import (
    calculate_post_revoke,
    update_account_state,
    update_award_state,
    update_solve_state,
)
from tests.helpers import (
    create_ctfd,
    destroy_ctfd,
    gen_award,
    gen_challenge,
    gen_solve,
    gen_user,
    login_as_user,
)


def _row(data, name):
    for row in data["rows"]:
        if row["name"] == name:
            return row
    raise AssertionError("Missing row {}".format(name))


def test_post_revoke_calc_simulates_bans_revoke_and_partial_scores():
    app = create_ctfd()
    with app.app_context():
        challenge = gen_challenge(
            app.db,
            name="dynamic",
            value=300,
            initial=500,
            decay=100,
            minimum=100,
            function="linear",
        )
        alice = gen_user(app.db, name="alice", email="alice@examplectf.com")
        bob = gen_user(app.db, name="bob", email="bob@examplectf.com")
        carol = gen_user(app.db, name="carol", email="carol@examplectf.com")

        gen_solve(app.db, user_id=alice.id, challenge_id=challenge.id)
        gen_solve(app.db, user_id=bob.id, challenge_id=challenge.id)
        carol_solve = gen_solve(app.db, user_id=carol.id, challenge_id=challenge.id)
        bob_award = gen_award(app.db, user_id=bob.id, name="bonus", value=50)

        data = calculate_post_revoke()
        assert _row(data, "alice")["post_score"] == 300
        assert _row(data, "bob")["post_score"] == 350
        assert _row(data, "carol")["post_score"] == 300

        update_account_state(alice.id, manual_banned=True, note="calc ban only")
        update_award_state(bob_award.id, percentage=50)

        data = calculate_post_revoke(sort_by="post")
        assert _row(data, "alice")["post_score"] == 0
        assert _row(data, "alice")["calc_banned"] is True
        assert _row(data, "alice")["note"] == "calc ban only"
        assert _row(data, "bob")["post_score"] == 425
        assert _row(data, "carol")["post_score"] == 400
        assert Users.query.get(alice.id).banned is False

        update_solve_state(carol_solve.id, revoked=True)

        data = calculate_post_revoke(sort_by="post")
        assert _row(data, "bob")["post_score"] == 525
        assert _row(data, "carol")["post_score"] == 0

    destroy_ctfd(app)


def test_post_revoke_calc_real_ban_affects_calc_without_manual_ban():
    app = create_ctfd()
    with app.app_context():
        challenge = gen_challenge(app.db, name="static", value=100)
        user = gen_user(app.db, name="banned-user", email="banned@examplectf.com")
        gen_solve(app.db, user_id=user.id, challenge_id=challenge.id)

        user.banned = True
        app.db.session.commit()

        data = calculate_post_revoke()
        row = _row(data, "banned-user")
        assert row["real_banned"] is True
        assert row["calc_banned"] is True
        assert row["manual_banned"] is False
        assert row["post_score"] == 0
        assert PostRevokeCalcAccounts.query.count() == 0

    destroy_ctfd(app)


def test_post_revoke_calc_assistant_permissions_read_and_write():
    app = create_ctfd()
    with app.app_context():
        challenge = gen_challenge(app.db, name="static", value=100)
        user = gen_user(app.db, name="player", email="player@examplectf.com")
        gen_solve(app.db, user_id=user.id, challenge_id=challenge.id)
        user_id = user.id

        gen_user(
            app.db,
            name="read-assistant",
            email="read-assistant@examplectf.com",
            type="assistant",
            assistant_permissions='["post_revoke_calc_read"]',
        )
        with login_as_user(app, name="read-assistant") as client:
            r = client.get("/admin/post-revoke-calc")
            assert r.status_code == 200
            assert "Post-Revoke Calc" in r.get_data(as_text=True)

            r = client.get("/api/v1/post-revoke-calc")
            assert r.status_code == 200

            r = client.patch(
                "/api/v1/post-revoke-calc/accounts/{}".format(user_id),
                json={"manual_banned": True},
            )
            assert r.status_code == 403

        gen_user(
            app.db,
            name="write-assistant",
            email="write-assistant@examplectf.com",
            type="assistant",
            assistant_permissions='["post_revoke_calc_write"]',
        )
        with login_as_user(app, name="write-assistant") as client:
            r = client.patch(
                "/api/v1/post-revoke-calc/accounts/{}".format(user_id),
                json={"manual_banned": True, "note": "reviewed"},
            )
            assert r.status_code == 200
            assert any(row["name"] == "player" for row in r.get_json()["data"]["rows"])

        state = PostRevokeCalcAccounts.query.filter_by(account_id=user_id).first()
        assert state.manual_banned is True
        assert state.note == "reviewed"

    destroy_ctfd(app)
