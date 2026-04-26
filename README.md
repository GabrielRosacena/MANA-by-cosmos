# MANA — Manila Advisory Network Alert

Disaster Response Recommendation and Decision Support System for LGUs.
Frontend prototype backed by a Python Flask/Django API.

---

## Project Structure

```
MANA/
├── frontend/
│   ├── index.html          # App shell — HTML structure only
│   ├── css/
│   │   └── style.css       # All styles (dark/light theme, components)
│   ├── js/
│   │   ├── config.js       # API_BASE, USE_MOCK toggle, apiFetch(), JWT helpers
│   │   ├── utils.js        # Pure helpers: formatNumber, filterPosts, showToast, etc.
│   │   ├── auth.js         # Login/logout, profile, password, captcha
│   │   ├── posts.js        # Post cards, pin/watchlist, alerts, cluster detail
│   │   ├── charts.js       # Histogram, line chart, bar chart, donut
│   │   ├── dashboard.js    # KPI cards, keywords, source directory, cluster nav
│   │   └── main.js         # App state, init(), event bindings, page routing
│   └── assets/
│       ├── spinner.svg
│       ├── images/
│       └── icons/
├── backend/
│   ├── app.py              # Flask entry point
│   ├── routes/
│   │   ├── auth.py         # /api/auth/* endpoints
│   │   ├── posts.py        # /api/posts, /api/clusters, /api/watchlist, /api/dashboard/*
│   │   └── stats.py        # /api/analytics/*
│   └── models/
│       └── __init__.py     # SQLAlchemy model definitions (add yours here)
└── README.md
```

---

## Quick Start (Frontend Only / Demo Mode)

1. Open `frontend/index.html` in any browser.
2. Everything works with `USE_MOCK = true` in `config.js` — no backend needed.

---

## Connecting to the Backend

1. Install Python dependencies:
   ```bash
   pip install flask flask-cors flask-sqlalchemy flask-jwt-extended
   ```

2. Run the Flask server:
   ```bash
   cd backend
   python app.py
   ```

3. In `frontend/js/config.js`, flip the toggle:
   ```js
   const USE_MOCK = false;
   ```

4. All data will now come from your Flask API at `http://localhost:5000/api`.

---

## Backend Implementation Checklist

Each route file has `# TODO` comments marking where to plug in DB queries.

| File           | Implement                                              |
|----------------|--------------------------------------------------------|
| `routes/auth.py`  | Real user table, JWT secret from env, email SMTP    |
| `routes/posts.py` | Post, Cluster, Watchlist DB models + queries        |
| `routes/stats.py` | Aggregation queries grouped by date range           |
| `models/`         | SQLAlchemy Post, Cluster, User, Watchlist models    |

---

## JS Module Load Order

Scripts must be loaded in `index.html` in this order:
```html
<script src="js/config.js"></script>
<script src="js/utils.js"></script>
<script src="js/auth.js"></script>
<script src="js/posts.js"></script>
<script src="js/charts.js"></script>
<script src="js/dashboard.js"></script>
<script src="js/main.js"></script>
```

---

## Thesis Reference

System architecture based on Chapter 3 — Monolithic Layered Architecture:
- Layer 1: Data Acquisition (Apify scraper → backend)
- Layer 2: Preprocessing (NLTK, spaCy, deep_translator)
- Layer 3: Topic Analysis (Anchored CorEx + Linear SVM)
- Layer 4: Sentiment & Priority (VADER + Random Forest)
- Layer 5: Decision Support (Rule-based recommendations)
- Layer 6: Feedback Loop (model retraining triggers)
