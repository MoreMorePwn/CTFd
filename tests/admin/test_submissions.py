import json
from io import BytesIO

from werkzeug.datastructures import FileStorage

from CTFd.models import Users
from CTFd.utils.uploads import upload_file
from tests.helpers import (
    create_ctfd,
    destroy_ctfd,
    gen_challenge,
    gen_solve,
    login_as_user,
    register_user,
    simulate_user_activity,
)


def test_browse_admin_submissions():
    """Test that an admin can create a challenge properly"""
    app = create_ctfd()
    with app.app_context():
        register_user(app, name="RegisteredUser")
        user = Users.query.filter_by(id=2).first()
        simulate_user_activity(app.db, user)

        admin = login_as_user(app, name="admin", password="password")

        # It's difficult to do better checks here becase we're just doing string search.
        # incorrect includes the word correct and the navbar has correct and incorrect in it
        r = admin.get("/admin/submissions")
        assert r.status_code == 200
        assert "RegisteredUser" in r.get_data(as_text=True)
        assert "correct" in r.get_data(as_text=True)
        assert "incorrect" in r.get_data(as_text=True)

        r = admin.get("/admin/submissions/correct")
        assert r.status_code == 200
        assert "RegisteredUser" in r.get_data(as_text=True)
        assert "correct" in r.get_data(as_text=True)

        r = admin.get("/admin/submissions/incorrect")
        assert r.status_code == 200
        assert "RegisteredUser" in r.get_data(as_text=True)

        r = admin.get("/admin/submissions/correct?field=challenge_id&q=1")
        assert r.status_code == 200
        assert "RegisteredUser" in r.get_data(as_text=True)
    destroy_ctfd(app)


def test_admin_submissions_renders_ai_tooltip_and_solver_preview():
    """Admin submissions table exposes AI source hover text and solver preview controls"""
    app = create_ctfd()
    with app.app_context():
        register_user(app, name="RegisteredUser")
        challenge = gen_challenge(app.db)
        solve = gen_solve(
            app.db,
            user_id=2,
            challenge_id=challenge.id,
            ai_source=json.dumps(
                ["https://chat.deepseek.com/share/vn8ae7zevhkuwauy1m"]
            ),
        )
        solver_file = upload_file(
            file=FileStorage(stream=BytesIO(b"print('solve')\n"), filename="solve.py"),
            submission_id=solve.id,
            type="submission",
        )
        solver_location = solver_file.location

        admin = login_as_user(app, name="admin", password="password")
        r = admin.get("/admin/submissions")
        html = r.get_data(as_text=True)

        assert r.status_code == 200
        assert 'class="submission-ai-source-link"' in html
        assert 'title="https://chat.deepseek.com/share/vn8ae7zevhkuwauy1m"' in html
        assert 'class="btn btn-link p-0 solver-preview-button"' in html
        assert f'data-solver-url="/files/{solver_location}"' in html
        assert 'data-solver-name="solve.py"' in html
        assert 'id="solver-preview-modal"' in html
    destroy_ctfd(app)
