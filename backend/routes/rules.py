"""
MANA — Rule-Based Decision Module Routes
Generates LGU recommendations from topic + sentiment. Does NOT affect priority.

Endpoints:
  GET  /api/admin/rules/list          — show all rules
  POST /api/admin/rules/evaluate      — evaluate a single (cluster, neg_pct, post_count) input
  POST /api/admin/rules/evaluate-all  — run engine on every post, writes Post.recommendation
"""

from __future__ import annotations

from collections import defaultdict

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from models import Post, PostSentiment, db
from services.rules.decision_engine import evaluate, list_rules

rules_bp = Blueprint("rules", __name__)


# ── GET /rules/list ───────────────────────────────────────────────────────────

@rules_bp.route("/rules/list", methods=["GET"])
@jwt_required()
def get_rules():
    """Return the full rule set for inspection."""
    return jsonify({"rules": list_rules(), "total": len(list_rules())}), 200


# ── POST /rules/evaluate ──────────────────────────────────────────────────────

@rules_bp.route("/rules/evaluate", methods=["POST"])
@jwt_required()
def evaluate_single():
    """
    Evaluate a single input and return a recommendation.

    Body (JSON):
        cluster_id  : str   — e.g. "cluster-g"
        neg_pct     : float — e.g. 72.5
        post_count  : int   — optional, default 1
    """
    body = request.get_json(silent=True) or {}
    cluster_id = body.get("cluster_id", "").strip()
    neg_pct = body.get("neg_pct", 0)
    post_count = body.get("post_count", 1)

    if not cluster_id:
        return jsonify({"error": "cluster_id is required"}), 400

    result = evaluate(cluster_id, neg_pct, post_count)
    return jsonify(result), 200


# ── POST /rules/evaluate-all ──────────────────────────────────────────────────

@rules_bp.route("/rules/evaluate-all", methods=["POST"])
@jwt_required()
def evaluate_all():
    """
    Run the rule engine on every post and write the recommendation to Post.recommendation.
    Priority (Post.priority / PostPriority) is not touched — that remains with the RF classifier.

    For each post:
    1. Get cluster_id and negative sentiment percentage from PostSentiment.
    2. Count posts in the same cluster for volume context.
    3. Evaluate rules → recommendation.
    4. Write result to Post.recommendation.
    """
    posts = Post.query.all()
    if not posts:
        return jsonify({"message": "No posts found", "evaluated": 0}), 200

    cluster_counts: dict[str, int] = defaultdict(int)
    for p in posts:
        cluster_counts[p.cluster_id or "cluster-a"] += 1

    sentiments = {s.post_id: s for s in PostSentiment.query.all()}

    evaluated = errors = 0

    for post in posts:
        try:
            cluster_id = post.cluster_id or "cluster-a"
            sentiment = sentiments.get(post.id)

            if sentiment:
                neg_pct = round(float(sentiment.negative or 0) * 100, 2)
            else:
                # Fall back to legacy sentiment_score heuristic (range 20–97, higher = more negative).
                score = post.sentiment_score or 50
                neg_pct = round(max(0.0, min(100.0, (score - 20) / 77 * 100)), 2)

            post_count = cluster_counts[cluster_id]
            result = evaluate(cluster_id, neg_pct, post_count)

            post.recommendation = result["recommendation"]
            evaluated += 1

        except Exception:
            errors += 1
            continue

    db.session.commit()

    return jsonify({
        "message": "Recommendations generated successfully",
        "evaluated": evaluated,
        "errors": errors,
    }), 200
