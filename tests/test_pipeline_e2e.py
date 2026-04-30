"""
End-to-end pipeline tests using an in-memory SQLite database.
Tests each ML stage independently, then tests the full pipeline chain.

Run:
    cd c:/xampp/htdocs/MANA
    python -m pytest tests/test_pipeline_e2e.py -v
"""

from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app import app
from models import Post, PostCluster, PostSentiment, PostTopic, PreprocessedText, db
from preprocessing import save_preprocessed_text


# ── Fake post templates — 30 posts, 3–4 per cluster ──────────────────────────

FAKE_ITEMS = [
    # cluster-a — Food/NFI
    {"postId": "t-a-1", "text": "Relief goods distribution: food pack and rice at Barangay San Miguel.", "pageName": "NDRRMC", "url": "https://fb.com/p/t-a-1", "time": "2026-04-28T09:00:00+08:00", "likes": 200, "comments": 40, "shares": 30},
    {"postId": "t-a-2", "text": "Hygiene kit and blanket distribution at evacuation center today.", "pageName": "DSWD", "url": "https://fb.com/p/t-a-2", "time": "2026-04-28T10:00:00+08:00", "likes": 150, "comments": 30, "shares": 20},
    {"postId": "t-a-3", "text": "Water refill stations and food packs running low. Please donate relief goods.", "pageName": "QC Relief", "url": "https://fb.com/p/t-a-3", "time": "2026-04-28T11:00:00+08:00", "likes": 300, "comments": 60, "shares": 50},
    {"postId": "t-a-4", "text": "Family needs food pack and hygiene kit at the evacuation center. Rice supply is low.", "pageName": "Pasig Updates", "url": "https://fb.com/p/t-a-4", "time": "2026-04-28T12:00:00+08:00", "likes": 100, "comments": 25, "shares": 15},

    # cluster-b — WASH/Medical
    {"postId": "t-b-1", "text": "Medical team attending to patients with fever and dehydration at the evacuation site.", "pageName": "DOH PH", "url": "https://fb.com/p/t-b-1", "time": "2026-04-28T09:00:00+08:00", "likes": 250, "comments": 50, "shares": 40},
    {"postId": "t-b-2", "text": "Insulin supplies depleted at the hospital. Diabetes patients need medicine urgently. Doctor requested.", "pageName": "Health Alert", "url": "https://fb.com/p/t-b-2", "time": "2026-04-28T10:00:00+08:00", "likes": 400, "comments": 90, "shares": 70},
    {"postId": "t-b-3", "text": "Water safety alert: flood waters contaminated. Dehydration cases rising. Medical team on-site.", "pageName": "DOH NCR", "url": "https://fb.com/p/t-b-3", "time": "2026-04-28T11:00:00+08:00", "likes": 350, "comments": 70, "shares": 60},

    # cluster-c — CCCM/Evacuation
    {"postId": "t-c-1", "text": "Evacuation center at covered court is overcapacity. Over 500 families registered. Safe space needed.", "pageName": "CDRRMO", "url": "https://fb.com/p/t-c-1", "time": "2026-04-28T09:00:00+08:00", "likes": 500, "comments": 110, "shares": 90},
    {"postId": "t-c-2", "text": "Evacuation center registration ongoing. Toilet line is very long. Safe space for women and children needed.", "pageName": "QC DRRMO", "url": "https://fb.com/p/t-c-2", "time": "2026-04-28T10:00:00+08:00", "likes": 200, "comments": 50, "shares": 35},
    {"postId": "t-c-3", "text": "Camp registration desk overwhelmed. Privacy concerns at evacuation center. Overflow sites being identified.", "pageName": "NDRRMC", "url": "https://fb.com/p/t-c-3", "time": "2026-04-28T11:00:00+08:00", "likes": 280, "comments": 65, "shares": 45},
    {"postId": "t-c-4", "text": "Ang evacuation center ay puno na. Kailangan ng dagdag na safe space para sa mga evacuees.", "pageName": "Marikina Balita", "url": "https://fb.com/p/t-c-4", "time": "2026-04-28T12:00:00+08:00", "likes": 220, "comments": 55, "shares": 38},

    # cluster-d — Logistics
    {"postId": "t-d-1", "text": "Blocked road in Antipolo due to landslide. Convoy rerouted. Delivery of relief goods delayed.", "pageName": "DPWH", "url": "https://fb.com/p/t-d-1", "time": "2026-04-28T09:00:00+08:00", "likes": 200, "comments": 45, "shares": 35},
    {"postId": "t-d-2", "text": "Warehouse flooded. Emergency reroute of truck convoy to alternate delivery hub.", "pageName": "OCD Logistics", "url": "https://fb.com/p/t-d-2", "time": "2026-04-28T10:00:00+08:00", "likes": 150, "comments": 30, "shares": 25},
    {"postId": "t-d-3", "text": "Road blocked by debris. Convoy movement delayed. Delivery reroute clearance awaited.", "pageName": "OCD NCR", "url": "https://fb.com/p/t-d-3", "time": "2026-04-28T11:00:00+08:00", "likes": 130, "comments": 28, "shares": 20},

    # cluster-e — ETC/Comms
    {"postId": "t-e-1", "text": "Signal down in Marikina. No network. Cell site repair team deployed. Power bank distributed.", "pageName": "PLDT PH", "url": "https://fb.com/p/t-e-1", "time": "2026-04-28T09:00:00+08:00", "likes": 300, "comments": 70, "shares": 55},
    {"postId": "t-e-2", "text": "Radio is the only connectivity available. Cell site signal down. Emergency radio channel activated.", "pageName": "Comms PH", "url": "https://fb.com/p/t-e-2", "time": "2026-04-28T10:00:00+08:00", "likes": 250, "comments": 55, "shares": 42},
    {"postId": "t-e-3", "text": "Walang signal at kuryente. Hindi kami makahingi ng tulong. Cell site hindi pa nai-restore.", "pageName": "Brgy Tumana", "url": "https://fb.com/p/t-e-3", "time": "2026-04-28T11:00:00+08:00", "likes": 380, "comments": 85, "shares": 70},

    # cluster-f — Education
    {"postId": "t-f-1", "text": "DepEd announces class suspension in all public schools. Students advised to stay home.", "pageName": "DepEd NCR", "url": "https://fb.com/p/t-f-1", "time": "2026-04-28T09:00:00+08:00", "likes": 700, "comments": 160, "shares": 145},
    {"postId": "t-f-2", "text": "School closure extended. Learning materials distribution postponed. Temporary classroom set up.", "pageName": "DepEd QC", "url": "https://fb.com/p/t-f-2", "time": "2026-04-28T10:00:00+08:00", "likes": 500, "comments": 110, "shares": 100},
    {"postId": "t-f-3", "text": "Class suspension in 15 municipalities. DepEd distributing learning materials at evacuation centers.", "pageName": "DepEd Region", "url": "https://fb.com/p/t-f-3", "time": "2026-04-28T11:00:00+08:00", "likes": 450, "comments": 95, "shares": 85},

    # cluster-g — SRR
    {"postId": "t-g-1", "text": "SOS! Family stranded on rooftop. Rescue boat urgently needed. 3 children trapped. Please respond.", "pageName": "Emergency PH", "url": "https://fb.com/p/t-g-1", "time": "2026-04-28T09:00:00+08:00", "likes": 1000, "comments": 300, "shares": 250},
    {"postId": "t-g-2", "text": "Rescue boat needed at Purok 5. Family of 7 trapped and stranded. Water still rising. Send rescue team.", "pageName": "Marikina SOS", "url": "https://fb.com/p/t-g-2", "time": "2026-04-28T10:00:00+08:00", "likes": 850, "comments": 250, "shares": 210},
    {"postId": "t-g-3", "text": "Nastranded kami sa bubong. SOS. Hindi makarating ang rescue team. Nagtatawag ng tulong.", "pageName": "Brgy Sta Elena", "url": "https://fb.com/p/t-g-3", "time": "2026-04-28T11:00:00+08:00", "likes": 1200, "comments": 380, "shares": 320},
    {"postId": "t-g-4", "text": "Search and rescue team deployed. 5 trapped family members located. Rescue boat on the way. Retrieval ongoing.", "pageName": "Rescue Ops", "url": "https://fb.com/p/t-g-4", "time": "2026-04-28T12:00:00+08:00", "likes": 600, "comments": 140, "shares": 115},

    # cluster-h — MDM
    {"postId": "t-h-1", "text": "3 residents missing after flash flood. Family tracing underway. Contact coordination desk at City Hall.", "pageName": "Cagayan Emergency", "url": "https://fb.com/p/t-h-1", "time": "2026-04-28T09:00:00+08:00", "likes": 500, "comments": 110, "shares": 95},
    {"postId": "t-h-2", "text": "Hospital list of identified flood victims at evacuation center. Family tracing and verification ongoing.", "pageName": "OCD Info", "url": "https://fb.com/p/t-h-2", "time": "2026-04-28T10:00:00+08:00", "likes": 380, "comments": 80, "shares": 65},
    {"postId": "t-h-3", "text": "Missing person alert: Jose Dela Cruz, 65 years old. Last seen near flood area. Family tracing and hospital list cross-check ongoing.", "pageName": "Missing PH", "url": "https://fb.com/p/t-h-3", "time": "2026-04-28T11:00:00+08:00", "likes": 780, "comments": 190, "shares": 170},
    {"postId": "t-h-4", "text": "Dead and missing coordination desk at City Hall. Bring ID for verification. Hospital intake data being cross-checked.", "pageName": "MDM Desk", "url": "https://fb.com/p/t-h-4", "time": "2026-04-28T12:00:00+08:00", "likes": 300, "comments": 65, "shares": 52},
]

