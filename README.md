# MANA — Manila Advisory Network Alert

> **Disaster Response Recommendation and Decision Support System for Philippine Local Government Units (LGUs)**

MANA is a social media analytics system designed to help **MDRRMO/CDRRMO officers** monitor disaster-related public discourse in near real-time. It automatically collects posts from Facebook and X (Twitter), processes them through an NLP and machine learning pipeline, and delivers prioritized disaster alerts with actionable response recommendations aligned with **NDRRMC operational procedures**.

---

## The Problem

The Philippines sits at the intersection of the Pacific Ring of Fire and the typhoon belt, making it one of the world's most disaster-prone nations. During emergencies, Filipino citizens turn to Facebook and X to report flooding, request rescue, and share on-the-ground observations — often before official channels publish anything.

But LGU offices face an impossible task manually: hundreds of posts per hour, written in Tagalog, English, and Taglish, containing varying levels of urgency and relevance. MANA was built to close that gap.

---

## What MANA Does

MANA transforms raw social media data into structured, prioritized disaster intelligence through a six-layer pipeline:

| Layer | Component | Technology |
|-------|-----------|------------|
| **1 · Data Acquisition** | Automated scraping of Facebook & X public pages | Apify Actors |
| **2 · Preprocessing** | Noise removal, tokenization, Tagalog→English translation, lemmatization, bigram detection | NLTK, spaCy, deep_translator |
| **3 · Topic Analysis** | Anchor-guided topic discovery + multi-class classification into NDRRMC disaster categories | Anchored CorEx + Linear SVM (One-vs-Rest) |
| **4 · Sentiment & Priority** | Sentiment scoring + urgency classification (High / Medium / Low) based on sentiment and engagement metrics | VADER + Random Forest |
| **5 · Decision Support** | IF-THEN rule engine maps topic + sentiment + priority → recommended LGU response actions | Rule-based logic (NDRRMC-aligned) |
| **6 · Feedback Loop** | Monitors model performance; triggers anchor updates, retraining, and rule refinements | Automated evaluation metrics |

---

## Key Features

- **Near-real-time monitoring dashboard** — KPI cards, keyword clouds, post clusters, and trend charts
- **Priority-flagged post feed** — posts tagged High / Medium / Low with source, engagement, and sentiment
- **Disaster topic clustering** — posts grouped by NDRRMC response categories (floods, rescue, infrastructure, evacuation, etc.)
- **Actionable recommendations** — rule-based suggestions displayed alongside each alert
- **Watchlist & pinning** — officers can track specific posts or accounts
- **Analytics view** — histogram, line chart, bar chart, and donut visualizations over configurable date ranges
- **Role-based access** — LGU Officers view dashboards; Admins manage users and trigger data collection
- **Mock mode** — full frontend demo with no backend required (`USE_MOCK = true`)

---

## System Architecture

MANA follows a **Monolithic Layered Architecture** — all pipeline components run in a single server environment with clear internal module boundaries. This design was chosen for three reasons specific to LGU deployment:

1. The pipeline processes data **sequentially** — each layer feeds directly into the next.
2. All ML components (CorEx, SVM, VADER, Random Forest) share **common preprocessed inputs**.
3. LGU server environments have **limited IT infrastructure**, making distributed/microservice architectures impractical.

```
Social Media Platforms (Facebook, X)
        │  Apify scraper
        ▼
  Raw Data Storage (NoSQL/JSON)
        │
        ▼
  Preprocessing Module (NLTK · spaCy · deep_translator)
        │
        ▼
  Topic Analysis (Anchored CorEx → Linear SVM OvR)
        │
        ▼
  Sentiment & Priority (VADER + Random Forest)
        │
        ▼
  Decision Support Engine (Rule-Based, NDRRMC-aligned)
        │
        ▼
  Relational Database ←──────── Feedback Loop
        │
        ▼
  Web Application Frontend (Dashboard · Alerts · Analytics)
```

---

