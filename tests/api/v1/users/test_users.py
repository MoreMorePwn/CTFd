#!/usr/bin/env python
# -*- coding: utf-8 -*-

from CTFd.models import Users, db
from CTFd.utils.crypto import verify_password
from tests.helpers import (
    create_ctfd,
    destroy_ctfd,
    gen_challenge,
    gen_fail,
    gen_solve,
    gen_team,
    gen_user,
    login_as_user,
    register_user,
)


def test_api_self_ban():
    """PATCH /api/v1/users/<user_id> should not allow a user to ban themselves"""
    app = create_ctfd()
    with app.app_context():
        with login_as_user(app, name="admin") as client:
            r = client.patch("/api/v1/users/1", json={"banned": True})
            resp = r.get_json()
            assert r.status_code == 400
            assert resp["success"] == False
            assert resp["errors"] == {"id": "You cannot ban yourself"}
    destroy_ctfd(app)


def test_api_modify_user_type():
    """Can an admin promote a user to admin and demote them to user"""
    app = create_ctfd()
    with app.app_context():
        register_user(app)
        with login_as_user(app, "admin") as client:
            r = client.patch("/api/v1/users/2", json={"type": "admin"})
            assert r.status_code == 200
            user_data = r.get_json()["data"]
            assert user_data["name"] == "user"
            assert user_data["type"] == "admin"

            r = client.patch("/api/v1/users/2", json={"type": "user"})
            assert r.status_code == 200
            user_data = r.get_json()["data"]
            assert user_data["name"] == "user"
            assert user_data["type"] == "user"
    destroy_ctfd(app)


def test_api_admin_can_create_assistant_with_permissions():
    """A full admin can create an Assistant account with scoped admin permissions"""
    app = create_ctfd()
    with app.app_context():
        with login_as_user(app, "admin") as client:
            r = client.post(
                "/api/v1/users",
                json={
                    "name": "assistant",
                    "email": "assistant@examplectf.com",
                    "password": "password",
                    "type": "assistant",
                    "assistant_permissions": ["users_write", "monitor", "invalid"],
                },
            )

            assert r.status_code == 200
            user_data = r.get_json()["data"]
            assert user_data["type"] == "assistant"
            assert user_data["assistant_permissions"] == [
                "users_write",
                "monitor",
                "users_read",
            ]

            assistant = Users.query.filter_by(name="assistant").first()
            assert assistant.type == "assistant"
            assert assistant.assistant_permission_list == [
                "users_write",
                "monitor",
                "users_read",
            ]
    destroy_ctfd(app)


def test_api_assistant_access_is_limited_to_granted_sections():
    """An Assistant can access granted admin sections but not other admin sections"""
    app = create_ctfd()
    with app.app_context():
        gen_user(
            db,
            name="assistant",
            email="assistant@examplectf.com",
            password="password",
            type="assistant",
            assistant_permissions='["users_read"]',
        )

        with login_as_user(app, "assistant") as client:
            r = client.get("/admin")
            assert r.status_code == 302
            assert r.location.endswith("/admin/users")

            assert client.get("/admin/users").status_code == 200
            r = client.get("/api/v1/users?view=admin", json=True)
            assert r.status_code == 200

            assert client.get("/admin/statistics").status_code == 403
            assert client.get("/api/v1/statistics/users", json=True).status_code == 403
    destroy_ctfd(app)


def test_assistant_sees_admin_panel_nav_link():
    """Assistants should see the Admin Panel link outside admin-only routes"""
    app = create_ctfd()
    with app.app_context():
        gen_user(
            db,
            name="assistant",
            email="assistant@examplectf.com",
            password="password",
            type="assistant",
            assistant_permissions='["submissions_read"]',
        )

        with login_as_user(app, "assistant") as client:
            r = client.get("/")
            assert r.status_code == 200
            assert b"Admin Panel" in r.data
    destroy_ctfd(app)


def test_api_assistant_user_read_cannot_write_users():
    """Assistants with Users Read access can inspect users but cannot edit them"""
    app = create_ctfd()
    with app.app_context():
        register_user(app)
        gen_user(
            db,
            name="assistant",
            email="assistant@examplectf.com",
            password="password",
            type="assistant",
            assistant_permissions='["users_read"]',
        )

        with login_as_user(app, "assistant") as client:
            assert client.get("/api/v1/users?view=admin", json=True).status_code == 200

            r = client.patch("/api/v1/users/2", json={"hidden": True})
            assert r.status_code == 403
            assert Users.query.get(2).hidden is False

            r = client.post(
                "/api/v1/users",
                json={
                    "name": "newuser",
                    "email": "newuser@examplectf.com",
                    "password": "password",
                },
            )
            assert r.status_code == 403
    destroy_ctfd(app)


