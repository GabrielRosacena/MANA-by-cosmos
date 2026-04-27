"""
MANA — Posts, watchlist, and dashboard routes backed by SQLite.
"""

from __future__ import annotations

from datetime import timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from data import CLUSTER_DEFINITIONS, now_utc, parse_date_range, top_keywords_from_posts
from models import Post, Watchlist, db

posts_bp = Blueprint("posts", __name__)


def current_username():
    return get_jwt_identity() or "admin_mana"


def apply_post_filters(query):
    source = request.args.get("source")
    cluster_id = request.args.get("cluster_id")
    priority = request.args.get("priority")
    date_range = request.args.get("date_range")

    if source:
        query = query.filter(Post.source == source)
    if cluster_id:
        query = query.filter(Post.cluster_id == cluster_id)
    if priority:
        mapped = "Moderate" if priority == "Medium" else ("Monitoring" if priority == "Low" else priority)
        query = query.filter(Post.priority == mapped)
    if date_range:
        cutoff = now_utc() - parse_date_range(date_range)
        query = query.filter(Post.date >= cutoff)
    return query


@posts_bp.route("/posts", methods=["GET"])
@jwt_required(optional=True)
def get_posts():
    posts = (
        apply_post_filters(Post.query)
        .order_by(Post.date.desc())
        .all()
    )
    return jsonify([post.to_api_dict() for post in posts])


@posts_bp.route("/posts/<post_id>/status", methods=["PATCH"])
@jwt_required(optional=True)
def update_post_status(post_id):
    data = request.get_json() or {}
    post = db.session.get(Post, post_id)
    if not post:
        return jsonify({"message": "Post not found"}), 404

    post.status = data.get("status", post.status)
    db.session.commit()
    return jsonify({"id": post_id, "status": post.status})


@posts_bp.route("/watchlist", methods=["GET"])
@jwt_required(optional=True)
def get_watchlist():
    pinned = (
        Watchlist.query.filter_by(username=current_username())
        .order_by(Watchlist.created_at.desc())
        .all()
    )
    return jsonify({"pinned": [item.post_id for item in pinned]})


@posts_bp.route("/watchlist/<post_id>", methods=["POST"])
@jwt_required(optional=True)
def pin_post(post_id):
    if not db.session.get(Post, post_id):
        return jsonify({"message": "Post not found"}), 404

    username = current_username()
    existing = Watchlist.query.filter_by(username=username, post_id=post_id).first()
    if not existing:
        db.session.add(Watchlist(username=username, post_id=post_id))
        db.session.commit()
    return get_watchlist()


@posts_bp.route("/watchlist/<post_id>", methods=["DELETE"])
@jwt_required(optional=True)
def unpin_post(post_id):
    username = current_username()
    Watchlist.query.filter_by(username=username, post_id=post_id).delete()
    db.session.commit()
    return get_watchlist()


@posts_bp.route("/clusters", methods=["GET"])
@jwt_required(optional=True)
def get_clusters():
    return jsonify(CLUSTER_DEFINITIONS)


@posts_bp.route("/dashboard/summary", methods=["GET"])
@jwt_required(optional=True)
def get_dashboard_summary():
    date_range = request.args.get("date_range", "7d")
    cutoff = now_utc() - parse_date_range(date_range)
    posts = Post.query.filter(Post.date >= cutoff).all()
    total = len(posts)
    fb_posts = sum(1 for post in posts if post.source == "Facebook")
    x_posts = sum(1 for post in posts if post.source == "X")
    critical = sum(1 for post in posts if post.priority == "Critical")
    high = sum(1 for post in posts if post.priority == "High")
    active_clusters = len({post.cluster_id for post in posts})
    cluster_count = max(len(CLUSTER_DEFINITIONS), 1)

    def pct(count):
        return round((count / total) * 100) if total else 0

    label_map = {"24h": "Today", "7d": "Last 7 days", "14d": "Last 14 days", "30d": "Last 30 days"}
    meta = label_map.get(date_range, "Recent")
    kpis = [
        {"label": "Critical Posts %", "value": f"{pct(critical)}%", "meta": meta, "bar": pct(critical)},
        {"label": "High Priority %", "value": f"{pct(high)}%", "meta": meta, "bar": pct(high)},
        {"label": "Total Posts Analyzed", "value": f"{total:,}", "meta": meta, "bar": min(100, max(8, total * 4 if total < 25 else total))},
        {"label": "Total Facebook Posts", "value": f"{fb_posts:,}", "meta": meta, "bar": pct(fb_posts)},
        {"label": "Total X/Twitter Posts", "value": f"{x_posts:,}", "meta": meta, "bar": pct(x_posts)},
        {
            "label": "Active Clusters %",
            "value": f"{round((active_clusters / cluster_count) * 100) if cluster_count else 0}%",
            "meta": "All active",
            "bar": round((active_clusters / cluster_count) * 100) if cluster_count else 0,
        },
    ]
    return jsonify({"kpis": kpis})


@posts_bp.route("/dashboard/keywords", methods=["GET"])
@jwt_required(optional=True)
def get_keywords():
    posts = Post.query.order_by(Post.date.desc()).limit(500).all()
    return jsonify({"keywords": top_keywords_from_posts(posts)})


@posts_bp.route("/settings/email-alerts", methods=["PATCH"])
@jwt_required(optional=True)
def update_email_alerts():
    data = request.get_json() or {}
    enabled = bool(data.get("enabled", True))
    return jsonify({"enabled": enabled})
