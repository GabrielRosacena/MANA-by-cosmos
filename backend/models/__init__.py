"""
MANA — SQLAlchemy Models
Shared data models used by the Flask backend.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class User(TimestampMixin, db.Model):
    __tablename__ = "users"

    username = db.Column(db.String(80), primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    role = db.Column(db.String(80), nullable=False, default="LGU Analyst")
    password_hash = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(32), nullable=False, default="Active")


class Cluster(TimestampMixin, db.Model):
    __tablename__ = "clusters"

    id = db.Column(db.String(32), primary_key=True)
    short = db.Column(db.String(64), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    accent = db.Column(db.String(16), nullable=False)
    keywords_json = db.Column(db.Text, nullable=False, default="[]")

    @property
    def keywords(self):
        return json.loads(self.keywords_json or "[]")


class Post(TimestampMixin, db.Model):
    __tablename__ = "posts"

    id = db.Column(db.String(128), primary_key=True)
    source = db.Column(db.String(32), nullable=False)
    page_source = db.Column(db.String(255), nullable=False)
    account_url = db.Column(db.String(512), nullable=True)
    author = db.Column(db.String(255), nullable=True)
    caption = db.Column(db.Text, nullable=False, default="")
    source_url = db.Column(db.String(1024), nullable=False)
    external_id = db.Column(db.String(128), nullable=True, index=True)
    reactions = db.Column(db.Integer, nullable=False, default=0)
    shares = db.Column(db.Integer, nullable=False, default=0)
    likes = db.Column(db.Integer, nullable=False, default=0)
    reposts = db.Column(db.Integer, nullable=False, default=0)
    comments = db.Column(db.Integer, nullable=False, default=0)
    views = db.Column(db.Integer, nullable=False, default=0)
    media_type = db.Column(db.String(32), nullable=True)
    priority = db.Column(db.String(32), nullable=False, default="Moderate")
    sentiment_score = db.Column(db.Integer, nullable=False, default=60)
    recommendation = db.Column(db.Text, nullable=False, default="")
    status = db.Column(db.String(32), nullable=False, default="Monitoring")
    cluster_id = db.Column(db.String(32), db.ForeignKey("clusters.id"), nullable=False)
    date = db.Column(db.DateTime, nullable=False, index=True)
    keywords_json = db.Column(db.Text, nullable=False, default="[]")
    location = db.Column(db.String(255), nullable=False, default="Philippines")
    severity_rank = db.Column(db.Integer, nullable=False, default=2)
    raw_payload_json = db.Column(db.Text, nullable=True)

    cluster = db.relationship("Cluster")

    @property
    def keywords(self):
        return json.loads(self.keywords_json or "[]")

    def to_api_dict(self):
        return {
            "id": self.id,
            "source": self.source,
            "pageSource": self.page_source,
            "author": self.author or self.page_source,
            "caption": self.caption,
            "reactions": self.reactions,
            "shares": self.shares,
            "likes": self.likes,
            "reposts": self.reposts,
            "comments": self.comments,
            "priority": self.priority,
            "sentimentScore": self.sentiment_score,
            "recommendation": self.recommendation,
            "status": self.status,
            "clusterId": self.cluster_id,
            "date": self.date.isoformat(),
            "keywords": self.keywords,
            "location": self.location,
            "severityRank": self.severity_rank,
            "sourceUrl": self.source_url,
            "mediaType": self.media_type,
            "views": self.views,
        }


class Watchlist(TimestampMixin, db.Model):
    __tablename__ = "watchlists"
    __table_args__ = (db.UniqueConstraint("username", "post_id", name="uq_watchlist_username_post"),)

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), nullable=False, index=True)
    post_id = db.Column(db.String(128), db.ForeignKey("posts.id"), nullable=False, index=True)
