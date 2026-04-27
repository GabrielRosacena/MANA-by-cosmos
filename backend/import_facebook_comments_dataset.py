"""
Import an exported Apify Facebook comments dataset into the local SQLite database.

Example:
    python import_facebook_comments_dataset.py --file "C:\\Users\\USER\\Downloads\\dataset_facebook-comments-scraper.json"
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from app import app, ensure_database
from data import extract_location, infer_cluster, now_utc
from models import Comment, Post, db


def safe_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def comment_id_for(item: dict):
    fingerprint = "||".join(
        [
            item.get("facebookUrl") or "",
            item.get("postTitle") or "",
            item.get("text") or "",
            str(item.get("likesCount") or "0"),
        ]
    )
    return hashlib.sha1(fingerprint.encode("utf-8")).hexdigest()


def normalize_item(item: dict, post: Post | None):
    text = (item.get("text") or "").strip()
    title = (item.get("postTitle") or "").strip()
    combined = f"{title}\n{text}".strip()
    inferred_cluster, _keywords = infer_cluster(combined)

    return {
        "id": comment_id_for(item),
        "post_id": post.id if post else None,
        "source": "Facebook",
        "page_source": post.page_source if post else "Facebook Source",
        "author": (item.get("authorName") or item.get("author") or "Facebook user").strip() or "Facebook user",
        "text": text,
        "likes": safe_int(item.get("likesCount")),
        "post_title": title,
        "post_url": item.get("facebookUrl") or (post.source_url if post else ""),
        "cluster_id": post.cluster_id if post else inferred_cluster["id"],
        "location": post.location if post else extract_location(combined),
        "date": post.date if post and post.date else now_utc(),
        "raw_payload_json": json.dumps(item),
    }


def import_dataset(file_path: Path):
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    inserted = updated = skipped = 0

    ensure_database()
    with app.app_context():
        for item in payload:
            text = (item.get("text") or "").strip()
            post_url = item.get("facebookUrl") or ""
            if not text or not post_url:
                skipped += 1
                continue

            post = Post.query.filter_by(source_url=post_url).first()
            normalized = normalize_item(item, post)
            comment = db.session.get(Comment, normalized["id"])

            if comment:
                for field, value in normalized.items():
                    setattr(comment, field, value)
                updated += 1
            else:
                db.session.add(Comment(**normalized))
                inserted += 1

        db.session.commit()

    return inserted, updated, skipped


def main():
    parser = argparse.ArgumentParser(description="Import exported Apify Facebook comments dataset into MANA SQLite DB.")
    parser.add_argument("--file", required=True, help="Path to the exported JSON comments dataset file.")
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        raise SystemExit(f"Dataset file not found: {file_path}")

    inserted, updated, skipped = import_dataset(file_path)
    print(f"Imported comments dataset from {file_path}")
    print(f"Inserted: {inserted}")
    print(f"Updated: {updated}")
    print(f"Skipped: {skipped}")


if __name__ == "__main__":
    main()
