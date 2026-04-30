"""
MANA — CorEx Topic Modeling Routes (admin only).

Endpoints:
  POST /api/admin/corex/train          — train CorEx from preprocessed_texts table
  GET  /api/admin/corex/status         — model status, coherence, expanded keywords
  POST /api/admin/corex/predict-all    — run inference on all posts, save to post_topics
  GET  /api/admin/corex/topics/<post_id> — get topic assignments for one post
"""

from __future__ import annotations

from functools import wraps

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, jwt_required

from models import PostTopic, PreprocessedText, db
from services.corex.topic_modeler import (
    get_model_status,
    is_model_trained,
    predict_topics_batch,
    train_corex,
)

corex_bp = Blueprint("corex", __name__)


def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get("role") != "Admin":
            return jsonify({"message": "Admin access required."}), 403
        return fn(*args, **kwargs)
    return wrapper


# ── Train ──────────────────────────────────────────────────────────────────────

@corex_bp.route("/corex/train", methods=["POST"])
@admin_required
def train():
    """
    Read all relevant, finalized preprocessed texts and train the CorEx model.
    Returns expanded keywords, coherence scores, and training metadata.
    """
    rows = (
        PreprocessedText.query
        .filter_by(preprocessing_status="processed", is_relevant=True)
        .filter(PreprocessedText.final_tokens_json != "[]")
        .all()
    )

    # Reconstruct space-joined text from final_tokens — these are the clean,
    # lemmatized, bigram-enriched tokens that CorEx should learn from.
    texts = [" ".join(row.final_tokens) for row in rows if row.final_tokens]

    try:
        result = train_corex(texts)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Training failed: {exc}"}), 500

    return jsonify({
        "message": "CorEx model trained successfully.",
        "corpus_size": result["corpus_size"],
        "trained_at": result["trained_at"],
        "overall_coherence": result["overall_coherence"],
        "coherence_scores": result["coherence_scores"],
        "low_coherence_topics": result["low_coherence_topics"],
        "expanded_keywords": result["expanded_keywords"],
    })


# ── Status ─────────────────────────────────────────────────────────────────────

@corex_bp.route("/corex/status", methods=["GET"])
@admin_required
def status():
    return jsonify(get_model_status())


# ── Predict all ────────────────────────────────────────────────────────────────

@corex_bp.route("/corex/predict-all", methods=["POST"])
@admin_required
def predict_all():
    """
    Run CorEx inference on all relevant preprocessed posts and save results to
    the post_topics table. Existing topic rows for a post are replaced.

    Optional JSON body:
      { "overwrite": true }   — re-run even if topics already exist (default: false)
    """
    if not is_model_trained():
        return jsonify({"error": "Model not trained. Call POST /api/admin/corex/train first."}), 400

    body = request.get_json(silent=True) or {}
    overwrite = bool(body.get("overwrite", False))

    rows = (
        PreprocessedText.query
        .filter_by(record_type="post", preprocessing_status="processed", is_relevant=True)
        .filter(PreprocessedText.final_tokens_json != "[]")
        .all()
    )

    if not rows:
        return jsonify({"message": "No preprocessed posts found.", "processed": 0})

    post_ids = [row.raw_id for row in rows]
    texts = [" ".join(row.final_tokens) for row in rows]

    if not overwrite:
        already_done = {
            pt.post_id
            for pt in PostTopic.query.filter(PostTopic.post_id.in_(post_ids)).all()
        }
        filtered = [(pid, txt) for pid, txt in zip(post_ids, texts) if pid not in already_done]
        if not filtered:
            return jsonify({"message": "All posts already have topic assignments.", "processed": 0})
        post_ids, texts = zip(*filtered)
        post_ids, texts = list(post_ids), list(texts)

    batch_results = predict_topics_batch(texts)

    inserted = updated = skipped = 0
    for post_id, topic_list in zip(post_ids, batch_results):
        if not topic_list:
            skipped += 1
            continue

        if overwrite:
            PostTopic.query.filter_by(post_id=post_id).delete()

        for item in topic_list:
            row = PostTopic(
                post_id=post_id,
                topic_label=item["topic"],
                confidence=item["confidence"],
            )
            db.session.merge(row) if overwrite else db.session.add(row)
            inserted += 1

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": f"Database commit failed: {exc}"}), 500

    return jsonify({
        "message": "Topic inference complete.",
        "posts_processed": len(post_ids),
        "topic_rows_inserted": inserted,
        "posts_skipped_no_topics": skipped,
    })


# ── Topics for one post ────────────────────────────────────────────────────────

@corex_bp.route("/corex/topics/<post_id>", methods=["GET"])
@admin_required
def get_post_topics(post_id: str):
    topics = (
        PostTopic.query
        .filter_by(post_id=post_id)
        .order_by(PostTopic.confidence.desc())
        .all()
    )
    return jsonify({
        "post_id": post_id,
        "topics": [t.to_api_dict() for t in topics],
        "count": len(topics),
    })
