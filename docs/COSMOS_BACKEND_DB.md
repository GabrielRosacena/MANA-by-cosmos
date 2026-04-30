# COSMOS — Backend & Database Reference
Load this when working on Flask routes, services, database schema, or auth.

---

## App Factory
```python
# backend/app.py
from flask import Flask
from flask_cors import CORS
from routes.auth import auth_bp
from routes.topics import topics_bp
from routes.sentiment import sentiment_bp
from routes.priority import priority_bp
from routes.recommendations import recommendations_bp
from routes.reports import reports_bp
from routes.users import users_bp
from routes.scraping import scraping_bp
from routes.retraining import retraining_bp

def create_app():
    app = Flask(__name__)
    CORS(app, origins=["http://localhost:3000", "https://cosmos-*.vercel.app"])
    for bp in [auth_bp, topics_bp, sentiment_bp, priority_bp, recommendations_bp,
               reports_bp, users_bp, scraping_bp, retraining_bp]:
        app.register_blueprint(bp, url_prefix='/api')
    @app.route('/api/health')
    def health(): return {'status': 'ok'}
    return app

if __name__ == '__main__':
    create_app().run(debug=True, port=5000)
```

## Config
```python
# backend/config.py
import os
from dotenv import load_dotenv
load_dotenv()
SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_KEY = os.environ['SUPABASE_SERVICE_KEY']   # service role — backend only
SUPABASE_ANON_KEY = os.environ['SUPABASE_ANON_KEY']
APIFY_TOKEN = os.environ.get('APIFY_TOKEN', '')
MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')
```

```
# .env (NEVER commit)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
SUPABASE_ANON_KEY=eyJ...
APIFY_TOKEN=apify_api_xxxxx
```

---

## Supabase Client (Singleton)
```python
# backend/database/supabase_client.py
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

_client: Client = None
def get_supabase() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client
```
> Backend uses `SERVICE_KEY` (bypasses RLS). Frontend uses `ANON_KEY` (respects RLS). Never expose SERVICE_KEY to client.

---

## Auth Middleware
```python
# backend/middleware/auth_middleware.py
from functools import wraps
from flask import request, jsonify, g
from database.supabase_client import get_supabase

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token: return jsonify({'error': 'Missing auth token'}), 401
        try:
            supabase = get_supabase()
            user = supabase.auth.get_user(token)
            g.user_id = user.user.id
            result = supabase.table('users').select('role').eq('id', g.user_id).single().execute()
            g.user_role = result.data['role']
        except:
            return jsonify({'error': 'Invalid or expired token'}), 401
        return f(*args, **kwargs)
    return decorated

def require_admin(f):
    @wraps(f)
    @require_auth
    def decorated(*args, **kwargs):
        if g.user_role != 'admin': return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated

def require_lgu_officer(f):
    @wraps(f)
    @require_auth
    def decorated(*args, **kwargs):
        if g.user_role not in ('admin', 'lgu_officer'): return jsonify({'error': 'Insufficient permissions'}), 403
        return f(*args, **kwargs)
    return decorated
```

## Route Permission Map
| Endpoint | Required Role |
|---|---|
| `/login`, `/health` | Public |
| `/topics`, `/sentiment`, `/priorities`, `/recommendations`, `/export/*` | lgu_officer or admin |
| `/users`, `/collect-data`, `/retrain-models` | admin only |

---

## Route Pattern (Keep Routes Thin)
```python
# backend/routes/topics.py
from flask import Blueprint, request, jsonify
from middleware.auth_middleware import require_lgu_officer
from database.supabase_client import get_supabase

topics_bp = Blueprint('topics', __name__)

@topics_bp.route('/topics', methods=['GET'])
@require_lgu_officer
def get_topics():
    try:
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        supabase = get_supabase()
        query = supabase.table('topics').select('topic_label, post_id, confidence, posts(timestamp, platform)')
        if date_from: query = query.gte('posts.timestamp', date_from)
        if date_to: query = query.lte('posts.timestamp', date_to)
        result = query.execute()
        topic_counts = {}
        for row in result.data:
            label = row['topic_label']
            topic_counts[label] = topic_counts.get(label, 0) + 1
        return jsonify({'topics': topic_counts, 'total_posts': len(set(r['post_id'] for r in result.data))})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

## API Response Format
```python
# Success:    {"data": {...}, "message": "optional"}
# Error:      {"error": "description"}
# Paginated:  {"data": [...], "total": N, "page": 1, "per_page": 25}
# HTTP codes: 200 success | 201 created | 400 bad request | 401 unauthorized | 403 forbidden | 500 server error
```

---

## Activity Logging Pattern
```python
def log_activity(user_id: str, action: str):
    get_supabase().table('activity_logs').insert({'user_id': user_id, 'action': action}).execute()
# Call in every admin route after the action completes.
```

---

## Frontend API Helper (Next.js)
```typescript
// lib/api/client.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000/api';

export async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('supabase_token');
  const res = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Network error' }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}
