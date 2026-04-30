# COSMOS — ML Pipeline Reference
Load this when working on any ML, preprocessing, or pipeline code.

---

## Stage 1: Apify Scraper
```python
# backend/services/scraper/apify_collector.py
from apify_client import ApifyClient
import os

client = ApifyClient(os.environ['APIFY_TOKEN'])

def collect_facebook(page_urls: list, date_from: str, date_to: str) -> list:
    run = client.actor("apify/facebook-posts-scraper").call(run_input={
        "startUrls": [{"url": url} for url in page_urls],
        "resultsLimit": 500,
    })
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    return [normalize_post(strip_pii(item), 'facebook') for item in items]

def normalize_post(raw: dict, platform: str) -> dict:
    return {
        'platform': platform,
        'post_text': raw.get('postText') or raw.get('text', ''),
        'timestamp': raw.get('timestamp') or raw.get('date'),
        'reaction_count': int(raw.get('likes', 0)),
        'comment_count': int(raw.get('comments', 0)) if isinstance(raw.get('comments'), int) else 0,
        'share_count': int(raw.get('shares', 0)),
        'engagement_count': int(raw.get('likes', 0)) + int(raw.get('shares', 0)),
        'comments': [{'comment_text': c.get('text', '')} for c in raw.get('comments', []) if isinstance(c, dict)]
    }

def strip_pii(post: dict) -> dict:
    for key in ('userName', 'userUrl', 'profilePic'):
        post.pop(key, None)
    return post
```
**Thesis gaps:** Exact Apify actor IDs not specified. X/Twitter scraper not detailed. Rate limits undefined.

---

## Stage 2: Text Preprocessing
**Order is fixed — do not change:**
1. Noise removal (URLs, mentions, HTML, special chars)
2. Lowercasing
3. Whitespace normalization
4. Tokenization
5. Tagalog→English translation (deep_translator → Google Translate)
6. Negation handling
7. Lemmatization
8. Bigram detection
9. Stop-word removal

```python
# backend/services/preprocessing/text_cleaner.py
import re
import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords
from deep_translator import GoogleTranslator

nltk.download('punkt', quiet=True)
nltk.download('wordnet', quiet=True)
nltk.download('stopwords', quiet=True)

lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words('english'))
translator = GoogleTranslator(source='auto', target='en')

def preprocess_text(text: str) -> str:
    text = re.sub(r'http\S+|www\.\S+', '', text)    # URLs
    text = re.sub(r'@\w+', '', text)                 # mentions
    text = re.sub(r'<[^>]+>', '', text)              # HTML
    text = re.sub(r'[^a-zA-Z\s]', ' ', text)        # special chars
    text = text.lower()
    text = re.sub(r'\s+', ' ', text).strip()
    tokens = word_tokenize(text)
    try:
        text = translator.translate(text)            # Tagalog→English
    except Exception:
        pass
    tokens = word_tokenize(text.lower())
    tokens = [lemmatizer.lemmatize(t) for t in tokens if t not in stop_words and len(t) > 2]
    return ' '.join(tokens)
```

---

## Stage 3: Anchored CorEx — Topic Keyword Expansion
```python
# backend/services/corex/topic_modeler.py
import corextopic.corextopic as ct
from sklearn.feature_extraction.text import CountVectorizer

# Define NDRRMC-aligned anchor words (expand based on your dataset)
ANCHOR_WORDS = {
    'flood':                ['flood', 'baha', 'tubig', 'inundation', 'flash flood'],
    'evacuation':           ['evacuation', 'evacuate', 'shelter', 'likas', 'evacuation center'],
    'rescue':               ['rescue', 'trapped', 'stranded', 'sagipin', 'search and rescue'],
    'infrastructure_damage':['damage', 'collapsed', 'road', 'bridge', 'landslide', 'guho'],
    'relief':               ['relief', 'ayuda', 'goods', 'donation', 'food pack'],
    'power_outage':         ['blackout', 'kuryente', 'power outage', 'electricity', 'walang kuryente'],
    'health_medical':       ['hospital', 'injured', 'medical', 'health', 'sick', 'ospital'],
    'communication':        ['signal', 'network', 'communication', 'internet', 'no signal'],
}
N_TOPICS = len(ANCHOR_WORDS)

def train_corex(texts: list[str]):
    vectorizer = CountVectorizer(max_features=5000, binary=True, ngram_range=(1, 2))
    doc_term_matrix = vectorizer.fit_transform(texts)
    vocab = vectorizer.get_feature_names_out()

    anchor_indices = [
        [list(vocab).index(w) for w in words if w in list(vocab)]
        for words in ANCHOR_WORDS.values()
    ]

    model = ct.Corex(n_hidden=N_TOPICS, words=list(vocab), seed=42)
    model.fit(doc_term_matrix, anchors=anchor_indices, anchor_strength=3)

    expanded_keywords = {}
    for i, name in enumerate(ANCHOR_WORDS.keys()):
        top_words = model.get_topics(topic=i, n_words=20)
        expanded_keywords[name] = [w for w, mi, sign in top_words if sign == 1]

    return model, expanded_keywords, vectorizer

def get_topic_coherence(model) -> list[float]:
    # Target: TC ≥ 0.50 overall. Flag topics with TC < 0.30 for anchor refinement.
    return list(model.tcs)
```
**Evaluation targets:** TC ≥ 0.50 overall | Flag individual topics < 0.30
**Thesis gaps:** Exact anchor words not listed, `anchor_strength` not specified (using 3), `max_features` not specified.

