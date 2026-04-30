"""
MANA — Linear SVM Cluster Classification Routes (admin only).

Endpoints:
  POST /api/admin/svm/train            — train SVM from preprocessed_texts + Post labels
  GET  /api/admin/svm/status           — model status, F1 scores, per-class report
  POST /api/admin/svm/predict-all      — run inference on all posts, save to post_clusters
  GET  /api/admin/svm/clusters/<post_id> — get cluster assignments for one post
"""

from __future__ import annotations

from functools import wraps

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, jwt_required

from models import Post, PostCluster, PreprocessedText, db
from services.svm.cluster_classifier import (
    get_model_status,
    is_model_trained,
    predict_clusters_batch,
    train_svm,
)

svm_bp = Blueprint("svm", __name__)


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

@svm_bp.route("/svm/train", methods=["POST"])
@admin_required
def train():
    """
    Join PreprocessedText with Post to get (text, cluster_label) pairs, then
    train the LinearSVC OvR classifier. Post.cluster_id provides the training
    labels (bootstrapped from the keyword heuristic in data.py).
    """
    rows = (
        db.session.query(PreprocessedText, Post)
        .join(Post, PreprocessedText.raw_id == Post.id)
        .filter(
            PreprocessedText.preprocessing_status == "processed",
            PreprocessedText.is_relevant == True,
            PreprocessedText.final_tokens_json != "[]",
            PreprocessedText.record_type == "post",
        )
        .all()
    )

    if not rows:
        return jsonify({"error": "No preprocessed posts found. Import data first."}), 400

    texts = [" ".join(pt.final_tokens) for pt, post in rows]
    # Wrap single cluster_id in a list for MultiLabelBinarizer compatibility
    labels = [[post.cluster_id] for pt, post in rows]

    try:
        result = train_svm(texts, labels)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Training failed: {exc}"}), 500

    return jsonify({
        "message": "SVM model trained successfully.",
        "corpus_size": result["corpus_size"],
        "best_C": result["best_C"],
        "f1_macro": result["f1_macro"],
        "trained_at": result["trained_at"],
        "per_class_report": result["per_class_report"],
    })


# ── Status ─────────────────────────────────────────────────────────────────────

@svm_bp.route("/svm/status", methods=["GET"])
@admin_required
def status():
    return jsonify(get_model_status())


# ── Predict all ────────────────────────────────────────────────────────────────

@svm_bp.route("/svm/predict-all", methods=["POST"])
@admin_required
def predict_all():
    """
    Run SVM inference on all relevant preprocessed posts, save multi-label
    cluster assignments to post_clusters, and update Post.cluster_id with
    the top-confidence SVM prediction (replacing the heuristic assignment).

    Optional JSON body:
      { "overwrite": true }  — re-run even if clusters already exist (default: false)
    """
    if not is_model_trained():
        return jsonify({"error": "Model not trained. Call POST /api/admin/svm/train first."}), 400

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
            pc.post_id
            for pc in PostCluster.query.filter(PostCluster.post_id.in_(post_ids)).all()
        }
        filtered = [(pid, txt) for pid, txt in zip(post_ids, texts) if pid not in already_done]
        if not filtered:
            return jsonify({"message": "All posts already have cluster assignments.", "processed": 0})
        post_ids, texts = zip(*filtered)
        post_ids, texts = list(post_ids), list(texts)

    batch_results = predict_clusters_batch(texts)

    inserted = skipped = cluster_updates = 0
    for post_id, cluster_list in zip(post_ids, batch_results):
        if not cluster_list:
            skipped += 1
            continue

        if overwrite:
            PostCluster.query.filter_by(post_id=post_id).delete()

        for item in cluster_list:
            existing = PostCluster.query.filter_by(
                post_id=post_id, cluster_id=item["cluster_id"]
            ).first()
            if existing:
                existing.confidence = item["confidence"]
            else:
                db.session.add(PostCluster(
                    post_id=post_id,
                    cluster_id=item["cluster_id"],
                    confidence=item["confidence"],
                ))
            inserted += 1

        # Update Post.cluster_id with the SVM's top-confidence cluster
        top_cluster = cluster_list[0]["cluster_id"]
        post = db.session.get(Post, post_id)
        if post and post.cluster_id != top_cluster:
            post.cluster_id = top_cluster
            cluster_updates += 1

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": f"Database commit failed: {exc}"}), 500

    return jsonify({
        "message": "SVM cluster inference complete.",
        "posts_processed": len(post_ids),
        "cluster_rows_inserted": inserted,
        "post_cluster_id_updated": cluster_updates,
        "posts_skipped_no_clusters": skipped,
    })


# ── Clusters for one post ──────────────────────────────────────────────────────

@svm_bp.route("/svm/clusters/<post_id>", methods=["GET"])
@admin_required
def get_post_clusters(post_id: str):
    clusters = (
        PostCluster.query
        .filter_by(post_id=post_id)
        .order_by(PostCluster.confidence.desc())
        .all()
    )
    return jsonify({
        "post_id": post_id,
        "clusters": [c.to_api_dict() for c in clusters],
        "count": len(clusters),
    })
