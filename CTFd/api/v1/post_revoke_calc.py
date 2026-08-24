from flask import request
from flask_restx import Namespace, Resource

from CTFd.utils.decorators import admins_only
from CTFd.utils.post_revoke_calc import (
    calculate_post_revoke,
    get_account_detail,
    get_challenge_detail,
    update_account_state,
    update_award_state,
    update_solve_state,
)

post_revoke_calc_namespace = Namespace(
    "post-revoke-calc", description="Endpoint to retrieve Post-Revoke Calc data"
)


def _serialize(data, include_details=False):
    serialized = {
        "mode": data["mode"],
        "account_type": data["account_type"],
        "bracket_id": data["bracket_id"],
        "brackets": [
            {
                "id": bracket.id,
                "name": bracket.name,
                "type": bracket.type,
            }
            for bracket in data["brackets"]
        ],
        "rows": data["rows"],
        "challenge_rows": data["challenge_rows"],
    }
    if include_details:
        serialized["details"] = data["details"]
    return serialized


def _request_data():
    return request.get_json(silent=True) or {}


@post_revoke_calc_namespace.route("")
class PostRevokeCalcList(Resource):
    @admins_only
    def get(self):
        data = calculate_post_revoke(
            bracket_id=request.args.get("bracket_id"),
            sort_by=request.args.get("sort", "pre"),
        )
        return {"success": True, "data": _serialize(data)}


@post_revoke_calc_namespace.route("/accounts/<int:account_id>")
@post_revoke_calc_namespace.param("account_id", "An account ID")
class PostRevokeCalcAccount(Resource):
    @admins_only
    def get(self, account_id):
        detail = get_account_detail(
            account_id=account_id,
            bracket_id=request.args.get("bracket_id"),
        )
        if detail is None:
            return {"success": False, "errors": {"id": ["Account not found"]}}, 404
        return {"success": True, "data": detail}

    @admins_only
    def patch(self, account_id):
        data = _request_data()
        update_account_state(
            account_id=account_id,
            manual_banned=data.get("manual_banned"),
            note=data.get("note"),
        )
        refreshed = calculate_post_revoke(
            bracket_id=request.args.get("bracket_id"),
            sort_by=request.args.get("sort", "pre"),
        )
        return {"success": True, "data": _serialize(refreshed)}


@post_revoke_calc_namespace.route("/challenges/<int:challenge_id>")
@post_revoke_calc_namespace.param("challenge_id", "A challenge ID")
class PostRevokeCalcChallenge(Resource):
    @admins_only
    def get(self, challenge_id):
        detail = get_challenge_detail(
            challenge_id=challenge_id,
            bracket_id=request.args.get("bracket_id"),
        )
        if detail is None:
            return {"success": False, "errors": {"id": ["Challenge not found"]}}, 404
        return {"success": True, "data": detail}


@post_revoke_calc_namespace.route("/solves/<int:solve_id>")
@post_revoke_calc_namespace.param("solve_id", "A solve ID")
class PostRevokeCalcSolve(Resource):
    @admins_only
    def patch(self, solve_id):
        data = _request_data()
        try:
            update_solve_state(
                solve_id=solve_id,
                percentage=data.get("percentage"),
                revoked=data.get("revoked"),
                note=data.get("note"),
            )
        except ValueError as e:
            return {"success": False, "errors": {"percentage": [str(e)]}}, 400
        refreshed = calculate_post_revoke(
            bracket_id=request.args.get("bracket_id"),
            sort_by=request.args.get("sort", "pre"),
        )
        return {"success": True, "data": _serialize(refreshed)}


@post_revoke_calc_namespace.route("/awards/<int:award_id>")
@post_revoke_calc_namespace.param("award_id", "An award ID")
class PostRevokeCalcAward(Resource):
    @admins_only
    def patch(self, award_id):
        data = _request_data()
        try:
            update_award_state(
                award_id=award_id,
                percentage=data.get("percentage"),
                revoked=data.get("revoked"),
                note=data.get("note"),
            )
        except ValueError as e:
            return {"success": False, "errors": {"percentage": [str(e)]}}, 400
        refreshed = calculate_post_revoke(
            bracket_id=request.args.get("bracket_id"),
            sort_by=request.args.get("sort", "pre"),
        )
        return {"success": True, "data": _serialize(refreshed)}
