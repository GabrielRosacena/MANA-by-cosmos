"""
MANA — Flask Backend Entry Point
Run: python app.py  (dev)
     gunicorn app:app  (prod)

Install: pip install flask flask-cors flask-sqlalchemy flask-jwt-extended
"""

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from routes.auth  import auth_bp
from routes.posts import posts_bp
from routes.stats import stats_bp

app = Flask(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
app.config["JWT_SECRET_KEY"] = "CHANGE_THIS_IN_PRODUCTION"   # <- replace before deploy
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mana.db"   # switch to PostgreSQL/MySQL in prod
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ── Extensions ────────────────────────────────────────────────────────────────
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:5500"])  # add your frontend origin
JWTManager(app)

# ── Blueprints ────────────────────────────────────────────────────────────────
app.register_blueprint(auth_bp,  url_prefix="/api/auth")
app.register_blueprint(posts_bp, url_prefix="/api")
app.register_blueprint(stats_bp, url_prefix="/api")

if __name__ == "__main__":
    app.run(debug=True, port=5000)
