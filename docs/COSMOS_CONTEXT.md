# COSMOS — Master Context
**Disaster Response Recommendation and Decision Support System for LGUs**
Academic thesis prototype | 3rd-year CS students | Small team | Free-tier budget

---

## What COSMOS Is
A government-grade dashboard that scrapes Filipino disaster social media (Facebook/X), runs an NLP/ML pipeline, and delivers prioritized recommendations to LGU Officers. Backend is Python Flask. Frontend is Next.js. Database is Supabase.

---

## Tech Stack (Locked)
| Layer | Technology |
|---|---|
| Frontend | Next.js (App Router), TypeScript, Tailwind CSS, Chart.js, WordCloud |
| Backend | Python Flask |
| Database | Supabase (PostgreSQL) + Supabase Auth |
| ML | Anchored CorEx, Linear SVM OvR, VADER, Random Forest (scikit-learn) |
| Recommendations | Rule-Based IF-THEN engine |
| Scraping | Apify Actors |
| Deployment | Vercel (frontend), Render/Railway (backend), Supabase (DB) |

---

## ML Pipeline — NEVER reorder or substitute
```
1. Apify Scrape → raw JSON
2. Text Preprocessing (NLTK, spaCy, deep_translator)
3. Anchored CorEx → keyword expansion + topic sets
4. Linear SVM (OvR) → topic labels per post (multi-label)
5. VADER → sentiment compound score
6. Random Forest → priority level (Critical/High/Medium/Low)
7. Rule-Based Engine → IF-THEN recommendations
8. Feedback Loop → monitors metrics, triggers retraining
```

**Do NOT substitute:** CorEx → not LDA/BERTopic | SVM → not BERT | VADER → not transformer | RF → not neural | Rules → not LLM
**Reason:** Thesis defensibility + explainability requirement.

---

## Database Schema
```
users            → id, name, email, password_hash, role, created_at
posts            → id, platform, post_text, timestamp, engagement_count
comments         → id, post_id, comment_text
topics           → id, post_id, topic_label, confidence  ← MULTI-ROW per post (see below)
sentiments       → id, post_id, compound, positive, negative, neutral
priorities       → id, post_id, priority_level
recommendations  → id, post_id, recommendation_text, response_cluster
activity_logs    → id, user_id, action, timestamp
feedback_metrics → id, model_name, f1_score, accuracy, coherence_score
```

---

## Categorization Rules (Critical)
- **One post = one DB record. Never duplicated.**
- One post may have **multiple topic rows** in `topics` table (multi-label, not multi-record).
- Comments **inherit parent post topics by default**.
- Comments only get independent topics if they clearly diverge from the parent.
- Topic labels are linked attributes, not split records.

---

## API Endpoints
```
POST /api/login                  — Public
POST /api/logout                 — Any auth
GET  /api/topics                 — lgu_officer, admin
GET  /api/sentiment              — lgu_officer, admin
GET  /api/priorities             — lgu_officer, admin
GET  /api/recommendations        — lgu_officer, admin
GET  /api/export/pdf             — lgu_officer, admin
GET  /api/export/csv             — lgu_officer, admin
GET  /api/users                  — admin only
POST /api/users                  — admin only
PUT  /api/users/:id              — admin only
DELETE /api/users/:id            — admin only
POST /api/collect-data           — admin only
POST /api/retrain-models         — admin only
GET  /api/health                 — public
```

---

## User Roles
| Role | Permissions |
|---|---|
| admin | Manage users, trigger scraping, trigger retraining, view all logs |
| lgu_officer | View analytics, receive recommendations, generate reports |

No public registration. Admin adds users only.

---

## Folder Structure
```
app/                          ← Next.js App Router
  login/
  dashboard/
    analytics/ | recommendations/ | reports/ | settings/
  admin/
    users/ | logs/ | scraping/ | retraining/

components/
  layout/ | dashboard/ | charts/ | recommendations/ | auth/ | ui/

backend/
  app.py
  routes/          ← auth, posts, topics, sentiment, priority, recommendations, reports, users, scraping, retraining
  services/        ← scraper, preprocessing, corex, svm, vader, random_forest, rules_engine, feedback, report
  middleware/      ← auth_middleware.py
  database/        ← supabase_client.py, queries.py
  models/          ← .pkl files

ml_pipeline/
  training/ | inference/ | models/ | experiments/
```

---

## Priority Classification Logic
| Priority | Condition |
|---|---|
| Critical | compound ≤ -0.5 AND high engagement |
| High | compound ≤ -0.05 AND moderate engagement |
| Medium | neutral compound OR moderate negative |
| Low | compound ≥ 0.05 OR minimal engagement |

---

## Dashboard Pages
**LGU Officer:** Overview → Topic Monitoring → Sentiment Analytics → Priority Alerts → Recommendations → Reports
**Admin only:** User Management → Activity Logs → Data Collection → Model Monitoring → Retraining

---

## AI Behavior Rules
- **Routes are thin. Services are thick.** Routes parse/validate → call service → return response.
- Suggest better solutions when you see inefficiencies, but explain the trade-off.
- Prefer simplicity > maintainability > scalability > performance.
- Solutions must be defensible in a CS thesis. Prefer explainable over black-box.
- Assume free-tier constraints: Supabase, Vercel, Render/Railway.
- When multiple solutions exist: give best option, low-cost option, and easiest option.
- Backend logic must NEVER leak into frontend. ML pipeline must remain independent.
- If a design is too complex or expensive for a 3-person student team, say so.

---

## Known Thesis Inconsistencies
| Issue | Resolution |
|---|---|
| Priority: 3 levels (High/Med/Low) vs 4 (Critical/High/Med/Low) | Use 4 levels — matches dashboard and context.md |
| Engagement: single `engagement_count` vs split reaction/comment/share | RF uses split counts; posts table stores combined |
| Anchor words for CorEx | Thesis references NDRRMC clusters but never lists them — define your own |
| Training data source | "Manual annotation by domain experts" — must build/annotate dataset yourself |
