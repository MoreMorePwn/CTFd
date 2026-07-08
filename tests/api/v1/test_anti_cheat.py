# -*- coding: utf-8 -*-

from CTFd.models import AntiCheatEvents, db
from tests.helpers import create_ctfd, destroy_ctfd, login_as_user


def test_admin_can_review_anti_cheat_event_from_ui_and_api():
    """Admins can review anti-cheat events from the admin UI and API"""
    app = create_ctfd()
    with app.app_context():
        event = AntiCheatEvents(
            type="shared_ip",
            severity="high",
            details="Shared IP detected during quality check",
            reviewed=False,
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id

        with login_as_user(app, "admin") as client:
            r = client.get("/admin/anti-cheat")
            assert r.status_code == 200
            assert "Shared IP detected during quality check" in r.get_data(as_text=True)

            with client.session_transaction() as sess:
                nonce = sess.get("nonce")
            r = client.post(
                f"/admin/anti-cheat/{event_id}/review",
                data={"reviewed": "true", "nonce": nonce},
            )
            assert r.status_code == 302

            event = AntiCheatEvents.query.get(event_id)
            assert event.reviewed is True
            assert event.reviewer_id == 1
            assert event.reviewed_at is not None

            r = client.patch(f"/api/v1/anti-cheat/{event_id}", json={"reviewed": False})
            assert r.status_code == 200
            assert r.get_json()["data"]["reviewed"] is False

            event = AntiCheatEvents.query.get(event_id)
            assert event.reviewed is False
            assert event.reviewer_id is None
            assert event.reviewed_at is None
    destroy_ctfd(app)