## Project Structure

```
MANA/
├── frontend/
│   ├── index.html          # App shell
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
│   │   ├── auth.py         # /api/auth/* — login, JWT, user management
│   │   ├── posts.py        # /api/posts, /api/clusters, /api/watchlist, /api/dashboard/*
│   │   └── stats.py        # /api/analytics/* — aggregation by date range
│   └── models/
│       └── __init__.py     # SQLAlchemy model definitions
└── README.md
```

### Script Load Order

Scripts must be loaded in `index.html` in this exact order:

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

## Getting Started

### Option A — Frontend Demo (No Backend)

1. Clone the repository.
2. Open `frontend/index.html` in any browser.
3. Confirm `USE_MOCK = true` in `frontend/js/config.js` (default).

Everything works with mock data — no Python, no database needed.

### Option B — Full Stack

**1. Install Python dependencies**

```bash
pip install flask flask-cors flask-sqlalchemy flask-jwt-extended \
            nltk spacy vaderSentiment corex_topic scikit-learn \
            deep_translator apify-client
```

**2. Set up the database**

Configure your MySQL or PostgreSQL connection string in `backend/app.py`, then run migrations.

**3. Start the Flask server**

```bash
cd backend
python app.py
```

The API will be available at `http://localhost:5000/api`.

**4. Connect the frontend**

In `frontend/js/config.js`:

```js
const USE_MOCK = false;
const API_BASE = "http://localhost:5000/api";
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | HTML5, CSS3, Vanilla JS, Bootstrap, Chart.js |
| Backend | Python, Flask (or Django) |
| Database | MySQL / PostgreSQL (SQLAlchemy ORM) |
| NLP / ML | NLTK, spaCy, scikit-learn, corex_topic, vaderSentiment |
| Translation | deep_translator (Google Translate) |
| Data Collection | Apify Actors (Facebook & X scrapers) |
| Auth | Flask-JWT-Extended |
| Report Export | ReportLab / WeasyPrint |
| Web Server | Nginx / Apache |

---

## Backend Implementation Checklist

Each route file contains `# TODO` comments where database queries need to be plugged in.

| File | What to Implement |
|------|-------------------|
| `routes/auth.py` | User table queries, JWT secret from environment variables, SMTP email |
| `routes/posts.py` | Post, Cluster, Watchlist models + CRUD queries |
| `routes/stats.py` | Aggregation queries grouped by configurable date range |
| `models/__init__.py` | SQLAlchemy models: `Post`, `Cluster`, `User`, `Watchlist` |

---

## System Actors

Three types of users interact with MANA:

- **LGU Officer / MDRRMO Personnel** — views recommendations, monitors the dashboard, requests reports, pins posts to watchlist
- **System Administrator** — triggers data collection cycles, manages user accounts, monitors logs, initiates model retraining
- **Automated System** — continuously scrapes, preprocesses, classifies, and generates recommendations without manual intervention

---

## Evaluation

System quality is assessed against the **ISO/IEC 25010** software quality model, covering functional suitability, reliability, and usability. Machine learning components are evaluated using accuracy, precision, recall, and F1-score. The system has been tested with respondents from four groups: MDRRMO/CDRRMO personnel, IT and Computer Science students, faculty experts, and non-technical community members.

---

## Research Context

MANA is the software artifact produced as part of an undergraduate thesis on disaster response decision support for Philippine LGUs. The system was motivated by the finding that approximately **68 million Filipinos** are active social media users (PSA, 2025), and that during disaster events, citizen-generated posts on Facebook and X frequently contain time-sensitive information that official channels have not yet published.

The core research gap addressed: existing NLP systems for disaster monitoring stop at classification and sentiment scoring. MANA extends this with **urgency prioritization** and **rule-based recommendations** aligned to NDRRMC response procedures, giving frontline LGU officers a complete decision support tool rather than just a monitoring feed.

---

## License

This project is for academic and research purposes. Contact the authors for usage inquiries.