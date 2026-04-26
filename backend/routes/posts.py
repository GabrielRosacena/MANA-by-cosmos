"""
MANA — Posts & Watchlist Routes
Endpoints:
  GET    /api/posts                    Query: date_range, source, cluster_id, priority
  PATCH  /api/posts/<id>/status        Body: { status }
  GET    /api/watchlist
  POST   /api/watchlist/<post_id>
  DELETE /api/watchlist/<post_id>
  GET    /api/clusters
  GET    /api/dashboard/summary        Query: date_range
  GET    /api/dashboard/keywords
  PATCH  /api/settings/email-alerts    Body: { enabled }
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

posts_bp = Blueprint("posts", __name__)

# ── Placeholder data — replace with DB queries ────────────────────────────────

@posts_bp.route("/posts", methods=["GET"])
@jwt_required()
def get_posts():
    """
    Query params:
      date_range  7d | 14d | 30d | 24h | 3d
      source      Facebook | X
      cluster_id  cluster-a … cluster-h
      priority    Critical | High | Moderate
    Returns: Post[]
    """
    date_range = request.args.get("date_range", "7d")
    source     = request.args.get("source")
    cluster_id = request.args.get("cluster_id")
    priority   = request.args.get("priority")

    # TODO: query DB with filters, e.g.:
    #   posts = Post.query.filter_by(cluster_id=cluster_id).all()
    return jsonify([])   # <- replace with real data


@posts_bp.route("/posts/<post_id>/status", methods=["PATCH"])
@jwt_required()
def update_post_status(post_id):
    """Body: { status }  Returns: { id, status }"""
    data   = request.get_json()
    status = data.get("status")
    # TODO: Post.query.get(post_id).status = status; db.session.commit()
    return jsonify({"id": post_id, "status": status})


@posts_bp.route("/watchlist", methods=["GET"])
@jwt_required()
def get_watchlist():
    """Returns: { pinned: [post_id, ...] }"""
    user = get_jwt_identity()
    # TODO: return Watchlist.query.filter_by(user=user).first().pinned_ids
    return jsonify({"pinned": []})


@posts_bp.route("/watchlist/<post_id>", methods=["POST"])
@jwt_required()
def pin_post(post_id):
    """Returns: { pinned: [post_id, ...] }"""
    # TODO: add post_id to user's watchlist in DB
    return jsonify({"pinned": [post_id]})


@posts_bp.route("/watchlist/<post_id>", methods=["DELETE"])
@jwt_required()
def unpin_post(post_id):
    """Returns: { pinned: [post_id, ...] }"""
    # TODO: remove post_id from user's watchlist in DB
    return jsonify({"pinned": []})


@posts_bp.route("/clusters", methods=["GET"])
@jwt_required()
def get_clusters():
    """Returns: Cluster[]"""
    # TODO: return Cluster.query.all()
    return jsonify([])


@posts_bp.route("/dashboard/summary", methods=["GET"])
@jwt_required()
def get_dashboard_summary():
    """
    Query: date_range
    Returns: { kpis: [{label, value, meta, bar}] }
    """
    date_range = request.args.get("date_range", "7d")
    # TODO: compute real KPIs from DB aggregations
    return jsonify({"kpis": []})


@posts_bp.route("/dashboard/keywords", methods=["GET"])
@jwt_required()
def get_keywords():
    """Returns: { keywords: [{keyword, note, count}] }"""
    # TODO: return top trending keywords from DB
    return jsonify({"keywords": []})


@posts_bp.route("/settings/email-alerts", methods=["PATCH"])
@jwt_required()
def update_email_alerts():
    """Body: { enabled: bool }  Returns: { enabled }"""
    data    = request.get_json()
    enabled = data.get("enabled", True)
    # TODO: update user preference in DB
    return jsonify({"enabled": enabled})
