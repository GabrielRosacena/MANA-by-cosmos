"""
MANA — Analytics / Stats Routes
Endpoints:
  GET /api/analytics/sentiment-histogram    ?date_range=14d
  GET /api/analytics/sentiment-trend        ?date_range=14d
  GET /api/analytics/cluster-activity       ?date_range=14d
  GET /api/analytics/priority-distribution  ?date_range=14d
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

stats_bp = Blueprint("stats", __name__)


@stats_bp.route("/analytics/sentiment-histogram", methods=["GET"])
@jwt_required()
def sentiment_histogram():
    """
    Returns: { histogram: [{label: "0-20", value: int, tone: "negative"|"neutral"|"positive"}] }
    """
    date_range = request.args.get("date_range", "14d")
    # TODO: bucket post sentiment scores from DB into 0-20, 21-40, 41-60, 61-80, 81-100
    return jsonify({"histogram": []})


@stats_bp.route("/analytics/sentiment-trend", methods=["GET"])
@jwt_required()
def sentiment_trend():
    """
    Returns: { labels: [str], positive: [int], neutral: [int], negative: [int] }
    """
    date_range = request.args.get("date_range", "14d")
    # TODO: group posts by day/week, count sentiment categories per period
    return jsonify({"labels": [], "positive": [], "neutral": [], "negative": []})


@stats_bp.route("/analytics/cluster-activity", methods=["GET"])
@jwt_required()
def cluster_activity():
    """
    Returns: { clusterActivity: [{label: str, value: int, color: str}] }
    """
    date_range = request.args.get("date_range", "14d")
    # TODO: COUNT posts GROUP BY cluster_id, join cluster color
    return jsonify({"clusterActivity": []})


@stats_bp.route("/analytics/priority-distribution", methods=["GET"])
@jwt_required()
def priority_distribution():
    """
    Returns: { priority: [{label: str, value: int, color: str}] }
    """
    date_range = request.args.get("date_range", "14d")
    # TODO: COUNT posts GROUP BY priority level
    return jsonify({"priority": []})
