"""
Import an exported Apify Facebook dataset into the local SQLite database.

Example:
    python import_facebook_dataset.py --file "C:\\Users\\USER\\Downloads\\dataset_facebook-posts-scraper_2026-04-26_20-46-25-366.json"
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from app import app, ensure_database
from data import (
    infer_cluster,
    infer_priority,
    infer_sentiment_score,
    media_type_for,
    recommendation_for,
    extract_location,
    PRIORITY_ORDER,
)
from models import Post, db


def parse_iso_datetime(value: str):
    if not value:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def normalize_item(item: dict):
    text = (item.get("text") or "").strip()
    cluster, keywords = infer_cluster(text)
    engagement = int(item.get("likes") or 0) + int(item.get("comments") or 0) + int(item.get("shares") or 0)
    priority = infer_priority(text, engagement)
    sentiment_score = infer_sentiment_score(text, engagement)

    post_id = str(item.get("postId") or item.get("url") or item.get("topLevelUrl"))
    return {
        "id": post_id,
        "source": "Facebook",
        "page_source": item.get("pageName") or "Facebook Source",
        "account_url": item.get("facebookUrl") or item.get("inputUrl"),
        "author": (item.get("user") or {}).get("name") or item.get("pageName"),
        "caption": text,
        "source_url": item.get("url") or item.get("topLevelUrl") or item.get("facebookUrl"),
        "external_id": str(item.get("postId") or ""),
        "reactions": int(item.get("topReactionsCount") or item.get("likes") or 0),
        "shares": int(item.get("shares") or 0),
        "likes": int(item.get("likes") or 0),
        "reposts": 0,
        "comments": int(item.get("comments") or 0),
        "views": int(item.get("viewsCount") or 0),
        "media_type": media_type_for(item),
        "priority": priority,
        "sentiment_score": sentiment_score,
        "recommendation": recommendation_for(cluster["id"], priority),
        "status": "Monitoring",
        "cluster_id": cluster["id"],
        "date": parse_iso_datetime(item.get("time")),
        "keywords_json": json.dumps(keywords),
        "location": extract_location(text),
        "severity_rank": PRIORITY_ORDER[priority],
        "raw_payload_json": json.dumps(item),
    }


def import_dataset(file_path: Path):
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    inserted = updated = 0

    ensure_database()
    with app.app_context():
        for item in payload:
            normalized = normalize_item(item)
            post = db.session.get(Post, normalized["id"])
            if post:
                for field, value in normalized.items():
                    setattr(post, field, value)
                updated += 1
            else:
                db.session.add(Post(**normalized))
                inserted += 1
        db.session.commit()

    return inserted, updated


def main():
    parser = argparse.ArgumentParser(description="Import exported Apify Facebook dataset into MANA SQLite DB.")
    parser.add_argument("--file", required=True, help="Path to the exported JSON dataset file.")
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        raise SystemExit(f"Dataset file not found: {file_path}")

    inserted, updated = import_dataset(file_path)
    print(f"Imported dataset from {file_path}")
    print(f"Inserted: {inserted}")
    print(f"Updated: {updated}")


if __name__ == "__main__":
    main()
