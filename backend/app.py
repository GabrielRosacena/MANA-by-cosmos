"""
MANA — Flask Backend Entry Point
Run: python app.py  (dev)
     gunicorn app:app  (prod)

Install: pip install flask flask-cors flask-sqlalchemy flask-jwt-extended
"""

import sqlite3

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from data import seed_clusters
from models import SystemSetting, User, db
from routes.auth  import auth_bp
from routes.posts import posts_bp
from routes.stats import stats_bp
from routes.admin import admin_bp

app = Flask(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
app.config["JWT_SECRET_KEY"] = "CHANGE_THIS_IN_PRODUCTION_SECRET_32B"   # <- replace before deploy
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mana.db"   # switch to PostgreSQL/MySQL in prod
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ── Extensions ────────────────────────────────────────────────────────────────
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:5500"])  # add your frontend origin
JWTManager(app)
db.init_app(app)

# ── Blueprints ────────────────────────────────────────────────────────────────
app.register_blueprint(auth_bp,  url_prefix="/api/auth")
app.register_blueprint(posts_bp, url_prefix="/api")
app.register_blueprint(stats_bp, url_prefix="/api")
app.register_blueprint(admin_bp, url_prefix="/api/admin")

DEFAULT_SETTINGS = {
    "general": {
        "systemName": "MANA — Manila Advisory Network Alert",
        "systemDesc": "Disaster Response Recommendation and Decision Support System for Philippine LGUs.",
        "timezone": "Asia/Manila",
        "dateFormat": "MMM D, YYYY",
        "defaultRange": "7d",
        "maintenanceMode": False,
    },
    "security": {
        "sessionTimeout": 30,
        "maxLoginAttempts": 5,
        "require2FA": False,
        "passwordMinLength": 8,
        "logRetentionDays": 90,
    },
    "notifications": {
        "emailAlerts": True,
        "criticalAlerts": True,
        "dailyDigest": False,
        "alertEmail": "admin@mana.ph",
    },
    "system": {
        "scrapeInterval": 60,
        "maxPostsPerRun": 500,
        "retryOnFail": True,
        "debugMode": False,
        "backupEnabled": True,
        "backupFreq": "daily",
    },
}


def ensure_user_columns():
    db_path = app.instance_path + "\\mana.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    columns = {row[1] for row in cur.execute("PRAGMA table_info(users)").fetchall()}
    wanted = {
        "name": "ALTER TABLE users ADD COLUMN name VARCHAR(120)",
        "last_login_at": "ALTER TABLE users ADD COLUMN last_login_at DATETIME",
        "login_count": "ALTER TABLE users ADD COLUMN login_count INTEGER NOT NULL DEFAULT 0",
    }
    for column, statement in wanted.items():
        if column not in columns:
            cur.execute(statement)
    conn.commit()
    conn.close()


def ensure_preprocessed_text_columns():
    db_path = app.instance_path + "\\mana.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS preprocessed_texts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_type VARCHAR(32) NOT NULL,
            raw_id VARCHAR(128) NOT NULL,
            raw_text TEXT,
            clean_text TEXT,
            tokens_json TEXT NOT NULL DEFAULT '[]',
            translated_text TEXT,
            translation_status VARCHAR(32) NOT NULL DEFAULT 'skipped',
            negation_handled_tokens_json TEXT NOT NULL DEFAULT '[]',
            lemmatized_tokens_json TEXT NOT NULL DEFAULT '[]',
            bigrams_json TEXT NOT NULL DEFAULT '[]',
            final_tokens_json TEXT NOT NULL DEFAULT '[]',
            is_emotion_only BOOLEAN NOT NULL DEFAULT 0,
            is_relevant BOOLEAN NOT NULL DEFAULT 1,
            parent_post_id VARCHAR(128),
            preprocessing_stage VARCHAR(32) NOT NULL DEFAULT 'tokenized',
            preprocessing_status VARCHAR(32) NOT NULL DEFAULT 'processed',
            error_message TEXT,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    columns = {row[1] for row in cur.execute("PRAGMA table_info(preprocessed_texts)").fetchall()}
    wanted = {
        "translated_text": "ALTER TABLE preprocessed_texts ADD COLUMN translated_text TEXT",
        "translation_status": "ALTER TABLE preprocessed_texts ADD COLUMN translation_status VARCHAR(32) NOT NULL DEFAULT 'skipped'",
        "negation_handled_tokens_json": "ALTER TABLE preprocessed_texts ADD COLUMN negation_handled_tokens_json TEXT NOT NULL DEFAULT '[]'",
        "lemmatized_tokens_json": "ALTER TABLE preprocessed_texts ADD COLUMN lemmatized_tokens_json TEXT NOT NULL DEFAULT '[]'",
        "bigrams_json": "ALTER TABLE preprocessed_texts ADD COLUMN bigrams_json TEXT NOT NULL DEFAULT '[]'",
        "final_tokens_json": "ALTER TABLE preprocessed_texts ADD COLUMN final_tokens_json TEXT NOT NULL DEFAULT '[]'",
        "is_emotion_only": "ALTER TABLE preprocessed_texts ADD COLUMN is_emotion_only BOOLEAN NOT NULL DEFAULT 0",
        "is_relevant": "ALTER TABLE preprocessed_texts ADD COLUMN is_relevant BOOLEAN NOT NULL DEFAULT 1",
        "parent_post_id": "ALTER TABLE preprocessed_texts ADD COLUMN parent_post_id VARCHAR(128)",
        "preprocessing_stage": "ALTER TABLE preprocessed_texts ADD COLUMN preprocessing_stage VARCHAR(32) NOT NULL DEFAULT 'tokenized'",
    }
    for column, statement in wanted.items():
        if column not in columns:
            cur.execute(statement)
    cur.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_preprocessed_record ON preprocessed_texts(record_type, raw_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS ix_preprocessed_parent_post_id ON preprocessed_texts(parent_post_id)"
    )
    conn.commit()
    conn.close()


def seed_default_users():
    if not db.session.get(User, "admin"):
        admin = User(
            username="admin",
            name="Ana Reyes",
            email="admin@mana.ph",
            role="Admin",
            status="Active",
        )
        admin.set_password("admin2026")
        db.session.add(admin)

    if not db.session.get(User, "admin_mana"):
        analyst = User(
            username="admin_mana",
            name="LGU Analyst",
            email="lgu.analyst@mana.ph",
            role="LGU Analyst",
            status="Active",
        )
        analyst.set_password("mana2026!")
        db.session.add(analyst)
    db.session.commit()


def seed_settings():
    for section, payload in DEFAULT_SETTINGS.items():
        setting = db.session.get(SystemSetting, section)
        if not setting:
            setting = SystemSetting(section=section)
            setting.set_payload(payload)
            db.session.add(setting)
    db.session.commit()


def ensure_database():
    with app.app_context():
        db.create_all()
        ensure_user_columns()
        ensure_preprocessed_text_columns()
        seed_clusters()
        seed_default_users()
        seed_settings()

if __name__ == "__main__":
    ensure_database()
    app.run(debug=True, port=5000)
