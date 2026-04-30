"""
CorEx (Anchored Correlation Explanation) Topic Modeler — Stage 3 of the MANA ML pipeline.

Responsibilities:
- train_corex: trains on preprocessed text corpus, saves model files to backend/models/
- predict_topics: returns topic assignments + confidence scores for a single text
- predict_topics_batch: same for many texts at once
- is_model_trained / get_model_status: introspection helpers for routes
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import joblib
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer

import corextopic.corextopic as ct

# ── Constants ─────────────────────────────────────────────────────────────────

TOPIC_LABELS = [
    "flood",
    "evacuation",
    "rescue",
    "infrastructure_damage",
    "relief",
    "power_outage",
    "health_medical",
    "communication",
]

# Anchor words aligned with NDRRMC disaster response clusters.
# Each list seeds the corresponding CorEx topic — CorEx will then expand
# these based on co-occurrence patterns in the actual corpus.
ANCHOR_WORDS: dict[str, list[str]] = {
    "flood": [
        "flood", "baha", "tubig", "inundation", "flash flood",
        "water level", "overflow", "flooded", "flooding",
    ],
    "evacuation": [
        "evacuation", "evacuate", "shelter", "likas", "evacuation center",
        "displaced", "evacuees", "camp",
    ],
    "rescue": [
        "rescue", "trapped", "stranded", "sagipin", "search and rescue",
        "sos", "roof", "retrieval", "rescue boat",
    ],
    "infrastructure_damage": [
        "damage", "collapsed", "road", "bridge", "landslide", "guho",
        "blocked", "debris", "infrastructure",
    ],
    "relief": [
        "relief", "ayuda", "goods", "donation", "food pack",
        "supply", "distribution", "relief goods", "rice",
    ],
    "power_outage": [
        "blackout", "kuryente", "power outage", "electricity",
        "walang kuryente", "brownout", "no power",
    ],
    "health_medical": [
        "hospital", "injured", "medical", "health", "sick",
        "ospital", "medicine", "doctor", "patient",
    ],
    "communication": [
        "signal", "network", "communication", "internet",
        "no signal", "cell site", "connectivity", "telecom",
    ],
}

N_TOPICS = len(TOPIC_LABELS)
MIN_CORPUS_SIZE = 10
ANCHOR_STRENGTH = 3
MAX_FEATURES = 5000

_MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "models")
_COREX_MODEL_PATH = os.path.join(_MODEL_DIR, "corex_model.pkl")
_VECTORIZER_PATH = os.path.join(_MODEL_DIR, "corex_vectorizer.pkl")
_KEYWORDS_PATH = os.path.join(_MODEL_DIR, "corex_keywords.json")
_META_PATH = os.path.join(_MODEL_DIR, "corex_meta.json")


# ── Training ──────────────────────────────────────────────────────────────────

def train_corex(texts: list[str]) -> dict:
    """
    Train Anchored CorEx on a corpus of preprocessed texts.

    Returns a summary dict with expanded keywords, coherence scores, and
    training metadata. Saves four files to backend/models/:
      corex_model.pkl, corex_vectorizer.pkl, corex_keywords.json, corex_meta.json

    Raises ValueError if the corpus is too small to train on.
    """
    relevant = [t for t in texts if t and t.strip()]
    if len(relevant) < MIN_CORPUS_SIZE:
        raise ValueError(
            f"Corpus too small: {len(relevant)} documents. "
            f"Need at least {MIN_CORPUS_SIZE} preprocessed posts to train CorEx."
        )

    vectorizer = CountVectorizer(
        max_features=MAX_FEATURES,
        binary=True,
        ngram_range=(1, 2),
    )
    doc_term_matrix = vectorizer.fit_transform(relevant)
    vocab = list(vectorizer.get_feature_names_out())
    vocab_set = set(vocab)

    # Build anchor index lists — skip words not in vocab (small corpus may lack them)
    anchor_indices = []
    for topic_words in ANCHOR_WORDS.values():
        indices = [vocab.index(w) for w in topic_words if w in vocab_set]
        anchor_indices.append(indices)

    # words must be passed to fit(), not to the constructor (corextopic 1.1 API)
    model = ct.Corex(n_hidden=N_TOPICS, seed=42)
    model.fit(doc_term_matrix, words=vocab, anchors=anchor_indices, anchor_strength=ANCHOR_STRENGTH)

    # Expand keywords: top-20 positively associated words per topic
    expanded_keywords: dict[str, list[str]] = {}
    for i, label in enumerate(TOPIC_LABELS):
        top_words = model.get_topics(topic=i, n_words=20)
        expanded_keywords[label] = [w for w, _mi, sign in top_words if sign == 1]

    coherence_scores = {
        label: float(score)
        for label, score in zip(TOPIC_LABELS, model.tcs)
    }
    low_coherence = [label for label, score in coherence_scores.items() if score < 0.30]

    os.makedirs(_MODEL_DIR, exist_ok=True)
    joblib.dump(model, _COREX_MODEL_PATH)
    joblib.dump(vectorizer, _VECTORIZER_PATH)
    with open(_KEYWORDS_PATH, "w", encoding="utf-8") as f:
        json.dump(expanded_keywords, f, indent=2)

    meta = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "corpus_size": len(relevant),
        "n_topics": N_TOPICS,
        "anchor_strength": ANCHOR_STRENGTH,
        "max_features": MAX_FEATURES,
        "coherence_scores": coherence_scores,
        "overall_coherence": float(np.mean(list(coherence_scores.values()))),
        "low_coherence_topics": low_coherence,
    }
    with open(_META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    return {
        "corpus_size": len(relevant),
        "expanded_keywords": expanded_keywords,
        "coherence_scores": coherence_scores,
        "overall_coherence": meta["overall_coherence"],
        "low_coherence_topics": low_coherence,
        "trained_at": meta["trained_at"],
    }


# ── Inference ─────────────────────────────────────────────────────────────────

def _load_model():
    if not is_model_trained():
        raise RuntimeError(
            "CorEx model is not trained yet. "
            "Call POST /api/admin/corex/train first."
        )
    model = joblib.load(_COREX_MODEL_PATH)
    vectorizer = joblib.load(_VECTORIZER_PATH)
    return model, vectorizer


def predict_topics(text: str) -> list[dict]:
    """
    Return topic assignments for a single preprocessed text.

    Returns a list of dicts for topics the model considers active (p > 0.5):
      [{"topic": "flood", "confidence": 0.87}, ...]

    Returns an empty list if no topics are detected.
    """
    model, vectorizer = _load_model()
    doc_term = vectorizer.transform([text or ""])

    # corextopic 1.1: use transform() which returns p_y_given_x (posterior probs, not log-probs)
    probs = model.transform(doc_term)[0]  # shape: (n_topics,), values in [0, 1]

    results = []
    for label, prob in zip(TOPIC_LABELS, probs):
        if prob > 0.5:
            results.append({"topic": label, "confidence": round(float(prob), 4)})

    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results


def predict_topics_batch(texts: list[str]) -> list[list[dict]]:
    """
    Return topic assignments for a list of preprocessed texts.

    Returns a list of lists — one inner list per input text.
    """
    if not texts:
        return []

    model, vectorizer = _load_model()
    cleaned = [t or "" for t in texts]
    doc_term = vectorizer.transform(cleaned)

    # corextopic 1.1: transform() returns p_y_given_x, shape (n_docs, n_topics)
    probs = model.transform(doc_term)  # shape: (n_docs, n_topics)

    all_results = []
    for doc_probs in probs:
        doc_topics = []
        for label, prob in zip(TOPIC_LABELS, doc_probs):
            if prob > 0.5:
                doc_topics.append({"topic": label, "confidence": round(float(prob), 4)})
        doc_topics.sort(key=lambda x: x["confidence"], reverse=True)
        all_results.append(doc_topics)

    return all_results


# ── Status helpers ────────────────────────────────────────────────────────────

def is_model_trained() -> bool:
    return os.path.exists(_COREX_MODEL_PATH) and os.path.exists(_VECTORIZER_PATH)


def get_model_status() -> dict:
    if not is_model_trained():
        return {"trained": False}

    meta: dict = {}
    if os.path.exists(_META_PATH):
        with open(_META_PATH, encoding="utf-8") as f:
            meta = json.load(f)

    keywords: dict = {}
    if os.path.exists(_KEYWORDS_PATH):
        with open(_KEYWORDS_PATH, encoding="utf-8") as f:
            keywords = json.load(f)

    return {
        "trained": True,
        "trained_at": meta.get("trained_at"),
        "corpus_size": meta.get("corpus_size"),
        "n_topics": meta.get("n_topics", N_TOPICS),
        "overall_coherence": meta.get("overall_coherence"),
        "coherence_scores": meta.get("coherence_scores", {}),
        "low_coherence_topics": meta.get("low_coherence_topics", []),
        "topic_labels": TOPIC_LABELS,
        "expanded_keywords": keywords,
    }
