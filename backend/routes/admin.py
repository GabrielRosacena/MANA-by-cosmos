"""
MANA — Admin Routes
All endpoints require a valid JWT with role = "Admin".

Blueprinted at: /api/admin
Register in app.py:
    from routes.admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix="/api/admin")

Endpoints:
  POST   /api/admin/auth/login
  GET    /api/admin/users
  POST   /api/admin/users
  PATCH  /api/admin/users/<id>
  DELETE /api/admin/users/<id>
  PATCH  /api/admin/users/<id>/status
  POST   /api/admin/users/<id>/reset-password
  GET    /api/admin/logs
  GET    /api/admin/stats
  GET    /api/admin/settings
  PATCH  /api/admin/settings/<section>
"""

from functools import wraps
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity, get_jwt
)

admin_bp = Blueprint("admin", __name__)

# ── Role Guard Decorator ───────────────────────────────────────────────────────
def admin_required(fn):
    """Decorator that enforces role = Admin on top of JWT auth."""
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get("role") != "Admin":
            return jsonify({"message": "Admin access required."}), 403
        return fn(*args, **kwargs)
    return wrapper


# ── Admin Login ────────────────────────────────────────────────────────────────
@admin_bp.route("/auth/login", methods=["POST"])
def admin_login():
    """
    Body: { username, password }
    Returns: { token, admin: { id, name, email, role } }

    TODO: look up user in DB, verify password hash, check role == "Admin"
    """
    data     = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")

    # TODO: replace with real DB query
    # user = User.query.filter_by(username=username).first()
    # if not user or not user.check_password(password) or user.role != "Admin":
    #     return jsonify({"message": "Invalid credentials or insufficient role."}), 401

    # Pass role in additional_claims so admin_required can read it
    token = create_access_token(
        identity=username,
        additional_claims={"role": "Admin"}
    )
    return jsonify({
        "token": token,
        "admin": { "id": "u1", "name": username, "email": f"{username}@mana.ph", "role": "Admin" }
    })


# ── Users ──────────────────────────────────────────────────────────────────────
@admin_bp.route("/users", methods=["GET"])
@admin_required
def list_users():
    """
    Query: search, role, status
    Returns: User[]
    TODO: User.query.filter(…).all()
    """
    search = request.args.get("search", "")
    role   = request.args.get("role", "")
    status = request.args.get("status", "")
    # TODO: build SQLAlchemy query with filters
    return jsonify([])


@admin_bp.route("/users", methods=["POST"])
@admin_required
def create_user():
    """
    Body: { name, email, role, password }
    Returns: User
    TODO: hash password, create User record, commit
    """
    data = request.get_json()
    # TODO: new_user = User(name=data["name"], email=data["email"], role=data["role"])
    #       new_user.set_password(data["password"])
    #       db.session.add(new_user); db.session.commit()
    return jsonify({"message": "User created", "id": "new_id"}), 201


@admin_bp.route("/users/<user_id>", methods=["PATCH"])
@admin_required
def update_user(user_id):
    """Body: { name?, email?, role? }  Returns: User"""
    data = request.get_json()
    # TODO: user = User.query.get_or_404(user_id)
    #       for k, v in data.items(): setattr(user, k, v)
    #       db.session.commit()
    return jsonify({"id": user_id, **data})


@admin_bp.route("/users/<user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id):
    """Returns: { success }"""
    # TODO: User.query.filter_by(id=user_id).delete(); db.session.commit()
    return jsonify({"success": True})


@admin_bp.route("/users/<user_id>/status", methods=["PATCH"])
@admin_required
def set_user_status(user_id):
    """Body: { status: "Active"|"Suspended"|"Inactive" }  Returns: { id, status }"""
    status = request.get_json().get("status")
    # TODO: user = User.query.get_or_404(user_id); user.status = status; db.session.commit()
    return jsonify({"id": user_id, "status": status})


@admin_bp.route("/users/<user_id>/reset-password", methods=["POST"])
@admin_required
def reset_password(user_id):
    """Body: { new_password }  Returns: { success }"""
    new_pw = request.get_json().get("new_password")
    # TODO: user = User.query.get_or_404(user_id); user.set_password(new_pw); db.session.commit()
    return jsonify({"success": True})


# ── Logs ───────────────────────────────────────────────────────────────────────
@admin_bp.route("/logs", methods=["GET"])
@admin_required
def get_logs():
    """
    Query: user_id, type, limit
    Returns: ActivityLog[]
    TODO: ActivityLog.query.filter(…).order_by(ActivityLog.created_at.desc()).limit(limit).all()
    """
    user_id = request.args.get("user_id")
    log_type= request.args.get("type")
    limit   = int(request.args.get("limit", 50))
    return jsonify([])


# ── Stats ──────────────────────────────────────────────────────────────────────
@admin_bp.route("/stats", methods=["GET"])
@admin_required
def get_stats():
    """
    Query: date_range (7d | 14d | 30d)
    Returns: DashboardStats
    TODO: Aggregate Post counts, sentiment scores, keywords from DB
          filtered by created_at >= now - timedelta(days=N)
    """
    date_range = request.args.get("date_range", "7d")
    return jsonify({
        "totalPosts": 0, "fbPosts": 0, "xPosts": 0,
        "critical": 0, "high": 0, "moderate": 0, "low": 0,
        "topKeywords": [],
        "sentiment": {"negative": 0, "neutral": 0, "positive": 0},
        "trendLabels": [], "trendFb": [], "trendX": [],
        "priorityTrend": {"critical": [], "high": []},
    })


# ── Settings ───────────────────────────────────────────────────────────────────
@admin_bp.route("/settings", methods=["GET"])
@admin_required
def get_settings():
    """
    Returns: { general, security, notifications, system }
    TODO: SystemSettings.query.first() or read from config file / env vars
    """
    return jsonify({
        "general":       {},
        "security":      {},
        "notifications": {},
        "system":        {},
    })


@admin_bp.route("/settings/<section>", methods=["PATCH"])
@admin_required
def update_settings(section):
    """
    Path param: section = general | security | notifications | system
    Body: partial settings dict
    Returns: { success, section, data }
    TODO: validate section, update SystemSettings record, commit
    """
    allowed = {"general", "security", "notifications", "system"}
    if section not in allowed:
        return jsonify({"message": f"Invalid section. Must be one of: {allowed}"}), 400
    data = request.get_json()
    # TODO: settings = SystemSettings.query.first()
    #       for k, v in data.items(): setattr(settings, f"{section}_{k}", v)
    #       db.session.commit()
    return jsonify({"success": True, "section": section, "data": data})
