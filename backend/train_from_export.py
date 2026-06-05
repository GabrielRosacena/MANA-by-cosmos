"""
Train all models (CorEx, SVM, RF) from a live DB export CSV.

Handles the db-export format which has:
  - caption          : raw post text
  - cluster_id       : heuristic cluster label (cluster-a..h)
  - priority         : Low / Medium / Moderate / High / Critical
  - engagement cols  : reactions, shares, likes, reposts, comments

Steps:
  1. Preprocess captions
  2. Auto-label missing cluster/priority via keyword heuristic
  3. Train CorEx (unsupervised, all 861 texts)
  4. Train SVM  (cluster_id labels)
  5. Train RF   (normalized priority labels)

Usage:
    cd backend
    python train_from_export.py --csv /path/to/posts_rows.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np

_BACKEND = Path(__file__).parent
sys.path.insert(0, str(_BACKEND))

from preprocessing import preprocess_record
from services.corex.topic_modeler import train_corex
from services.svm.cluster_classifier import train_svm, CLUSTER_LABELS
from services.random_forest.priority_classifier import (
    DEFAULT_FEATURE_COLUMNS,
    DISASTER_TERMS,
    PRIORITY_LABELS,
    RF_COLUMNS_PATH,
    RF_META_PATH,
    RF_MODEL_PATH,
    SENTIMENT_ENCODE,
    _TOPIC_NAMES,
)
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split

# ── Label mappings ────────────────────────────────────────────────────────────

PRIORITY_NORM = {
    "High":     "High",
    "Critical": "High",
    "Medium":   "Medium",
    "Moderate": "Medium",
    "Low":      "Low",
}

CLUSTER_TO_TOPIC = {
    "cluster-a": "relief",
    "cluster-b": "health_medical",
    "cluster-c": "evacuation",
    "cluster-d": "logistics",
    "cluster-e": "telecom_power",
    "cluster-f": "education",
    "cluster-g": "rescue",
    "cluster-h": "dead_missing",
}

# Keyword rules for auto-labeling posts whose cluster_id is null/unknown
CLUSTER_KEYWORDS = {
    "cluster-g": ["rescue", "fire", "firefighter", "bfp", "trapped", "retrieved", "search", "retrieval"],
    "cluster-c": ["evacuat", "shelter", "displaced", "evacuee", "camp", "tent"],
    "cluster-b": ["medical", "hospital", "health", "injury", "patient", "cholera", "dengue", "leptospirosis", "wash"],
    "cluster-e": ["power", "electric", "meralco", "signal", "telecom", "communication", "outage", "internet"],
    "cluster-d": ["logistics", "supply", "relief goods", "distribution", "truck", "warehouse"],
    "cluster-h": ["missing", "dead", "fatality", "casualties", "death", "body"],
    "cluster-f": ["school", "class", "deped", "student", "education", "teacher"],
    "cluster-a": ["food", "relief", "nfi", "assistance", "aid", "water", "non-food"],
}

PRIORITY_KEYWORDS = {
    "High":   ["urgent", "emergency", "critical", "danger", "fatality", "death", "rescue", "trapped", "missing"],
    "Medium": ["warning", "alert", "flooding", "evacuate", "advisory", "threat", "hazard"],
    "Low":    ["forecast", "update", "monitor", "information", "weather", "info", "advisory"],
}


def _auto_label_cluster(text: str) -> str:
    t = text.lower()
    for cluster, kws in CLUSTER_KEYWORDS.items():
        if any(k in t for k in kws):
            return cluster
    return "cluster-a"  # default: relief/general


def _auto_label_priority(text: str, reactions: float, shares: float, comments: float) -> str:
    t = text.lower()
    engagement = reactions + shares * 3 + comments * 2
    if any(k in t for k in PRIORITY_KEYWORDS["High"]) or engagement > 500:
        return "High"
    if any(k in t for k in PRIORITY_KEYWORDS["Medium"]) or engagement > 100:
        return "Medium"
    return "Low"


# ── Load CSV ──────────────────────────────────────────────────────────────────

def load_csv(path: str) -> list[dict]:
    import csv
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    print(f"[CSV] Loaded {len(rows)} rows from {path}")
    return rows


# ── Preprocess ────────────────────────────────────────────────────────────────

def preprocess_rows(rows: list[dict]) -> list[dict]:
    try:
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source="auto", target="en")
    except Exception:
        translator = None
        print("[WARN] deep_translator unavailable — translation skipped.")

    skipped = 0
    for row in rows:
        caption = (row.get("caption") or "").strip()
        result = preprocess_record(
            raw_id=row.get("id", ""),
            item={"caption": caption, "text": caption},
            record_type="post",
            translator=translator,
        )
        row["_preprocess"] = result
        if result["preprocessing_status"] != "processed" or not result["final_tokens"]:
            skipped += 1

    print(f"[Preprocess] {len(rows) - skipped} processed, {skipped} skipped")
    return rows


# ── VADER ─────────────────────────────────────────────────────────────────────

def compute_vader(rows: list[dict]) -> list[dict]:
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        vader = SentimentIntensityAnalyzer()
    except ImportError:
        vader = None
        print("[WARN] vaderSentiment unavailable — falling back to CSV compound.")

    for row in rows:
        pre = row["_preprocess"]
        text = pre.get("vader_text") or pre.get("clean_text") or row.get("caption") or ""
        if vader:
            s = vader.polarity_scores(text)
            row["_vader"] = {"compound": s["compound"], "positive": s["pos"],
                             "negative": s["neg"], "neutral": s["neu"]}
        else:
            compound = float(row.get("sentiment_compound") or 0.0)
            abs_c = abs(compound)
            if compound >= 0.05:
                row["_vader"] = {"compound": compound, "positive": abs_c, "negative": 0.0, "neutral": 1.0 - abs_c}
            elif compound <= -0.05:
                row["_vader"] = {"compound": compound, "positive": 0.0, "negative": abs_c, "neutral": 1.0 - abs_c}
            else:
                row["_vader"] = {"compound": compound, "positive": 0.0, "negative": 0.0, "neutral": 1.0}
    return rows


# ── Auto-label ────────────────────────────────────────────────────────────────

def apply_labels(rows: list[dict]) -> list[dict]:
    cluster_auto = priority_auto = 0
    for row in rows:
        caption = (row.get("caption") or "").strip()

        # Cluster
        raw_cluster = (row.get("cluster_id") or "").strip().lower()
        if raw_cluster in CLUSTER_LABELS:
            row["_cluster"] = raw_cluster
        else:
            row["_cluster"] = _auto_label_cluster(caption)
            cluster_auto += 1

        # Priority
        raw_priority = (row.get("priority") or "").strip()
        norm = PRIORITY_NORM.get(raw_priority)
        if norm:
            row["_priority"] = norm
        else:
            r = float(row.get("reactions") or 0)
            s = float(row.get("shares") or 0)
            c = float(row.get("comments") or 0)
            row["_priority"] = _auto_label_priority(caption, r, s, c)
            priority_auto += 1

    print(f"[Labels] Auto-labeled clusters: {cluster_auto}, priorities: {priority_auto}")
    return rows


# ── CorEx ─────────────────────────────────────────────────────────────────────

def run_corex(rows: list[dict]) -> dict:
    texts = []
    for row in rows:
        pre = row["_preprocess"]
        tokens = pre.get("final_tokens") or []
        text = " ".join(tokens)
        if text.strip():
            texts.append(text)

    print(f"\n[CorEx] Training on {len(texts)} preprocessed texts ...")
    result = train_corex(texts)
    print(f"[CorEx] Done — overall_coherence={result['overall_coherence']:.4f}")
    print("        Per-topic coherence:")
    for topic, score in result["coherence_scores"].items():
        flag = " ⚠ LOW" if score < 2.5 else ""
        print(f"          {topic}: {score:.3f}{flag}")
    return result


# ── SVM ───────────────────────────────────────────────────────────────────────

def run_svm(rows: list[dict]) -> dict:
    texts, labels = [], []
    for row in rows:
        pre = row["_preprocess"]
        tokens = pre.get("final_tokens") or []
        text = " ".join(tokens)
        if not text.strip():
            continue
        texts.append(text)
        labels.append([row["_cluster"]])

    print(f"\n[SVM] Training on {len(texts)} posts")
    dist = Counter(l[0] for l in labels)
    print("      Cluster distribution:")
    for k in CLUSTER_LABELS:
        print(f"        {k}: {dist.get(k, 0)}")

    result = train_svm(texts, labels)
    print(f"[SVM] Done — f1_macro={result['f1_macro']:.4f}, best_C={result['best_C']}")
    print("      Per-cluster metrics:")
    for lbl, m in result.get("per_class_report", {}).items():
        print(f"        {lbl}: P={m['precision']:.3f} R={m['recall']:.3f} F1={m['f1']:.3f} (n={m['support']})")
    return result


# ── RF ────────────────────────────────────────────────────────────────────────

def run_rf(rows: list[dict]) -> dict:
    valid = [r for r in rows if r.get("_priority") in PRIORITY_LABELS]

    eng_raw = np.array([
        float(r.get("reactions") or 0) + float(r.get("comments") or 0)
        + float(r.get("shares") or 0) + float(r.get("reposts") or 0)
        for r in valid
    ], dtype=float)

    q25 = float(np.quantile(eng_raw, 0.25))
    q75 = float(np.quantile(eng_raw, 0.75))
    if q25 == q75:
        eng_levels = np.ones(len(valid))
    else:
        eng_levels = np.where(eng_raw > q75, 2.0, np.where(eng_raw <= q25, 0.0, 1.0))

    topic_counter: Counter = Counter()
    for r in valid:
        t = CLUSTER_TO_TOPIC.get(r["_cluster"])
        if t:
            topic_counter[t] += 1
    batch_total = max(len(valid), 1)

    X_rows, y_labels = [], []
    for i, row in enumerate(valid):
        v = row["_vader"]
        compound = float(v["compound"])
        positive = float(v["positive"])
        negative = float(v["negative"])
        neutral  = float(v["neutral"])

        sent_label = "Positive" if compound >= 0.05 else "Negative" if compound <= -0.05 else "Neutral"
        sent_enc = float(SENTIMENT_ENCODE.get(sent_label, 1))

        reactions = float(row.get("reactions") or 0)
        comments  = float(row.get("comments")  or 0)
        shares    = float(row.get("shares")    or 0)
        reposts   = float(row.get("reposts")   or 0)

        pre = row["_preprocess"]
        clean = (pre.get("clean_text") or row.get("caption") or "").lower()
        keyword_intensity = float(sum(1 for term in DISASTER_TERMS if term in clean))

        topic_label = CLUSTER_TO_TOPIC.get(row["_cluster"])
        topic_list  = [topic_label] if topic_label else []
        recurrence  = (
            sum(topic_counter[t] / batch_total for t in topic_list) / len(topic_list)
            if topic_list else 0.0
        )
        topic_set = set(topic_list)
        topic_one_hot = [float(name in topic_set) for name in _TOPIC_NAMES]

        X_rows.append([
            compound, positive, negative, neutral, sent_enc,
            reactions, comments, shares, reposts,
            eng_raw[i], eng_levels[i],
            keyword_intensity, recurrence,
        ] + topic_one_hot)
        y_labels.append(row["_priority"])

    X = np.array(X_rows, dtype=float)
    y = np.array(y_labels)

    print(f"\n[RF] Training on {len(y)} posts")
    dist = Counter(y)
    print("     Priority distribution:")
    for k in PRIORITY_LABELS:
        print(f"       {k}: {dist.get(k, 0)}")

    unique, counts = np.unique(y, return_counts=True)
    can_stratify = len(unique) > 1 and all(c >= 2 for c in counts)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42,
        stratify=(y if can_stratify else None),
    )

    clf = RandomForestClassifier(n_estimators=100, class_weight="balanced",
                                  random_state=42, n_jobs=-1)
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)

    accuracy  = float(accuracy_score(y_test, y_pred))
    report    = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    prec, rec, f1, _ = precision_recall_fscore_support(y_test, y_pred, average="weighted", zero_division=0)
    labels_in = [l for l in PRIORITY_LABELS if l in set(y_test) or l in set(y_pred)]
    matrix    = confusion_matrix(y_test, y_pred, labels=labels_in)

    joblib.dump(clf, RF_MODEL_PATH)
    RF_COLUMNS_PATH.write_text(json.dumps(DEFAULT_FEATURE_COLUMNS))

    class_dist = {lbl: int(np.sum(y == lbl)) for lbl in PRIORITY_LABELS}
    meta = {
        "trained_at":       datetime.now(timezone.utc).isoformat(),
        "corpus_size":      int(len(y)),
        "n_estimators":     100,
        "accuracy":         round(accuracy, 4),
        "precision":        round(float(prec), 4),
        "recall":           round(float(rec), 4),
        "f1_score":         round(float(f1), 4),
        "confusion_matrix": {"labels": labels_in, "values": matrix.tolist()},
        "class_distribution": class_dist,
        "feature_columns":  DEFAULT_FEATURE_COLUMNS,
        "source":           "train_from_export.py",
    }
    RF_META_PATH.write_text(json.dumps(meta, indent=2))

    print(f"[RF] Done — accuracy={accuracy:.4f}")
    print(f"     Weighted: P={float(prec):.4f} R={float(rec):.4f} F1={float(f1):.4f}")
    print("     Confusion matrix:")
    print(f"       labels: {labels_in}")
    for row_ in matrix.tolist():
        print(f"       {row_}")
    print("     Per-class:")
    for lbl in PRIORITY_LABELS:
        m = report.get(lbl, {})
        print(f"       {lbl}: P={m.get('precision',0):.3f} R={m.get('recall',0):.3f} F1={m.get('f1-score',0):.3f} (n={int(m.get('support',0))})")
    return {**meta, "report": report}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--skip-corex", action="store_true")
    parser.add_argument("--skip-svm",   action="store_true")
    parser.add_argument("--skip-rf",    action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print("MANA — Export-based model training")
    print("=" * 60)

    rows = load_csv(args.csv)
    rows = preprocess_rows(rows)
    rows = compute_vader(rows)
    rows = apply_labels(rows)

    corex_result = svm_result = rf_result = None

    if not args.skip_corex:
        corex_result = run_corex(rows)
    if not args.skip_svm:
        svm_result = run_svm(rows)
    if not args.skip_rf:
        rf_result = run_rf(rows)

    print("\n" + "=" * 60)
    print("Training complete. Model files saved to backend/models/")
    if corex_result:
        print(f"  CorEx coherence : {corex_result['overall_coherence']:.4f}")
    if svm_result:
        print(f"  SVM f1_macro    : {svm_result['f1_macro']:.4f}")
    if rf_result:
        print(f"  RF  accuracy    : {rf_result['accuracy']:.4f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