```

---

## Database Schema (Full SQL)
Run in Supabase SQL Editor:

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'lgu_officer')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    platform TEXT NOT NULL CHECK (platform IN ('facebook', 'x')),
    post_text TEXT NOT NULL,
    timestamp TIMESTAMPTZ,
    engagement_count INTEGER DEFAULT 0,
    reaction_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    share_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_posts_timestamp ON posts(timestamp DESC);
CREATE INDEX idx_posts_platform ON posts(platform);

CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    comment_text TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_comments_post_id ON comments(post_id);

-- CRITICAL: One post can have MULTIPLE topic rows (multi-label)
-- But same post + same topic must never be duplicated (unique index below)
CREATE TABLE topics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    topic_label TEXT NOT NULL,
    confidence REAL DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE UNIQUE INDEX idx_topics_post_topic ON topics(post_id, topic_label);
CREATE INDEX idx_topics_label ON topics(topic_label);

CREATE TABLE sentiments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    compound REAL NOT NULL,
    positive REAL, negative REAL, neutral REAL,
    sarcasm_flag BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE UNIQUE INDEX idx_sentiments_post ON sentiments(post_id);

CREATE TABLE priorities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    priority_level TEXT NOT NULL CHECK (priority_level IN ('Critical', 'High', 'Medium', 'Low')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE UNIQUE INDEX idx_priorities_post ON priorities(post_id);

CREATE TABLE recommendations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    recommendation_text TEXT NOT NULL,
    response_cluster TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE UNIQUE INDEX idx_recommendations_post ON recommendations(post_id);

CREATE TABLE activity_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_activity_logs_time ON activity_logs(timestamp DESC);

CREATE TABLE feedback_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name TEXT NOT NULL,
    f1_score REAL, accuracy REAL, coherence_score REAL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Row Level Security (RLS)
```sql
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE sentiments ENABLE ROW LEVEL SECURITY;
ALTER TABLE priorities ENABLE ROW LEVEL SECURITY;
ALTER TABLE recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE feedback_metrics ENABLE ROW LEVEL SECURITY;

-- Authenticated users can read analytics data
CREATE POLICY "Auth users read posts" ON posts FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Auth users read topics" ON topics FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Auth users read sentiments" ON sentiments FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Auth users read priorities" ON priorities FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "Auth users read recommendations" ON recommendations FOR SELECT USING (auth.role() = 'authenticated');

-- Backend (service key) bypasses RLS for all writes
-- Admin-only tables managed entirely via service key on backend
```

## Multi-Topic Insert Pattern (Critical)
```python
# backend/database/queries.py
def insert_post_with_pipeline_results(supabase, post_data: dict, topics: list[str],
                                       sentiment: dict, priority: str, recommendation: dict) -> str:
    # 1. Insert post (single record)
    post = supabase.table('posts').insert({
        'platform': post_data['platform'],
        'post_text': post_data['post_text'],
        'timestamp': post_data['timestamp'],
        'engagement_count': post_data['engagement_count'],
        'reaction_count': post_data.get('reaction_count', 0),
        'comment_count': post_data.get('comment_count', 0),
        'share_count': post_data.get('share_count', 0),
    }).execute()
    post_id = post.data[0]['id']

    # 2. Insert multiple topic rows (one per label, never duplicate post record)
    for topic in topics:
        supabase.table('topics').upsert(
            {'post_id': post_id, 'topic_label': topic, 'confidence': 0.0},
            on_conflict='post_id,topic_label'  # uses unique index
        ).execute()

    # 3. One sentiment row per post
    supabase.table('sentiments').insert({
        'post_id': post_id, 'compound': sentiment['compound'],
        'positive': sentiment['positive'], 'negative': sentiment['negative'], 'neutral': sentiment['neutral']
    }).execute()

    # 4. One priority row per post
    supabase.table('priorities').insert({'post_id': post_id, 'priority_level': priority}).execute()

    # 5. One recommendation row per post
    supabase.table('recommendations').insert({
        'post_id': post_id,
        'recommendation_text': recommendation['recommendation_text'],
        'response_cluster': recommendation['response_cluster']
    }).execute()

    return post_id
```

## Common Dashboard Queries
```python
# Topic distribution
def get_topic_distribution(supabase, date_from=None, date_to=None) -> list:
    query = supabase.table('topics').select('topic_label, posts(timestamp)').order('topic_label')
    # Apply date filters on joined posts.timestamp
    return query.execute().data

# Full priority feed for alerts table
def get_priority_feed(supabase, priority_filter=None, limit=50) -> list:
    query = (supabase.table('priorities')
        .select('priority_level, posts(post_text, timestamp, platform), recommendations(recommendation_text)')
        .order('posts.timestamp', desc=True)
        .limit(limit))
    if priority_filter:
        query = query.eq('priority_level', priority_filter)
    return query.execute().data

# Sentiment trend by date
def get_sentiment_trend(supabase, days=30) -> list:
    return (supabase.table('sentiments')
        .select('compound, posts(timestamp)')
        .gte('posts.timestamp', f'now() - interval \'{days} days\'')
        .execute().data)

# Model metrics for monitoring
def get_latest_metrics(supabase) -> list:
    return (supabase.table('feedback_metrics')
        .select('*')
        .order('created_at', desc=True)
        .limit(10)
        .execute().data)
```

---

## Deployment (Render Free Tier)
```yaml
# render.yaml
services:
  - type: web
    name: cosmos-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn "app:create_app()" --bind 0.0.0.0:$PORT
    envVars:
      - key: SUPABASE_URL
        sync: false
      - key: SUPABASE_SERVICE_KEY
        sync: false
      - key: SUPABASE_ANON_KEY
        sync: false
      - key: APIFY_TOKEN
        sync: false
```
> ⚠️ Render free tier spins down after 15 min inactivity. First request ~30s cold start. Mention this to thesis panel.