def test_api_assistant_user_write_cannot_manage_roles_or_privileged_accounts():
    """Assistants with Users Write access cannot promote users or manage admins/assistants"""
    app = create_ctfd()
    with app.app_context():
        register_user(app)
        gen_user(
            db,
            name="assistant",
            email="assistant@examplectf.com",
            password="password",
            type="assistant",
            assistant_permissions='["users_write"]',
        )

        with login_as_user(app, "assistant") as client:
            r = client.patch("/api/v1/users/2", json={"hidden": True})
            assert r.status_code == 200
            assert Users.query.get(2).hidden is True

            r = client.patch("/api/v1/users/2", json={"type": "admin"})
            assert r.status_code == 403
            assert Users.query.get(2).type == "user"

            r = client.patch("/api/v1/users/1", json={"hidden": False})
            assert r.status_code == 403
            assert Users.query.get(1).type == "admin"

            r = client.delete("/api/v1/users/1", json=True)
            assert r.status_code == 403
            assert Users.query.get(1) is not None
    destroy_ctfd(app)


def test_api_assistant_submission_read_cannot_write_submissions():
    """Assistants with Submissions Read can inspect but not mutate submissions"""
    app = create_ctfd()
    with app.app_context():
        gen_user(
            db,
            name="assistant",
            email="assistant@examplectf.com",
            password="password",
            type="assistant",
            assistant_permissions='["submissions_read"]',
        )

        with login_as_user(app, "assistant") as client:
            assert client.get("/admin").status_code == 302
            assert client.get("/admin").location.endswith("/admin/submissions")
            assert client.get("/admin/submissions").status_code == 200
            assert client.get("/api/v1/submissions", json=True).status_code == 200

            r = client.patch("/api/v1/submissions/1", json={"type": "correct"})
            assert r.status_code == 403
            assert client.delete("/api/v1/submissions/1", json=True).status_code == 403
    destroy_ctfd(app)


def test_api_assistant_team_read_cannot_write_teams():
    """Assistants with Teams Read access can inspect teams but cannot edit them"""
    app = create_ctfd(user_mode="teams")
    with app.app_context():
        team = gen_team(db)
        team_id = team.id
        gen_user(
            db,
            name="assistant",
            email="assistant@examplectf.com",
            password="password",
            type="assistant",
            assistant_permissions='["teams_read"]',
        )

        with login_as_user(app, "assistant") as client:
            assert client.get("/admin/teams").status_code == 200
            assert client.get("/api/v1/teams?view=admin", json=True).status_code == 200

            r = client.patch(f"/api/v1/teams/{team_id}", json={"hidden": True})
            assert r.status_code == 403
            assert db.session.query(type(team)).get(team_id).hidden is False
    destroy_ctfd(app)


def test_api_assistant_team_write_can_write_teams():
    """Assistants with Teams Write access can edit teams"""
    app = create_ctfd(user_mode="teams")
    with app.app_context():
        team = gen_team(db)
        team_id = team.id
        gen_user(
            db,
            name="assistant",
            email="assistant@examplectf.com",
            password="password",
            type="assistant",
            assistant_permissions='["teams_write"]',
        )

        with login_as_user(app, "assistant") as client:
            r = client.patch(f"/api/v1/teams/{team_id}", json={"hidden": True})
            assert r.status_code == 200
            assert db.session.query(type(team)).get(team_id).hidden is True
    destroy_ctfd(app)


def test_api_assistant_user_read_does_not_leak_submission_secrets():
    """Users Read assistants should not receive submitted flags or solver metadata"""
    app = create_ctfd()
    with app.app_context():
        user = gen_user(db, name="player", email="player@examplectf.com")
        challenge = gen_challenge(db)
        gen_solve(
            db,
            user_id=user.id,
            challenge_id=challenge.id,
            provided="flag{secret-solve}",
            ip="10.0.0.1",
            ai_source="https://chat.deepseek.com/share/secret",
        )
        gen_fail(
            db,
            user_id=user.id,
            challenge_id=challenge.id,
            provided="wrong-secret",
            ip="10.0.0.2",
        )
        gen_user(
            db,
            name="assistant",
            email="assistant@examplectf.com",
            password="password",
            type="assistant",
            assistant_permissions='["users_read"]',
        )
        user_id = user.id

        with login_as_user(app, "assistant") as client:
            r = client.get(f"/api/v1/users/{user_id}/solves", json=True)
            assert r.status_code == 200
            response_text = r.get_data(as_text=True)
            solve = r.get_json()["data"][0]
            assert "provided" not in solve
            assert "ip" not in solve
            assert "ai_source" not in solve
            assert "solver_files" not in solve
            assert "flag{secret-solve}" not in response_text
            assert "https://chat.deepseek.com/share/secret" not in response_text

            r = client.get(f"/api/v1/users/{user_id}/fails", json=True)
            assert r.status_code == 200
            assert r.get_json()["data"] == []
            assert "wrong-secret" not in r.get_data(as_text=True)
    destroy_ctfd(app)


