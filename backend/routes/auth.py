"""
MANA — Auth Routes
Endpoints:
  POST /api/auth/login
  POST /api/auth/logout
  GET  /api/auth/me
  PATCH /api/auth/me
  POST /api/auth/change-password
  POST /api/auth/request-email-change
  POST /api/auth/verify-email-change
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity, unset_jwt_cookies
)

auth_bp = Blueprint("auth", __name__)

# Placeholder user store — replace with your DB model
USERS = {
    "admin_mana": {"password": "mana2026!", "role": "LGU Analyst", "email": "lgu.analyst@mana.ph"}
}


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Body: { username, password, remember }
    Returns: { token, user: { username, role, email } }
    """
    data     = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")

    user = USERS.get(username)
    if not user or user["password"] != password:
        return jsonify({"message": "Invalid credentials"}), 401

    token = create_access_token(identity=username)
    return jsonify({
        "token": token,
        "user":  {"username": username, "role": user["role"], "email": user["email"]},
    })


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """Returns: { success: true }"""
    return jsonify({"success": True})


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_profile():
    """Returns: { username, role, email }"""
    username = get_jwt_identity()
    user     = USERS.get(username)
    if not user:
        return jsonify({"message": "User not found"}), 404
    return jsonify({"username": username, "role": user["role"], "email": user["email"]})


@auth_bp.route("/me", methods=["PATCH"])
@jwt_required()
def update_profile():
    """Body: { username?, role? }  Returns: updated user"""
    username = get_jwt_identity()
    data     = request.get_json()
    user     = USERS.get(username, {})
    if "role" in data:
        user["role"] = data["role"]
    # username change would require re-issuing a token — handle in production
    USERS[username] = user
    return jsonify({"username": username, "role": user["role"], "email": user["email"]})


@auth_bp.route("/change-password", methods=["POST"])
@jwt_required()
def change_password():
    """Body: { current_password, new_password }  Returns: { success }"""
    username = get_jwt_identity()
    data     = request.get_json()
    user     = USERS.get(username)
    if not user or user["password"] != data.get("current_password"):
        return jsonify({"message": "Current password is incorrect"}), 400
    user["password"] = data.get("new_password")
    return jsonify({"success": True})


@auth_bp.route("/request-email-change", methods=["POST"])
@jwt_required()
def request_email_change():
    """Body: { new_email }  Returns: { success } — sends verification code in production"""
    # TODO: generate code, store in DB, send email via SMTP
    return jsonify({"success": True})


@auth_bp.route("/verify-email-change", methods=["POST"])
@jwt_required()
def verify_email_change():
    """Body: { new_email, code }  Returns: { success, email }"""
    # TODO: validate code from DB, update user email
    data  = request.get_json()
    email = data.get("new_email")
    return jsonify({"success": True, "email": email})
