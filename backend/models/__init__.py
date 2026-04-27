"""
MANA — SQLAlchemy Models
Shared data models used by the Flask backend.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

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
    name = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    role = db.Column(db.String(80), nullable=False, default="LGU Analyst")
    password_hash = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(32), nullable=False, default="Active")
    last_login_at = db.Column(db.DateTime, nullable=True)
    login_count = db.Column(db.Integer, nullable=False, default=0)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def to_api_dict(self):
        return {
            "id": self.username,
            "username": self.username,
            "name": self.name or self.username,
            "email": self.email,
            "role": self.role,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "login_count": self.login_count or 0,
        }


class ActivityLog(TimestampMixin, db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    actor_username = db.Column(db.String(80), nullable=True, index=True)
    actor_name = db.Column(db.String(120), nullable=False)
    action = db.Column(db.String(120), nullable=False)
    detail = db.Column(db.Text, nullable=False, default="")
    type = db.Column(db.String(32), nullable=False, default="system", index=True)

    def to_api_dict(self):
        return {
            "id": self.id,
            "user_id": self.actor_username,
            "user_name": self.actor_name,
            "action": self.action,
            "detail": self.detail,
            "type": self.type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SystemSetting(TimestampMixin, db.Model):
    __tablename__ = "system_settings"

    section = db.Column(db.String(32), primary_key=True)
    payload_json = db.Column(db.Text, nullable=False, default="{}")

    @property
    def payload(self):
        return json.loads(self.payload_json or "{}")

    def set_payload(self, payload):
        self.payload_json = json.dumps(payload or {})


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


class Comment(TimestampMixin, db.Model):
    __tablename__ = "comments"

    id = db.Column(db.String(128), primary_key=True)
    post_id = db.Column(db.String(128), db.ForeignKey("posts.id"), nullable=True, index=True)
    source = db.Column(db.String(32), nullable=False, default="Facebook")
    page_source = db.Column(db.String(255), nullable=False, default="Facebook Source")
    author = db.Column(db.String(255), nullable=False, default="Facebook user")
    text = db.Column(db.Text, nullable=False, default="")
    likes = db.Column(db.Integer, nullable=False, default=0)
    post_title = db.Column(db.Text, nullable=False, default="")
    post_url = db.Column(db.String(1024), nullable=False)
    cluster_id = db.Column(db.String(32), db.ForeignKey("clusters.id"), nullable=False)
    location = db.Column(db.String(255), nullable=False, default="Philippines")
    date = db.Column(db.DateTime, nullable=False, index=True)
    raw_payload_json = db.Column(db.Text, nullable=True)

    post = db.relationship("Post")
    cluster = db.relationship("Cluster")

    def to_api_dict(self):
        return {
            "id": self.id,
            "postId": self.post_id,
            "source": self.source,
            "pageSource": self.page_source,
            "author": self.author,
            "text": self.text,
            "likes": self.likes,
            "postTitle": self.post_title,
            "postUrl": self.post_url,
            "clusterId": self.cluster_id,
            "location": self.location,
            "date": self.date.isoformat() if self.date else None,
        }


class Watchlist(TimestampMixin, db.Model):
    __tablename__ = "watchlists"
    __table_args__ = (db.UniqueConstraint("username", "post_id", name="uq_watchlist_username_post"),)

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), nullable=False, index=True)
    post_id = db.Column(db.String(128), db.ForeignKey("posts.id"), nullable=False, index=True)