---

## Stage 4: Linear SVM (OvR) — Topic Classification
- Multi-label: one post can receive multiple topic labels
- One post = one DB record; topics stored as multiple rows in `topics` table
- 80/20 stratified split | Tune C via cross-validation | Evaluate per-class F1

```python
# backend/services/svm/topic_classifier.py
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.multiclass import OneVsRestClassifier
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.metrics import classification_report
import joblib

TOPIC_LABELS = ['flood','evacuation','rescue','infrastructure_damage','relief','power_outage','health_medical','communication']

def train_svm(texts: list[str], labels: list[list[str]]):
    mlb = MultiLabelBinarizer(classes=TOPIC_LABELS)
    y = mlb.fit_transform(labels)
    tfidf = TfidfVectorizer(max_features=5000, sublinear_tf=True)
    X = tfidf.fit_transform(texts)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    clf = OneVsRestClassifier(LinearSVC(max_iter=10000, class_weight='balanced'))
    grid = GridSearchCV(clf, {'estimator__C': [0.01, 0.1, 1.0, 10.0]}, cv=5, scoring='f1_macro', n_jobs=-1)
    grid.fit(X_train, y_train)
    best = grid.best_estimator_
    report = classification_report(y_test, best.predict(X_test), target_names=TOPIC_LABELS, output_dict=True)
    joblib.dump(best, 'models/svm_classifier.pkl')
    joblib.dump(tfidf, 'models/tfidf_vectorizer.pkl')
    joblib.dump(mlb, 'models/label_binarizer.pkl')
    return best, report

def predict_topics(text: str) -> list[str]:
    clf = joblib.load('models/svm_classifier.pkl')
    tfidf = joblib.load('models/tfidf_vectorizer.pkl')
    mlb = joblib.load('models/label_binarizer.pkl')
    return list(mlb.inverse_transform(clf.predict(tfidf.transform([text])))[0])
```
**Evaluation target:** F1-score (macro) ≥ 0.75
**Thesis gaps:** Training dataset source/size not specified. Decision threshold for multi-label not specified (using LinearSVC default).

---

## Stage 5: VADER — Sentiment Analysis
- Compound thresholds: ≥ 0.05 = Positive | ≤ -0.05 = Negative | else = Neutral
- Sarcasm detection: (1) positive compound + inherently negative topic → flag; (2) comment deviates from thread average → flag; (3) manual MDRRMO override

```python
# backend/services/vader/sentiment_analyzer.py
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import numpy as np

analyzer = SentimentIntensityAnalyzer()
NEGATIVE_TOPICS = {'flood', 'infrastructure_damage', 'rescue', 'power_outage', 'health_medical'}

def analyze_sentiment(text: str) -> dict:
    s = analyzer.polarity_scores(text)
    c = s['compound']
    return {
        'compound': c, 'positive': s['pos'], 'negative': s['neg'], 'neutral': s['neu'],
        'label': 'Positive' if c >= 0.05 else ('Negative' if c <= -0.05 else 'Neutral')
    }

def check_sarcasm_incongruence(compound: float, topics: list[str]) -> bool:
    return compound >= 0.05 and any(t in NEGATIVE_TOPICS for t in topics)

def check_thread_deviation(comment_compound: float, thread_compounds: list[float], threshold: float = 1.5) -> bool:
    if len(thread_compounds) < 3: return False
    std = np.std(thread_compounds)
    if std == 0: return False
    return abs(comment_compound - np.mean(thread_compounds)) / std > threshold
```
**Thesis gaps:** Thread deviation threshold undefined (using 1.5 std). Aggregation method not specified (using mean). Sarcasm override storage mechanism unclear.

---

## Stage 6: Random Forest — Priority Classification
Feature vector: `[reaction_count, comment_count, share_count, compound_score, disaster_relevance, recurrence_frequency]`
Output classes: **Critical, High, Medium, Low**