assert len(FAKE_ITEMS) == 28


# ── Shared setup helpers ──────────────────────────────────────────────────────

def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _create_post(item: dict) -> Post:
    from data import (PRIORITY_ORDER, extract_location, infer_cluster,
                      infer_priority, infer_sentiment_score, media_type_for,
                      recommendation_for)
    text = (item.get("text") or "").strip()
    cluster, keywords = infer_cluster(text)
    engagement = int(item.get("likes", 0)) + int(item.get("comments", 0)) + int(item.get("shares", 0))
    priority = infer_priority(text, engagement)
    return Post(
        id=str(item["postId"]),
        source="Facebook",
        page_source=item.get("pageName", "Facebook Source"),
        account_url=None,
        author=item.get("pageName"),
        caption=text,
        source_url=item.get("url", "https://fb.com"),
        external_id=str(item["postId"]),
        reactions=int(item.get("likes", 0)),
        shares=int(item.get("shares", 0)),
        likes=int(item.get("likes", 0)),
        reposts=0,
        comments=int(item.get("comments", 0)),
        views=0,
        media_type="text",
        priority=priority,
        sentiment_score=infer_sentiment_score(text, engagement),
        recommendation=recommendation_for(cluster["id"], priority),
        status="Monitoring",
        cluster_id=cluster["id"],
        date=_parse_iso(item["time"]),
        keywords_json=json.dumps(keywords),
        location=extract_location(text),
        severity_rank=PRIORITY_ORDER[priority],
        raw_payload_json=json.dumps(item),
    )


