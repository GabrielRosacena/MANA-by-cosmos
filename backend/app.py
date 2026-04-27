"""
MANA — Flask Backend Entry Point
Run: python app.py  (dev)
     gunicorn app:app  (prod)

Install: pip install flask flask-cors flask-sqlalchemy flask-jwt-extended
"""

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from data import seed_clusters
from models import db
from routes.auth  import auth_bp
from routes.posts import posts_bp
from routes.stats import stats_bp
from routes.admin import admin_bp

app = Flask(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
app.config["JWT_SECRET_KEY"] = "CHANGE_THIS_IN_PRODUCTION"   # <- replace before deploy
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

def ensure_database():
    with app.app_context():
        db.create_all()
        seed_clusters()

if __name__ == "__main__":
    ensure_database()
    app.run(debug=True, port=5000)
