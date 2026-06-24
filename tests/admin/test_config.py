from tests.helpers import create_ctfd, destroy_ctfd, login_as_user


def test_reset_route_removed():
    app = create_ctfd()
    with app.app_context():
        client = login_as_user(app, name="admin", password="password")

        r = client.get("/admin/reset")
        assert r.status_code == 404

        with client.session_transaction() as sess:
            data = {"nonce": sess.get("nonce"), "accounts": "on"}
            r = client.post("/admin/reset", data=data)
            assert r.status_code == 404

        r = client.get("/admin/config")
        assert b"/admin/reset" not in r.data

    destroy_ctfd(app)


def test_user_mode_route_removed():
    app = create_ctfd()
    with app.app_context():
        client = login_as_user(app, name="admin", password="password")

        with client.session_transaction() as sess:
            data = {"nonce": sess.get("nonce"), "user_mode": "users"}
            r = client.post("/admin/user_mode", data=data)
            assert r.status_code == 404

        r = client.get("/admin/config")
        assert b"Danger zone" not in r.data
        assert b"User Mode" not in r.data

    destroy_ctfd(app)