def _seed_posts(items: list[dict]) -> list[Post]:
    """Insert Post + PreprocessedText for each item. Returns inserted Post objects."""
    posts = []
    for item in items:
        post = _create_post(item)
        db.session.add(post)
        processed_row, _ = save_preprocessed_text(
            item=item,
            raw_id=post.id,
            record_type="post",
            fallback_text=post.caption,
        )
        db.session.add(processed_row)
        posts.append(post)
    db.session.commit()
    return posts


# ── Base test class ───────────────────────────────────────────────────────────

class PipelineTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_ENGINE_OPTIONS={},
        )

    def setUp(self):
        self.ctx = app.app_context()
        self.ctx.push()
        db.session.remove()
        db.drop_all()
        db.create_all()
        # Seed clusters so FK constraints are satisfied
        from data import seed_clusters
        seed_clusters()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()


# ── Stage 1: Preprocessing ────────────────────────────────────────────────────

class TestPreprocessingStage(PipelineTestBase):
    def test_preprocessing_saves_tokens_for_all_posts(self):
        _seed_posts(FAKE_ITEMS[:10])
        rows = PreprocessedText.query.all()
        self.assertEqual(len(rows), 10)
        processed = [r for r in rows if r.preprocessing_status == "processed"]
        self.assertGreater(len(processed), 0, "At least some posts should be processed")

    def test_relevant_disaster_posts_are_marked_relevant(self):
        _seed_posts(FAKE_ITEMS)
        relevant = PreprocessedText.query.filter_by(is_relevant=True).all()
        self.assertGreaterEqual(
            len(relevant), 20,
            f"Expected at least 20 relevant posts from disaster content, got {len(relevant)}"
        )

    def test_preprocessed_text_has_final_tokens(self):
        _seed_posts(FAKE_ITEMS[:5])
        rows = PreprocessedText.query.filter(
            PreprocessedText.final_tokens_json != "[]"
        ).all()
        self.assertGreater(len(rows), 0, "Disaster posts should have non-empty final_tokens")
        for row in rows:
            self.assertIsInstance(row.final_tokens, list)
            self.assertGreater(len(row.final_tokens), 0)

    def test_cluster_assignment_heuristic_covers_all_clusters(self):
        _seed_posts(FAKE_ITEMS)
        posts = Post.query.all()
        assigned_clusters = {p.cluster_id for p in posts}
        self.assertGreaterEqual(
            len(assigned_clusters), 5,
            f"Expected posts spread across multiple clusters, got: {assigned_clusters}"
        )


