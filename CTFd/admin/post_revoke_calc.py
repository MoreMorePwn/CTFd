import datetime

from flask import jsonify, render_template, request, send_file

from CTFd.admin import admin
from CTFd.utils.admin_permissions import current_user_can_access_admin_permission
from CTFd.utils.decorators import admins_only
from CTFd.utils.post_revoke_calc import (
    build_pdf,
    calculate_post_revoke,
    reset_state_with_backup,
)
from CTFd.utils import config as ctf_config


def _can_write():
    return current_user_can_access_admin_permission("post_revoke_calc_write")


@admin.route("/admin/post-revoke-calc", methods=["GET"])
@admins_only
def post_revoke_calc():
    data = calculate_post_revoke(
        bracket_id=request.args.get("bracket_id"),
        sort_by=request.args.get("sort", "pre"),
    )
    return render_template(
        "admin/post_revoke_calc.html",
        data=data,
        rows=data["rows"],
        brackets=data["brackets"],
        selected_bracket_id=data["bracket_id"],
        selected_sort=request.args.get("sort", "pre"),
        can_write=_can_write(),
    )


@admin.route("/admin/post-revoke-calc/export.pdf", methods=["GET"])
@admins_only
def post_revoke_calc_export():
    pdf = build_pdf(bracket_id=request.args.get("bracket_id"))
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = "{}.post_revoke_calc.{}.pdf".format(ctf_config.ctf_name(), timestamp)
    return send_file(
        pdf,
        mimetype="application/pdf",
        as_attachment=True,
        attachment_filename=filename,
        cache_timeout=-1,
    )


@admin.route("/admin/post-revoke-calc/reset", methods=["POST"])
@admins_only
def post_revoke_calc_reset():
    data = request.get_json(silent=True) or request.form
    if data.get("confirmation") != "RESET POST REVOKE CALC":
        return (
            jsonify(
                {
                    "success": False,
                    "errors": {
                        "confirmation": [
                            "Type RESET POST REVOKE CALC to reset Post-Revoke Calc"
                        ]
                    },
                }
            ),
            400,
        )

    backup_path = reset_state_with_backup()
    return jsonify(
        {
            "success": True,
            "data": {
                "backup": str(backup_path),
            },
        }
    )
