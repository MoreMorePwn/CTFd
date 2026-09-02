# -*- coding: utf-8 -*-

import json
from unittest.mock import Mock, patch

from requests.exceptions import Timeout

from CTFd.models import AnnouncerBotLogs
from CTFd.utils import set_config
from tests.helpers import (
    create_ctfd,
    destroy_ctfd,
    gen_challenge,
    gen_flag,
    gen_user,
    login_as_user,
)


def submit_flag(app, username, challenge_id, submission="flag"):
    with login_as_user(app, username) as client:
        return client.post(
            "/api/v1/challenges/attempt",
            json={"challenge_id": challenge_id, "submission": submission},
        )


def test_announcer_config_hides_webhook_and_validates_template():
    app = create_ctfd()
    with app.app_context():
        webhook = "https://discord.com/api/webhooks/secret"
        set_config("announcer_bot_webhook_url", webhook)

        with login_as_user(app, "admin") as client:
            r = client.get("/admin/config")
            html = r.get_data(as_text=True)
            assert r.status_code == 200
            assert "Announcer Bot" in html
            assert "Webhook configured" in html
            assert webhook not in html

            r = client.get("/api/v1/announcer-bot", json=True)
            assert r.status_code == 200
            data = r.get_json()["data"]
            assert data["webhook_configured"] is True
            assert "webhook_url" not in data

            r = client.patch(
                "/api/v1/announcer-bot",
                json={"template": "[not json"},
            )
            assert r.status_code == 400
    destroy_ctfd(app)


def test_announcer_posts_first_second_third_blood_for_visible_accounts():
    app = create_ctfd()
    with app.app_context():
        set_config("announcer_bot_webhook_url", "https://discord.example/webhook")
        set_config("announcer_bot_announce_solve", "false")

        challenge = gen_challenge(app.db, name="Honey Vault", category="web")
        gen_flag(app.db, challenge_id=challenge.id, content="flag")

        for name in ("alpha", "beta", "gamma", "delta"):
            gen_user(app.db, name=name, email=f"{name}@examplectf.com")

        response = Mock(status_code=204, text="")
        with patch("CTFd.utils.announcer_bot.requests.post", return_value=response) as post:
            for name in ("alpha", "beta", "gamma", "delta"):
                r = submit_flag(app, name, challenge.id)
                assert r.status_code == 200
                assert r.get_json()["data"]["status"] == "correct"

        assert post.call_count == 3
        titles = [call.kwargs["json"]["embeds"][0]["title"] for call in post.call_args_list]
        assert titles == ["First Blood", "Second Blood", "Third Blood"]
        descriptions = [
            call.kwargs["json"]["embeds"][0]["description"]
            for call in post.call_args_list
        ]
        assert descriptions[0] == "alpha has solved Honey Vault!"
        assert all(call.kwargs["json"]["allowed_mentions"] == {"parse": []} for call in post.call_args_list)
        assert AnnouncerBotLogs.query.count() == 3
    destroy_ctfd(app)


def test_announcer_ignores_hidden_and_banned_accounts_for_blood_rank():
    app = create_ctfd()
    with app.app_context():
        set_config("announcer_bot_webhook_url", "https://discord.example/webhook")

        challenge = gen_challenge(app.db, name="Hidden Filter", category="misc")
        gen_flag(app.db, challenge_id=challenge.id, content="flag")
        gen_user(app.db, name="hidden_solver", email="hidden@examplectf.com", hidden=True)
        gen_user(app.db, name="banned_solver", email="banned@examplectf.com", banned=True)
        gen_user(app.db, name="visible_solver", email="visible@examplectf.com")

        response = Mock(status_code=204, text="")
        with patch("CTFd.utils.announcer_bot.requests.post", return_value=response) as post:
            submit_flag(app, "hidden_solver", challenge.id)
            submit_flag(app, "banned_solver", challenge.id)
            submit_flag(app, "visible_solver", challenge.id)

        assert post.call_count == 1
        payload = post.call_args.kwargs["json"]
        assert payload["embeds"][0]["title"] == "First Blood"
        assert payload["embeds"][0]["description"] == "visible_solver has solved Hidden Filter!"
    destroy_ctfd(app)


def test_announcer_logs_webhook_failures_without_breaking_solves():
    app = create_ctfd()
    with app.app_context():
        set_config("announcer_bot_webhook_url", "https://discord.example/webhook")

        challenge = gen_challenge(app.db, name="Timeout Challenge", category="pwn")
        gen_flag(app.db, challenge_id=challenge.id, content="flag")
        gen_user(app.db, name="solver", email="solver@examplectf.com")

        with patch(
            "CTFd.utils.announcer_bot.requests.post",
            side_effect=Timeout("webhook timed out"),
        ):
            r = submit_flag(app, "solver", challenge.id)

        assert r.status_code == 200
        assert r.get_json()["data"]["status"] == "correct"

        log = AnnouncerBotLogs.query.one()
        assert log.success is False
        assert "webhook timed out" in log.error
        assert json.loads(log.payload)["embeds"][0]["title"] == "First Blood"
    destroy_ctfd(app)