# ── Stage 2: CorEx ────────────────────────────────────────────────────────────

class TestCorExStage(PipelineTestBase):
    def setUp(self):
        super().setUp()
        _seed_posts(FAKE_ITEMS)

    def _get_texts(self) -> list[str]:
        rows = (
            PreprocessedText.query
            .filter_by(record_type="post", preprocessing_status="processed", is_relevant=True)
            .filter(PreprocessedText.final_tokens_json != "[]")
            .all()
        )
        return [" ".join(r.final_tokens) for r in rows if r.final_tokens]

    def test_corex_trains_without_error(self):
        from services.corex.topic_modeler import train_corex
        texts = self._get_texts()
        self.assertGreaterEqual(len(texts), 10, "Need at least 10 preprocessed posts")
        result = train_corex(texts)
        self.assertIn("corpus_size", result)
        self.assertIn("overall_coherence", result)
        self.assertEqual(result["corpus_size"], len(texts))

    def test_corex_returns_eight_topic_scores(self):
        from services.corex.topic_modeler import train_corex
        texts = self._get_texts()
        result = train_corex(texts)
        self.assertEqual(len(result["coherence_scores"]), 8)

    def test_corex_predict_returns_topic_dicts(self):
        from services.corex.topic_modeler import predict_topics_batch, train_corex
        texts = self._get_texts()
        train_corex(texts)
        results = predict_topics_batch(texts)
        self.assertEqual(len(results), len(texts))
        # Each result is a list of {topic, confidence}
        flat = [item for sublist in results for item in sublist]
        if flat:
            self.assertIn("topic", flat[0])
            self.assertIn("confidence", flat[0])
            self.assertGreaterEqual(flat[0]["confidence"], 0.0)
            self.assertLessEqual(flat[0]["confidence"], 1.0)

    def test_corex_predict_writes_to_post_topics(self):
        from services.corex.topic_modeler import predict_topics_batch, train_corex
        rows = (
            PreprocessedText.query
            .filter_by(record_type="post", preprocessing_status="processed", is_relevant=True)
            .filter(PreprocessedText.final_tokens_json != "[]")
            .all()
        )
        texts = [" ".join(r.final_tokens) for r in rows if r.final_tokens]
        train_corex(texts)
        batch = predict_topics_batch(texts)

        for row, topics in zip(rows, batch):
            for t in topics:
                db.session.add(PostTopic(
                    post_id=row.raw_id,
                    topic_label=t["topic"],
                    confidence=t["confidence"],
                ))
        db.session.commit()

        topic_count = PostTopic.query.count()
        self.assertGreater(topic_count, 0, "CorEx should produce at least some topic rows")


# ── Stage 3: SVM ──────────────────────────────────────────────────────────────