def test_api_assistant_team_read_does_not_leak_submission_secrets():
    """Teams Read assistants should not receive submitted flags or solver metadata"""
    app = create_ctfd(user_mode="teams")
    with app.app_context():
        team = gen_team(db)
        user = team.members[0]
        challenge = gen_challenge(db)
        gen_solve(
            db,
            user_id=user.id,
            team_id=team.id,
            challenge_id=challenge.id,
            provided="flag{team-secret-solve}",
            ip="10.0.0.3",
            ai_source="https://chat.deepseek.com/share/team-secret",
        )
        gen_fail(
            db,
            user_id=user.id,
            team_id=team.id,
            challenge_id=challenge.id,
            provided="wrong-team-secret",
            ip="10.0.0.4",
        )
        gen_user(
            db,
            name="assistant",
            email="assistant@examplectf.com",
            password="password",
            type="assistant",
            assistant_permissions='["teams_read"]',
        )
        team_id = team.id

        with login_as_user(app, "assistant") as client:
            r = client.get(f"/api/v1/teams/{team_id}/solves", json=True)
            assert r.status_code == 200
            response_text = r.get_data(as_text=True)
            solve = r.get_json()["data"][0]
            assert "provided" not in solve
            assert "ip" not in solve
            assert "ai_source" not in solve
            assert "solver_files" not in solve
            assert "flag{team-secret-solve}" not in response_text
            assert "https://chat.deepseek.com/share/team-secret" not in response_text

            r = client.get(f"/api/v1/teams/{team_id}/fails", json=True)
            assert r.status_code == 200
            assert r.get_json()["data"] == []
            assert "wrong-team-secret" not in r.get_data(as_text=True)
    destroy_ctfd(app)


def test_api_can_query_by_user_emails():
    """Can an admin user query /api/v1/users using a user's email address"""
    app = create_ctfd()
    with app.app_context():
        register_user(app, name="testuser", email="user@findme.com")
        with login_as_user(app, "testuser") as client:
            r = client.get("/api/v1/users?field=email&q=findme", json=True)
            assert r.status_code == 400
            assert r.get_json()["errors"].get("field")
        with login_as_user(app, "admin") as client:
            r = client.get("/api/v1/users?field=email&q=findme", json=True)
            assert r.status_code == 200
            assert r.get_json()["data"][0]["id"] == 2
    destroy_ctfd(app)


def test_api_user_can_update_password_if_none_not_if_set():
    """Can a user set their password if they do not currently have a password"""
    app = create_ctfd()
    with app.app_context():
        # Create a user with a null password. Use raw SQL to bypass SQLAlchemy validates
        register_user(app, name="testuser", email="user@examplectf.com")
        db.session.execute("UPDATE users SET password=NULL WHERE name='testuser'")
        user = Users.query.filter_by(name="testuser").first()
        db.session.commit()
        assert user.password is None

        with app.test_client() as client:
            # Login as user
            with client.session_transaction() as sess:
                sess["id"] = user.id
            r = client.get("/api/v1/users/me", json=True)
            assert r.status_code == 200

            # Test that user can change password
            user = Users.query.filter_by(name="testuser").first()
            assert user.password is None
            data = {"password": "12345", "confirm": "password"}
            r = client.patch("/api/v1/users/me", json=data)
            assert r.status_code == 200

            # Verify password is now set
            user = Users.query.filter_by(name="testuser").first()
            assert verify_password(plaintext="12345", ciphertext=user.password)

            # Verify that password cannot be changed
            data = {"password": "noset", "confirm": "password"}
            r = client.patch("/api/v1/users/me", json=data)
            resp = r.get_json()
            assert resp["errors"]["confirm"] == ["Your previous password is incorrect"]
            assert r.status_code == 400

            # Verify a regular user cannot patch another user
            register_user(
                app,
                name="testuser2",
                email="user2@examplectf.com",
                password="testinguser",
            )
            testuser = Users.query.filter_by(name="testuser2").first()
            assert verify_password(
                plaintext="testinguser", ciphertext=testuser.password
            )
            data = {"password": "password", "confirm": "password"}
            r = client.patch("/api/v1/users/3", json=data)
            assert r.status_code == 403
            testuser = Users.query.filter_by(name="testuser2").first()
            assert verify_password(
                plaintext="testinguser", ciphertext=testuser.password
            )

    destroy_ctfd(app)
