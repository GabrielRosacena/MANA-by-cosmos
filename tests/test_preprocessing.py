import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app import app
from models import PreprocessedText, db
from preprocessing import preprocess_record, save_preprocessed_text


class RaisingTranslator:
    def translate(self, _text):
        raise RuntimeError("service unavailable")


class EchoTranslator:
    def translate(self, text):
        return text.replace("walang rescue team", "no rescue team").replace("walang", "no")


class PreprocessingPipelineTests(unittest.TestCase):
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

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_translation_fallback_keeps_clean_text_and_error(self):
        result = preprocess_record(
            raw_id="1",
            item={"text": "Walang rescue team"},
            record_type="post",
            translator=RaisingTranslator(),
        )
        self.assertEqual(result["clean_text"], "walang rescue team")
        self.assertEqual(result["translated_text"], "walang rescue team")
        self.assertEqual(result["translation_status"], "error")
        self.assertIn("Translation failed", result["error_message"])

    def test_negation_handling_preserves_context(self):
        result = preprocess_record(
            raw_id="2",
            item={"text": "not safe and no rescue"},
            record_type="post",
            translator=EchoTranslator(),
        )
        self.assertIn("not_safe", result["negation_handled_tokens"])
        self.assertIn("no_rescue", result["negation_handled_tokens"])
        self.assertIn("not_safe", result["final_tokens"])

    def test_lemmatization_reduces_disaster_terms(self):
        result = preprocess_record(
            raw_id="3",
            item={"text": "Flooding roads rescued families"},
            record_type="post",
            translator=EchoTranslator(),
        )
        self.assertIn("flood", result["lemmatized_tokens"])
        self.assertIn("road", result["lemmatized_tokens"])
        self.assertIn("rescue", result["lemmatized_tokens"])

    def test_bigram_detection_preserves_disaster_pairs(self):
        result = preprocess_record(
            raw_id="4",
            item={"text": "Flood water reached the evacuation center"},
            record_type="post",
            translator=EchoTranslator(),
        )
        self.assertIn("flood_water", result["bigrams"])
        self.assertIn("evacuation_center", result["bigrams"])
        self.assertIn("flood_water", result["final_tokens"])

    def test_stop_word_removal_keeps_negations(self):
        result = preprocess_record(
            raw_id="5",
            item={"text": "No rescue team in the area"},
            record_type="post",
            translator=EchoTranslator(),
        )
        self.assertIn("no_rescue", result["final_tokens"])
        self.assertNotIn("the", result["final_tokens"])
        self.assertNotIn("in", result["final_tokens"])

    def test_emotion_only_detection_for_comments(self):
        result = preprocess_record(
            raw_id="6",
            item={"text": "😭😭"},
            record_type="comment",
            parent_post_id="post-1",
            parent_context_text="flood water near evacuation center",
            translator=EchoTranslator(),
        )
        self.assertTrue(result["is_emotion_only"])
        self.assertTrue(result["is_relevant"])

    def test_relevance_filtering_marks_unrelated_comments(self):
        result = preprocess_record(
            raw_id="7",
            item={"text": "Nice haircut bro"},
            record_type="comment",
            translator=EchoTranslator(),
        )
        self.assertFalse(result["is_relevant"])

    def test_database_storage_preserves_original_and_new_outputs(self):
        row, processed = save_preprocessed_text(
            item={"text": "Walang rescue team sa barangay"},
            raw_id="8",
            record_type="comment",
            fallback_text="Walang rescue team sa barangay",
            parent_post_id="post-88",
            parent_context_text="rescue team requested in barangay",
            translator=EchoTranslator(),
        )
        db.session.add(row)
        db.session.commit()

        stored = PreprocessedText.query.filter_by(record_type="comment", raw_id="8").first()
        self.assertIsNotNone(stored)
        self.assertEqual(stored.raw_text, processed["raw_text"])
        self.assertEqual(stored.clean_text, processed["clean_text"])
        self.assertEqual(stored.translated_text, processed["translated_text"])
        self.assertEqual(stored.parent_post_id, "post-88")
        self.assertEqual(stored.preprocessing_stage, "finalized")
        self.assertEqual(stored.tokens, processed["tokens"])
        self.assertEqual(stored.negation_handled_tokens, processed["negation_handled_tokens"])
        self.assertEqual(stored.lemmatized_tokens, processed["lemmatized_tokens"])
        self.assertEqual(stored.bigrams, processed["bigrams"])
        self.assertEqual(stored.final_tokens, processed["final_tokens"])


if __name__ == "__main__":
    unittest.main()
