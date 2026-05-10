"""
MANA — Shared data helpers
Cluster definitions plus lightweight heuristics for imported social posts.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone

from models import Cluster, db

CLUSTER_DEFINITIONS = [
    {
        "id": "cluster-a",
        "short": "Cluster A",
        "name": "Food and Non-food Items (NFIs)",
        "description": "Tracks posts about food packs, water, hygiene kits, blankets, and other basic relief needs.",
        "keywords": ["relief goods", "rice", "water refill", "hygiene kit", "blanket", "food pack", "pagkain", "bigas", "relief pack", "drinking water", "canned goods", "sardinas", "noodles", "inumin", "water sachet", "ayuda", "NFI", "non-food items"],
        "accent": "#f59e0b",
        "recommendation": "Dispatch rapid food and NFI validation support to the affected area within the next response cycle.",
    },
    {
        "id": "cluster-b",
        "short": "Cluster B",
        "name": "WASH, Medical and Public Health, Nutrition, Mental Health and Psychosocial Support (Health)",
        "description": "Tracks posts about health, medicine, clean water, nutrition, and mental health support.",
        "keywords": ["fever", "insulin", "washing area", "dehydration", "doctor", "medical team", "medicine", "gamot", "health center", "clean water", "clinic", "nurse", "ospital", "sugat", "wound", "injured", "leptospirosis", "diarrhea", "cholera", "first aid", "tubig linis"],
        "accent": "#3b82f6",
        "recommendation": "Coordinate a health sweep, water safety check, and medicine support with the nearest response unit.",
    },
    {
        "id": "cluster-c",
        "short": "Cluster C",
        "name": "Camp Coordination, Management and Protection (CCCM)",
        "description": "Tracks evacuation center crowding, camp services, registration, and protection issues.",
        "keywords": ["evacuation center", "overcapacity", "privacy", "registration", "safe space", "toilet line", "evacuation site", "evacuees", "shelter", "camp", "crowded", "likas", "displaced families", "pabahay", "gym", "covered court", "barangay hall", "tent", "evacuation area"],
        "accent": "#8b5cf6",
        "recommendation": "Coordinate immediate shelter protection adjustments, sanitation checks, and overflow site support.",
    },
    {
        "id": "cluster-d",
        "short": "Cluster D",
        "name": "Logistics",
        "description": "Tracks blocked routes, delivery delays, convoy movement, and supply transport issues.",
        "keywords": ["blocked road", "convoy", "truck", "warehouse", "delivery", "reroute", "road clearing", "bridge damage", "passable", "supply route", "transport", "blocked bridge", "impassable", "mudslide", "alternate route", "aerial delivery", "bangka", "barge"],
        "accent": "#f97316",
        "recommendation": "Activate alternate routing and issue a field logistics advisory before dispatch resumes.",
    },
    {
        "id": "cluster-e",
        "short": "Cluster E",
        "name": "Emergency Telecommunications (ETC)",
        "description": "Tracks signal loss, network problems, and urgent communication needs.",
        "keywords": ["signal down", "no network", "power bank", "cell site", "radio", "connectivity", "no signal", "communication line", "internet down", "telecom", "network outage", "walang signal", "dead zone", "no wifi", "brownout", "blackout", "walang kuryente", "generator", "DRRM radio"],
        "accent": "#06b6d4",
        "recommendation": "Escalate emergency telecommunications support and deploy backup communications where needed.",
    },
    {
        "id": "cluster-f",
        "short": "Cluster F",
        "name": "Education",
        "description": "Tracks school closures, displaced learners, and temporary learning needs.",
        "keywords": ["school closure", "class suspension", "learning materials", "temporary classroom", "deped", "students", "walang pasok", "school suspension", "learners", "class cancelled", "walang klase", "no classes", "virtual learning", "school flooded", "school used as evacuation", "online class"],
        "accent": "#10b981",
        "recommendation": "Coordinate temporary learning support and school recovery planning with education partners.",
    },
    {
        "id": "cluster-g",
        "short": "Cluster G",
        "name": "Search, Rescue and Retrieval (SRR)",
        "description": "Tracks stranded people, rescue calls, rooftop signals, and retrieval updates.",
        "keywords": ["stranded", "roof", "rescue boat", "trapped family", "sos", "retrieval", "rescue team", "saklolo", "na stranded", "trapped", "save us", "tabang", "nastranded", "naipit", "helicopter", "coast guard", "search party", "swift water rescue"],
        "accent": "#ef4444",
        "recommendation": "Push rescue coordinates to the nearest SRR team and validate extraction access immediately.",
    },
    {
        "id": "cluster-h",
        "short": "Cluster H",
        "name": "Management of Dead and Missing (MDM)",
        "description": "Tracks missing persons, identification concerns, and related coordination updates.",
        "keywords": ["missing", "identified", "hospital list", "family tracing", "coordination desk", "verification", "missing person", "body identified", "casualty", "fatality", "unaccounted", "namatay", "patay", "nawawala", "nawala", "missing child", "lost contact", "remains"],
        "accent": "#64748b",
        "recommendation": "Cross-check tracing, registry, and hospital intake data with missing-person coordination desks.",
    },
]

CLUSTER_MAP = {cluster["id"]: cluster for cluster in CLUSTER_DEFINITIONS}
CLUSTER_SIGNAL_TERMS = {
    "cluster-a": {
        "relief goods", "food pack", "rice", "bigas", "pagkain", "tubig", "water", "drinking water", "blanket",
        "hygiene kit", "relief pack", "inumin", "canned goods", "sardinas", "noodles", "ayuda", "donation",
        "NFI", "distribution", "supply", "water sachet",
    },
    "cluster-b": {
        "doctor", "nurse", "hospital", "clinic", "medical", "medicine", "gamot", "health", "dehydration",
        "fever", "clean water", "sanitation", "ospital", "sugat", "wound", "injured", "sick",
        "leptospirosis", "diarrhea", "cholera", "first aid", "health center", "tubig linis",
    },
    "cluster-c": {
        "evacuation center", "evacuation site", "evacuees", "shelter", "camp", "registration", "safe space",
        "overcapacity", "crowded", "likas", "displaced", "pabahay", "gym", "covered court",
        "barangay hall", "tent", "displaced families", "evacuation area",
    },
    "cluster-d": {
        "blocked road", "bridge", "road", "truck", "convoy", "delivery", "reroute", "warehouse", "transport",
        "passable", "impassable", "landslide", "debris", "alternate route", "road clearing",
        "mudslide", "blocked bridge", "guho", "collapsed road",
    },
    "cluster-e": {
        "signal", "no signal", "no network", "network", "connectivity", "radio", "cell site", "internet",
        "telecom", "communication", "power bank", "walang signal", "dead zone", "no wifi", "brownout",
        "blackout", "walang kuryente", "generator", "power outage",
    },
    "cluster-f": {
        "school", "class suspension", "school closure", "walang pasok", "deped", "students", "learners",
        "class cancelled", "temporary classroom", "walang klase", "school flooded", "online class",
        "virtual learning", "no classes",
    },
    "cluster-g": {
        "rescue", "rescue team", "rescue boat", "stranded", "trapped", "saklolo", "sos", "roof", "retrieval",
        "save us", "tabang", "nastranded", "naipit", "helicopter", "coast guard", "naiipit",
        "swift water", "search party",
    },
    "cluster-h": {
        "missing", "missing person", "identified", "family tracing", "casualty", "fatality", "body identified",
        "hospital list", "unaccounted", "namatay", "patay", "nawawala", "nawala",
        "missing child", "lost contact",
    },
}
PRIORITY_ORDER = {"Monitoring": 1, "Moderate": 2, "High": 3, "Critical": 4}
DISTRESS_TERMS = {
    "urgent": 8,
    "alert": 8,
    "critical": 12,
    "danger": 10,
    "stranded": 14,
    "rescue": 14,
    "sos": 18,
    "evacuate": 10,
    "warning": 8,
    "lagnat": 8,
    "hospital": 8,
    "trapped": 14,
    "ashfall": 10,
    "volcano": 6,
    "flood": 8,
}
LOCATION_PATTERNS = [
    re.compile(r"#([A-Z][A-Za-z]+)"),
    re.compile(r"\b(?:sa|ng|of)\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,2})"),
]


def now_utc():
    return datetime.now(timezone.utc)


def parse_date_range(date_range: str) -> timedelta:
    mapping = {"24h": timedelta(days=1), "3d": timedelta(days=3), "7d": timedelta(days=7), "14d": timedelta(days=14), "30d": timedelta(days=30)}
    return mapping.get(date_range, timedelta(days=7))


def seed_clusters():
    for cluster in CLUSTER_DEFINITIONS:
        existing = db.session.get(Cluster, cluster["id"])
        if existing:
            existing.short = cluster["short"]
            existing.name = cluster["name"]
            existing.description = cluster["description"]
            existing.accent = cluster["accent"]
            existing.keywords_json = json.dumps(cluster["keywords"])
        else:
            db.session.add(
                Cluster(
                    id=cluster["id"],
                    short=cluster["short"],
                    name=cluster["name"],
                    description=cluster["description"],
                    accent=cluster["accent"],
                    keywords_json=json.dumps(cluster["keywords"]),
                )
            )
    db.session.commit()


def infer_cluster(text: str):
    lower = (text or "").lower()
    best_cluster = CLUSTER_DEFINITIONS[0]
    best_score = -1
    matched_keywords = []

    for cluster in CLUSTER_DEFINITIONS:
        exact_matches = [keyword for keyword in cluster["keywords"] if keyword.lower() in lower]
        signal_matches = [term for term in CLUSTER_SIGNAL_TERMS.get(cluster["id"], set()) if term in lower]
        weighted_score = (len(exact_matches) * 3) + len(signal_matches)
        if any(term in lower for term in ["sos", "saklolo", "rescue", "trapped", "stranded"]) and cluster["id"] == "cluster-g":
            weighted_score += 4
        if any(term in lower for term in ["evacuation center", "evacuees", "shelter"]) and cluster["id"] == "cluster-c":
            weighted_score += 3
        if any(term in lower for term in ["missing", "fatality", "body identified"]) and cluster["id"] == "cluster-h":
            weighted_score += 4
        score = weighted_score
        if score > best_score:
            best_cluster = cluster
            best_score = score
            matched_keywords = exact_matches or signal_matches

    if best_score <= 0:
        fallback_map = [
            ("weather", "cluster-e"),
            ("heat index", "cluster-b"),
            ("air quality", "cluster-b"),
            ("volcano", "cluster-g"),
            ("ash", "cluster-g"),
            ("evacuation", "cluster-c"),
            ("relief", "cluster-a"),
            ("medicine", "cluster-b"),
            ("school", "cluster-f"),
            ("signal", "cluster-e"),
        ]
        for trigger, cluster_id in fallback_map:
            if trigger in lower:
                best_cluster = CLUSTER_MAP[cluster_id]
                break

    hashtags = [token.strip("#") for token in re.findall(r"#([A-Za-z][A-Za-z0-9]+)", text or "")]
    keywords = matched_keywords or hashtags[:3] or best_cluster["keywords"][:2]
    return best_cluster, keywords[:6]


def infer_sentiment_score(text: str, engagement: int) -> int:
    """
    Return a distress score in range [20, 97].
    Primary: VADER compound mapped via compound_to_score().
    Fallback: keyword heuristic if vaderSentiment is unavailable.
    """
    try:
        from services.vader.sentiment_analyzer import analyze_sentiment, compound_to_score
        result = analyze_sentiment(text or "")
        return compound_to_score(result["compound"])
    except Exception:
        lower = (text or "").lower()
        score = 58
        for term, weight in DISTRESS_TERMS.items():
            if term in lower:
                score += weight
        if engagement >= 100:
            score += 8
        if engagement >= 250:
            score += 8
        return max(20, min(score, 97))


def infer_priority(text: str, engagement: int):
    lower = (text or "").lower()
    if any(term in lower for term in ["sos", "rescue", "stranded", "trapped", "critical", "danger zone"]):
        return "Critical"
    if any(term in lower for term in ["alert", "warning", "evacu", "ash", "volcano", "flood", "medical", "heat index"]):
        return "High"
    if engagement >= 100:
        return "High"
    return "Moderate"


def extract_location(text: str):
    source = text or ""
    for pattern in LOCATION_PATTERNS:
        match = pattern.search(source)
        if match:
            return match.group(1).replace("#", "").strip()
    return "Philippines"


def recommendation_for(cluster_id: str, priority: str):
    base = CLUSTER_MAP[cluster_id]["recommendation"]
    if priority == "Critical":
        return base.replace("Coordinate", "Immediately coordinate").replace("Dispatch", "Immediately dispatch")
    return base


def priority_label(priority: str):
    return {"Monitoring": "Low", "Moderate": "Medium"}.get(priority, priority)


def score_tone(score: int):
    if score >= 80:
        return "negative"
    if score >= 60:
        return "neutral"
    return "positive"


def media_type_for(item: dict):
    if item.get("isVideo"):
        return "video"
    if item.get("media"):
        return "photo"
    return "text"


def top_keywords_from_posts(posts, limit=6):
    counts = Counter()
    notes = {}
    for post in posts:
        for keyword in post.keywords:
            counts[keyword] += 1
            notes.setdefault(keyword, f"{CLUSTER_MAP[post.cluster_id]['short']} surge")
    top = counts.most_common(limit)
    return [{"keyword": keyword, "note": notes.get(keyword, "Detected keyword"), "count": count} for keyword, count in top]