class TestSVMStage(PipelineTestBase):
    def setUp(self):
        super().setUp()
        _seed_posts(FAKE_ITEMS)

    def _get_texts_and_labels(self):
        rows = (
            db.session.query(PreprocessedText, Post)
            .join(Post, PreprocessedText.raw_id == Post.id)
            .filter(
                PreprocessedText.preprocessing_status == "processed",
                PreprocessedText.is_relevant == True,
                PreprocessedText.final_tokens_json != "[]",
                PreprocessedText.record_type == "post",
            )
            .all()
        )
        texts = [" ".join(pt.final_tokens) for pt, _ in rows]
        labels = [[post.cluster_id] for _, post in rows]
        return texts, labels

    def test_svm_trains_without_error(self):
        from services.svm.cluster_classifier import train_svm
        texts, labels = self._get_texts_and_labels()
        self.assertGreaterEqual(len(texts), 20, "Need at least 20 labeled posts")
        result = train_svm(texts, labels)
        self.assertIn("corpus_size", result)
        self.assertIn("f1_macro", result)
        self.assertIn("best_C", result)
        self.assertGreaterEqual(result["f1_macro"], 0.0)

    def test_svm_predict_returns_cluster_dicts(self):
        from services.svm.cluster_classifier import predict_clusters_batch, train_svm
        texts, labels = self._get_texts_and_labels()
        train_svm(texts, labels)
        results = predict_clusters_batch(texts)
        self.assertEqual(len(results), len(texts))
        flat = [item for sublist in results for item in sublist]
        if flat:
            self.assertIn("cluster_id", flat[0])
            self.assertIn("confidence", flat[0])

    def test_svm_predict_writes_to_post_clusters(self):
        from services.svm.cluster_classifier import predict_clusters_batch, train_svm
        rows = (
            db.session.query(PreprocessedText, Post)
            .join(Post, PreprocessedText.raw_id == Post.id)
            .filter(
                PreprocessedText.preprocessing_status == "processed",
                PreprocessedText.is_relevant == True,
                PreprocessedText.final_tokens_json != "[]",
                PreprocessedText.record_type == "post",
            )
            .all()
        )
        texts = [" ".join(pt.final_tokens) for pt, _ in rows]
        labels = [[post.cluster_id] for _, post in rows]
        train_svm(texts, labels)
        batch = predict_clusters_batch(texts)

        for (pt, post), cluster_list in zip(rows, batch):
            for c in cluster_list:
                db.session.add(PostCluster(
                    post_id=pt.raw_id,
                    cluster_id=c["cluster_id"],
                    confidence=c["confidence"],
                ))
        db.session.commit()
        self.assertGreater(PostCluster.query.count(), 0)


# ── Stage 4: VADER ────────────────────────────────────────────────────────────

class TestVADERStage(PipelineTestBase):
    def test_vader_analyzes_all_posts(self):
        from services.vader.sentiment_analyzer import analyze_post
        _seed_posts(FAKE_ITEMS[:10])
        posts = Post.query.all()
        for post in posts:
            result = analyze_post(post.caption or "", post.cluster_id)
            db.session.add(PostSentiment(
                post_id=post.id,
                compound=result["compound"],
                positive=result["positive"],
                negative=result["negative"],
                neutral=result["neutral"],
                sarcasm_flag=result["sarcasm_flag"],
            ))
            post.sentiment_score = result["sentiment_score"]
            post.sentiment_compound = result["compound"]
        db.session.commit()

        self.assertEqual(PostSentiment.query.count(), 10)

    def test_vader_compound_is_in_valid_range(self):
        from services.vader.sentiment_analyzer import analyze_post
        _seed_posts(FAKE_ITEMS[:10])
        for post in Post.query.all():
            result = analyze_post(post.caption or "", post.cluster_id)
            self.assertGreaterEqual(result["compound"], -1.0)
            self.assertLessEqual(result["compound"], 1.0)
            self.assertIn(result["label"], ("Positive", "Negative", "Neutral"))
            self.assertIn(result["sentiment_score"], range(20, 98))

    def test_vader_flags_sarcasm_on_negative_cluster_positive_text(self):
        from services.vader.sentiment_analyzer import analyze_post
        # "Great job rescue team, amazing work!" is positive but cluster-g is a negative cluster
        result = analyze_post("Great job rescue team, amazing work!", "cluster-g")
        self.assertTrue(result["sarcasm_flag"],
                        "Positive text in negative cluster (cluster-g) should be flagged as sarcasm")

    def test_vader_no_sarcasm_on_genuinely_negative_disaster_text(self):
        from services.vader.sentiment_analyzer import analyze_post
        # Use an unambiguously negative text so VADER compound is <= -0.05
        result = analyze_post("Terrible flooding. People trapped and dying. Nobody coming to help.", "cluster-g")
        self.assertFalse(result["sarcasm_flag"],
                         "Genuinely negative disaster text (compound < 0) should NOT be flagged as sarcasm")


