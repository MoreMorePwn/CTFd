# -*- coding: utf-8 -*-

from CTFd.models import db
from CTFd.utils.tickets import create_ticket, pending_tickets_for_user
from tests.helpers import (
    create_ctfd,
    destroy_ctfd,
    gen_team,
    gen_user,
    login_as_user,
    register_user,
)


def test_admin_can_create_and_progress_ticket():
    """Tickets notify the target while pending and enforce the admin flow"""
    app = create_ctfd()
    with app.app_context():
        register_user(app, name="target", email="target@examplectf.com")
        register_user(app, name="other", email="other@examplectf.com")

        with login_as_user(app, "admin") as client:
            r = client.post(
                "/api/v1/tickets",
                json={
                    "target_id": 2,
                    "title": "Ticket title",
                    "message": "**Needs action**",
                    "notification_type": "alert",
                    "sound": False,
                },
            )
            assert r.status_code == 200
            ticket = r.get_json()["data"]
            assert ticket["status"] == "pending"
            assert ticket["target_name"] == "target"
            assert "<strong>Needs action</strong>" in ticket["html"]

            ticket_id = ticket["id"]
            r = client.patch(
                f"/api/v1/tickets/{ticket_id}",
                json={"status": "resolved", "resolve_note": "Done"},
            )
            assert r.status_code == 400

        with login_as_user(app, "target") as client:
            r = client.get("/api/v1/tickets/pending")
            assert r.status_code == 200
            pending = r.get_json()["data"]
            assert len(pending) == 1
            assert pending[0]["title"] == "Ticket title"

        with login_as_user(app, "other") as client:
            r = client.get("/api/v1/tickets/pending")
            assert r.status_code == 200
            assert r.get_json()["data"] == []

        with login_as_user(app, "admin") as client:
            r = client.patch(
                f"/api/v1/tickets/{ticket_id}",
                json={"status": "ongoing"},
            )
            assert r.status_code == 200
            assert r.get_json()["data"]["status"] == "ongoing"

        with login_as_user(app, "target") as client:
            r = client.get("/api/v1/tickets/pending")
            assert r.status_code == 200
            assert r.get_json()["data"] == []

        with login_as_user(app, "admin") as client:
            r = client.patch(
                f"/api/v1/tickets/{ticket_id}",
                json={"status": "resolved"},
            )
            assert r.status_code == 400

            r = client.patch(
                f"/api/v1/tickets/{ticket_id}",
                json={"status": "resolved", "resolve_note": "Handled"},
            )
            assert r.status_code == 200
            assert r.get_json()["data"]["status"] == "resolved"

            r = client.patch(
                f"/api/v1/tickets/{ticket_id}",
                json={"status": "ongoing"},
            )
            assert r.status_code == 400
    destroy_ctfd(app)


def test_ticket_assistant_permission_controls_admin_access():
    """Assistants need the Ticket permission to use the ticket admin section"""
    app = create_ctfd()
    with app.app_context():
        gen_user(
            db,
            name="ticket_assistant",
            email="ticket_assistant@examplectf.com",
            password="password",
            type="assistant",
            assistant_permissions='["tickets"]',
        )
        gen_user(
            db,
            name="stats_assistant",
            email="stats_assistant@examplectf.com",
            password="password",
            type="assistant",
            assistant_permissions='["statistics"]',
        )

        with login_as_user(app, "ticket_assistant") as client:
            assert client.get("/admin/tickets").status_code == 200
            assert client.get("/api/v1/tickets", json=True).status_code == 200

        with login_as_user(app, "stats_assistant") as client:
            assert client.get("/admin/tickets").status_code == 403
            assert client.get("/api/v1/tickets", json=True).status_code == 403
    destroy_ctfd(app)


def test_ticket_creation_publishes_realtime_event():
    """Ticket creation publishes a targeted SSE event for immediate alerts"""
    app = create_ctfd(user_mode="teams")
    with app.app_context():
        team = gen_team(db, name="realtime_team", member_count=1)
        published = []

        def capture_event(data, type=None, id=None, channel="ctf"):
            published.append(
                {
                    "data": data,
                    "type": type,
                    "id": id,
                    "channel": channel,
                }
            )

        app.events_manager.publish = capture_event

        with login_as_user(app, "admin") as client:
            r = client.post(
                "/api/v1/tickets",
                json={
                    "target_id": team.id,
                    "title": "Realtime ticket",
                    "message": "Open now",
                    "notification_type": "toast",
                    "sound": True,
                },
            )

        assert r.status_code == 200
        assert len(published) == 1
        assert published[0]["type"] == "ticket"
        assert published[0]["channel"] == "ctf"
        assert published[0]["data"]["target_id"] == team.id
        assert published[0]["data"]["target_type"] == "team"
        assert published[0]["data"]["title"] == "Realtime ticket"
        assert published[0]["data"]["content"] == "Open now"
        assert published[0]["data"]["type"] == "toast"
        assert published[0]["data"]["sound"] is True
    destroy_ctfd(app)


def test_team_ticket_pending_alert_follows_current_membership():
    """Team-mode tickets alert every current team member while pending"""
    app = create_ctfd(user_mode="teams")
    with app.app_context():
        team = gen_team(db, name="target_team", member_count=1)
        first_member = team.members[0]
        ticket = create_ticket(
            target_id=team.id,
            title="Team ticket",
            message="Team message",
            notification_type="toast",
            sound=True,
            created_by_id=1,
        )
        late_member = gen_user(
            db,
            name="late_member",
            email="late_member@examplectf.com",
            team_id=team.id,
        )

        assert pending_tickets_for_user(first_member) == [ticket]
        assert pending_tickets_for_user(late_member) == [ticket]

        ticket.status = "ongoing"
        db.session.commit()

        assert pending_tickets_for_user(first_member) == []
        assert pending_tickets_for_user(late_member) == []
    destroy_ctfd(app)
