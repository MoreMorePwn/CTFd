#!/usr/bin/env python
# -*- coding: utf-8 -*-

from CTFd.models import Comments
from tests.helpers import (
    create_ctfd,
    destroy_ctfd,
    gen_challenge,
    gen_comment,
    gen_user,
    login_as_user,
    register_user,
)


def test_api_post_comments():
    app = create_ctfd()
    with app.app_context():
        gen_challenge(app.db)
        with login_as_user(app, "admin") as admin:
            r = admin.post(
                "/api/v1/comments",
                json={
                    "content": "this is a challenge comment",
                    "type": "challenge",
                    "challenge_id": 1,
                },
            )
            # Check that POST response has comment data
            assert r.status_code == 200
            resp = r.get_json()
            assert resp["data"]["content"] == "this is a challenge comment"
            assert "this is a challenge comment" in resp["data"]["html"]
            assert resp["data"]["type"] == "challenge"

            # Check that the comment shows up in the list of comments for the given challenge
            r = admin.get("/api/v1/comments?challenge_id=1", json="")
            assert r.status_code == 200
            resp = r.get_json()
            assert resp["data"][0]["content"] == "this is a challenge comment"
            assert "this is a challenge comment" in resp["data"][0]["html"]
            assert resp["data"][0]["type"] == "challenge"
    destroy_ctfd(app)


def test_api_post_comments_with_invalid_author_id():
    app = create_ctfd()
    with app.app_context():
        gen_challenge(app.db)
        register_user(app)
        with login_as_user(app, "admin") as admin:
            r = admin.post(
                "/api/v1/comments",
                json={
                    "content": "this is a challenge comment",
                    "type": "challenge",
                    "challenge_id": 1,
                    "author_id": 2,
                },
            )
            # Check that POST response has comment data
            assert r.status_code == 200
            resp = r.get_json()
            assert resp["data"]["author_id"] == 1
    destroy_ctfd(app)


def test_api_get_comments():
    app = create_ctfd()
    with app.app_context():
        gen_challenge(app.db)
        with login_as_user(app, "admin") as admin:
            gen_comment(
                app.db,
                content="this is a challenge comment",
                author_id=1,
                challenge_id=1,
            )
            r = admin.get("/api/v1/comments", json="")

            # Check that the comment shows up in the list of all comments
            assert r.status_code == 200
            resp = r.get_json()
            assert resp["data"][0]["content"] == "this is a challenge comment"
            assert "this is a challenge comment" in resp["data"][0]["html"]
            assert resp["data"][0]["type"] == "challenge"
    destroy_ctfd(app)


def test_api_delete_comments():
    app = create_ctfd()
    with app.app_context():
        gen_challenge(app.db)
        with login_as_user(app, "admin") as admin:
            gen_comment(
                app.db,
                content="this is a challenge comment",
                author_id=1,
                challenge_id=1,
            )
            assert Comments.query.count() == 1

            # Check that the comment can be deleted
            r = admin.delete("/api/v1/comments/1", json="")
            assert r.status_code == 200
            resp = r.get_json()
            assert Comments.query.count() == 0
            assert resp["success"] is True
    destroy_ctfd(app)


def test_api_challenge_assistant_cannot_access_user_comments():
    """Challenge assistants should not access user comments through the global comments API"""
    app = create_ctfd()
    with app.app_context():
        challenge = gen_challenge(app.db)
        user = gen_user(app.db, name="player", email="player@examplectf.com")
        challenge_comment = gen_comment(
            app.db,
            content="challenge note",
            author_id=1,
            challenge_id=challenge.id,
        )
        user_comment = gen_comment(
            app.db,
            content="private user note",
            author_id=1,
            type="user",
            user_id=user.id,
        )
        gen_user(
            app.db,
            name="assistant",
            email="assistant@examplectf.com",
            password="password",
            type="assistant",
            assistant_permissions='["challenges"]',
        )
        challenge_comment_id = challenge_comment.id
        user_comment_id = user_comment.id
        user_id = user.id

        with login_as_user(app, "assistant") as client:
            r = client.get("/api/v1/comments", json="")
            assert r.status_code == 200
            assert [c["id"] for c in r.get_json()["data"]] == [challenge_comment_id]

            r = client.get(f"/api/v1/comments?user_id={user_id}", json="")
            assert r.status_code == 403

            r = client.post(
                "/api/v1/comments",
                json={
                    "content": "tamper",
                    "type": "user",
                    "user_id": user_id,
                },
            )
            assert r.status_code == 403

            r = client.delete(f"/api/v1/comments/{user_comment_id}", json="")
            assert r.status_code == 403
            assert Comments.query.filter_by(id=user_comment_id).first() is not None
    destroy_ctfd(app)