```python
# backend/services/random_forest/priority_classifier.py
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib, pandas as pd

FEATURE_COLS = ['reaction_count','comment_count','share_count','compound_score','disaster_relevance','recurrence_frequency']

def build_feature_vector(post: dict) -> dict:
    return {
        'reaction_count': post.get('reaction_count', 0),
        'comment_count': post.get('comment_count', 0),
        'share_count': post.get('share_count', 0),
        'compound_score': post.get('compound', 0.0),
        'disaster_relevance': 1 if post.get('topic_labels') else 0,
        'recurrence_frequency': post.get('topic_frequency', 0),
    }

def train_random_forest(data: pd.DataFrame):
    X = data[FEATURE_COLS]
    y = data['priority_level']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    rf = RandomForestClassifier(n_estimators=100, class_weight='balanced', random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    report = classification_report(y_test, rf.predict(X_test), output_dict=True)
    importances = dict(zip(FEATURE_COLS, rf.feature_importances_))
    joblib.dump(rf, 'models/rf_prioritizer.pkl')
    return rf, report, importances

def predict_priority(features: dict) -> str:
    rf = joblib.load('models/rf_prioritizer.pkl')
    return rf.predict(pd.DataFrame([features])[FEATURE_COLS])[0]
```
**Evaluation target:** F1-score (macro) ≥ 0.70 | Confirm `compound` and `engagement` are top features
**Thesis gaps:** `disaster_relevance` and `recurrence_frequency` not precisely defined. Hyperparameters not specified. Training label source not specified.

---

## Stage 7: Rule-Based Recommendation Engine
```python
# backend/services/rules_engine/recommender.py

def generate_recommendation(topic: str, sentiment_label: str, engagement_score: int, priority_level: str) -> dict:
    t, s, e, p = topic.lower(), sentiment_label, engagement_score, priority_level.lower()

    if t == 'flood' and s == 'Negative' and e >= 1000 and p == 'high':
        return {'recommendation_text': 'Immediate MDRRMO Disaster Response: Activate flood response team. Coordinate evacuation. Alert barangay officials.', 'response_cluster': 'Search, Rescue, and Retrieval'}
    if t == 'rescue' and p in ('critical', 'high'):
        return {'recommendation_text': 'Deploy search and rescue units immediately. Coordinate with MDRRMO.', 'response_cluster': 'Search, Rescue, and Retrieval'}
    if t == 'infrastructure_damage' and p in ('critical', 'high', 'medium'):
        return {'recommendation_text': 'Dispatch assessment team. Coordinate with DPWH. Report to MDRRMO.', 'response_cluster': 'Public Works and Engineering'}
    if t == 'evacuation' and p in ('critical', 'high'):
        return {'recommendation_text': 'Activate evacuation protocols. Open evacuation centers. Coordinate transport.', 'response_cluster': 'Evacuation'}
    if t == 'relief' and p in ('critical', 'high', 'medium'):
        return {'recommendation_text': 'Coordinate relief distribution. Mobilize food packs and supplies.', 'response_cluster': 'Relief'}
    if t == 'power_outage' and p in ('critical', 'high', 'medium'):
        return {'recommendation_text': 'Report to local electric cooperative. Deploy backup power to critical facilities.', 'response_cluster': 'Utilities'}
    if t == 'health_medical' and p in ('critical', 'high', 'medium'):
        return {'recommendation_text': 'Alert medical response teams. Coordinate with hospitals and health centers.', 'response_cluster': 'Health'}
    if t == 'communication' and p in ('critical', 'high'):
        return {'recommendation_text': 'Activate emergency communication channels. Coordinate with telecom providers.', 'response_cluster': 'Logistics and Communication'}
    if p in ('critical', 'high'):
        return {'recommendation_text': 'Alert Disaster Response Team for immediate coordination.', 'response_cluster': 'General Response'}
    if p == 'medium':
        return {'recommendation_text': 'Prepare response resources. Monitor situation for escalation.', 'response_cluster': 'General Monitoring'}
    return {'recommendation_text': 'Continue monitoring. No immediate action required.', 'response_cluster': 'Monitoring'}
```

---

## Stage 8: Feedback Loop
```python
# backend/services/feedback/feedback_loop.py
THRESHOLDS = {'svm_f1_macro': 0.75, 'rf_f1_macro': 0.70, 'corex_coherence': 0.50}

def check_metrics(current_metrics: dict) -> dict:
    return {
        'corex': current_metrics.get('corex_coherence', 1.0) < THRESHOLDS['corex_coherence'],
        'svm': current_metrics.get('svm_f1_macro', 1.0) < THRESHOLDS['svm_f1_macro'],
        'random_forest': current_metrics.get('rf_f1_macro', 1.0) < THRESHOLDS['rf_f1_macro'],
    }
```

---

## requirements.txt
```
flask==3.0.0
flask-cors==4.0.0
gunicorn==21.2.0
supabase==2.0.0
python-dotenv==1.0.0
scikit-learn==1.3.0
corextopic==1.1
vaderSentiment==3.3.2
nltk==3.8.1
deep-translator==1.11.4
pandas==2.1.0
numpy==1.25.0
joblib==1.3.2
reportlab==4.0.0
apify-client==1.5.0
```