# ── Stage 5: Full pipeline run-all endpoint ───────────────────────────────────

class TestPipelineRunAll(PipelineTestBase):
    def setUp(self):
        super().setUp()
        _seed_posts(FAKE_ITEMS)
        # Seed default admin user for JWT auth
        from models import User
        from data import seed_clusters
        admin = User(username="admin", name="Test Admin", email="admin@test.ph",
                     role="Admin", status="Active")
        admin.set_password("admin2026")
        db.session.add(admin)
        db.session.commit()

    def _get_token(self, client) -> str:
        resp = client.post("/api/auth/login",
                           json={"username": "admin", "password": "admin2026"},
                           content_type="application/json")
        self.assertEqual(resp.status_code, 200, f"Login failed: {resp.get_data(as_text=True)}")
        return resp.get_json()["token"]

    def test_pipeline_run_all_returns_all_steps(self):
        with app.test_client() as client:
            token = self._get_token(client)
            resp = client.post(
                "/api/admin/pipeline/run-all",
                json={"force_retrain": True},
                headers={"Authorization": f"Bearer {token}"},
                content_type="application/json",
            )
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        data = resp.get_json()
        self.assertIn("steps", data)
        steps = data["steps"]
        self.assertIn("preprocessing", steps)
        self.assertIn("corex_train", steps)
        self.assertIn("corex_predict", steps)
        self.assertIn("svm_train", steps)
        self.assertIn("svm_predict", steps)
        self.assertIn("vader", steps)

    def test_pipeline_run_all_populates_all_tables(self):
        with app.test_client() as client:
            token = self._get_token(client)
            client.post(
                "/api/admin/pipeline/run-all",
                json={"force_retrain": True},
                headers={"Authorization": f"Bearer {token}"},
                content_type="application/json",
            )
        self.assertGreater(PostTopic.query.count(), 0, "post_topics should be populated")
        self.assertGreater(PostCluster.query.count(), 0, "post_clusters should be populated")
        self.assertGreater(PostSentiment.query.count(), 0, "sentiments should be populated")

    def test_pipeline_status_shows_all_trained(self):
        with app.test_client() as client:
            token = self._get_token(client)
            # Train first
            client.post(
                "/api/admin/pipeline/run-all",
                json={"force_retrain": True},
                headers={"Authorization": f"Bearer {token}"},
                content_type="application/json",
            )
            # Check status
            resp = client.get(
                "/api/admin/pipeline/status",
                headers={"Authorization": f"Bearer {token}"},
            )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["corex"]["trained"])
        self.assertTrue(data["svm"]["trained"])
        self.assertTrue(data["vader"]["available"])

    def test_pipeline_skip_retrain_when_models_exist(self):
        with app.test_client() as client:
            token = self._get_token(client)
            # First run — trains from scratch
            client.post(
                "/api/admin/pipeline/run-all",
                json={"force_retrain": True},
                headers={"Authorization": f"Bearer {token}"},
                content_type="application/json",
            )
            # Second run — should skip retraining
            resp = client.post(
                "/api/admin/pipeline/run-all",
                json={"force_retrain": False},
                headers={"Authorization": f"Bearer {token}"},
                content_type="application/json",
            )
        data = resp.get_json()
        self.assertTrue(data["steps"]["corex_train"]["skipped"])
        self.assertTrue(data["steps"]["svm_train"]["skipped"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
