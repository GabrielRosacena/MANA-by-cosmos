"""
VADER Sentiment Analyzer — Stage 5 of the MANA ML pipeline.

Classifies preprocessed post text into sentiment scores and labels.
Uses VADER (Valence Aware Dictionary and sEntiment Reasoner) — no training required.

Responsibilities:
- analyze_sentiment: raw VADER compound/pos/neg/neu + label for a text
- compound_to_score: maps VADER compound (-1..+1) → legacy distress int (0-100)
- check_sarcasm_incongruence: positive compound + inherently negative cluster → flag
- check_thread_deviation: comment deviates from thread mean by > 1.5 std → flag
- analyze_post: high-level helper combining sentiment + sarcasm, used by routes and import
- get_status: introspection helper for /vader/status endpoint
"""

from __future__ import annotations

import numpy as np
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# ── Singleton (VADER lexicon loaded once at import time) ──────────────────────
_analyzer = SentimentIntensityAnalyzer()

# MANA cluster IDs that represent inherently negative disaster contexts.
# Maps to thesis NEGATIVE_TOPICS = {flood, rescue, infrastructure_damage, ...}
# using MANA's cluster-ID vocabulary instead of CorEx topic names.
NEGATIVE_CLUSTERS = {
    "cluster-d",   # Logistics — blocked roads/bridges are objectively negative
    "cluster-e",   # Telecom/Power — outages are objectively negative
    "cluster-h",   # MDM — no genuinely positive news about death/missing
}

# ── Core functions ─────────────────────────────────────────────────────────────

def analyze_sentiment(text: str) -> dict:
    """
    Run VADER on text. Returns compound, positive, negative, neutral, and label.
    Thresholds (per thesis spec):
        compound >= 0.05  → Positive
        compound <= -0.05 → Negative
        else              → Neutral
    """
    s = _analyzer.polarity_scores(text or "")
    c = s["compound"]
    return {
        "compound": round(c, 4),
        "positive": round(s["pos"], 4),
        "negative": round(s["neg"], 4),
        "neutral":  round(s["neu"], 4),
        "label":    "Positive" if c >= 0.05 else ("Negative" if c <= -0.05 else "Neutral"),
    }


def compound_to_score(compound: float) -> int:
    """
    Map VADER compound (-1..+1) to the legacy distress scale (int 0-100) used by
    Post.sentiment_score and score_tone() in data.py.

    Formula: max(20, min(round(60 - compound * 40), 97))

    Alignment with score_tone() thresholds:
        compound = +1.0  →  score = 20  →  "positive"  (score < 60)
        compound =  0.0  →  score = 60  →  "neutral"   (60 <= score < 80)
        compound = -0.5  →  score = 80  →  "negative"  (score >= 80)
        compound = -1.0  →  score = 97  →  "negative"  (clamped at 97)
    """
    return max(20, min(round(60 - compound * 40), 97))


def check_sarcasm_incongruence(compound: float, cluster_id: str | None) -> bool:
    """
    Thesis sarcasm rule 1: positive sentiment in an inherently negative disaster cluster.
    Returns True when compound >= 0.05 AND cluster_id is one of the negative clusters.
    """
    return compound >= 0.05 and cluster_id in NEGATIVE_CLUSTERS


def check_thread_deviation(
    comment_compound: float,
    thread_compounds: list[float],
    threshold: float = 1.5,
) -> bool:
    """
    Thesis sarcasm rule 2: comment deviates from the thread's mean compound by
    more than `threshold` standard deviations.

    Returns False when fewer than 3 thread compounds are available (insufficient data).
    """
    if len(thread_compounds) < 3:
        return False
    std = float(np.std(thread_compounds))
    if std == 0:
        return False
    return abs(comment_compound - float(np.mean(thread_compounds))) / std > threshold


_SARCASM_PHRASES = frozenset({
    "oh great", "oh wow", "how wonderful", "how amazing", "how nice",
    "how fantastic", "how lovely", "how convenient", "how helpful",
    "yeah right", "of course it is", "oh perfect", "just perfect",
    "absolutely perfect", "so great", "so wonderful", "so amazing",
    "how great", "how perfect", "how nice of",
})


def _check_sarcasm_phrases(text: str) -> bool:
    """Thesis sarcasm rule 3: exclamatory positive phrases in disaster context."""
    lowered = (text or "").lower()
    return any(phrase in lowered for phrase in _SARCASM_PHRASES)


def analyze_post(
    text: str,
    cluster_id: str | None,
    thread_compounds: list[float] | None = None,
) -> dict:
    """
    High-level helper combining analyze_sentiment + all three sarcasm rules.

    Returns a dict ready to be stored in PostSentiment and used to update
    Post.sentiment_score and Post.sentiment_compound.

    Keys: compound, positive, negative, neutral, label,
          sentiment_score (int 0-100), sarcasm_flag (bool)

    thread_compounds: sibling comment compounds for Rule 2 (thread deviation).
    Omit or pass None for posts (Rule 2 fires only with ≥ 3 data points).
    """
    result = analyze_sentiment(text)
    result["sentiment_score"] = compound_to_score(result["compound"])
    result["sarcasm_flag"] = (
        check_sarcasm_incongruence(result["compound"], cluster_id)
        or check_thread_deviation(result["compound"], thread_compounds or [])
        or _check_sarcasm_phrases(text)
    )
    return result


def get_status() -> dict:
    """Introspection helper for the /vader/status endpoint."""
    try:
        _analyzer.polarity_scores("test")
        available = True
    except Exception:
        available = False
    return {
        "available": available,
        "negative_clusters": sorted(NEGATIVE_CLUSTERS),
        "compound_thresholds": {"positive": 0.05, "negative": -0.05},
        "thread_deviation_threshold": 1.5,
        "score_formula": "max(20, min(round(60 - compound * 40), 97))",
    }
