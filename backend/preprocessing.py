"""
Text preprocessing helpers for imported Apify records.
"""

from __future__ import annotations

import re
from html import unescape

from models import PreprocessedText

TEXT_FIELDS = ("text", "caption", "content", "comment", "message", "postText", "body")
URL_RE = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)
MENTION_RE = re.compile(r"(?<!\w)@([A-Za-z0-9_]+)")
HTML_TAG_RE = re.compile(r"<[^>]+>")
HASHTAG_RE = re.compile(r"#([A-Za-z0-9_]+)")
NON_WORD_RE = re.compile(r"[^a-z0-9\s]")
WHITESPACE_RE = re.compile(r"\s+")


def extract_raw_text(item: dict, fallback_text: str | None = None):
    for field in TEXT_FIELDS:
        value = item.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip(), field
    if isinstance(fallback_text, str) and fallback_text.strip():
        return fallback_text.strip(), "fallback"
    return None, None


def clean_text(text: str):
    value = unescape(text or "")
    value = HTML_TAG_RE.sub(" ", value)
    value = URL_RE.sub(" ", value)
    value = MENTION_RE.sub(" ", value)
    value = HASHTAG_RE.sub(r" \1 ", value)
    value = value.lower()
    value = NON_WORD_RE.sub(" ", value)
    value = WHITESPACE_RE.sub(" ", value).strip()
    return value


def tokenize_text(cleaned_text: str):
    if not cleaned_text:
        return []
    return [token for token in cleaned_text.split(" ") if token]


def preprocess_record(raw_id: str, item: dict, record_type: str, fallback_text: str | None = None):
    result = {
        "raw_id": str(raw_id or ""),
        "raw_text": None,
        "clean_text": None,
        "tokens": [],
        "preprocessing_status": "processed",
        "error_message": None,
    }

    try:
        raw_text, _field = extract_raw_text(item or {}, fallback_text=fallback_text)
        if not raw_text:
            result["preprocessing_status"] = "skipped"
            result["error_message"] = "No usable text field found in source record."
            return result

        cleaned = clean_text(raw_text)
        tokens = tokenize_text(cleaned)
        if not cleaned:
            result["preprocessing_status"] = "skipped"
            result["raw_text"] = raw_text
            result["clean_text"] = ""
            result["tokens"] = []
            result["error_message"] = "Text became empty after preprocessing."
            return result

        result["raw_text"] = raw_text
        result["clean_text"] = cleaned
        result["tokens"] = tokens
        return result
    except Exception as exc:
        result["preprocessing_status"] = "error"
        result["error_message"] = str(exc)
        return result


def save_preprocessed_text(item: dict, raw_id: str, record_type: str, fallback_text: str | None = None):
    processed = preprocess_record(raw_id=raw_id, item=item, record_type=record_type, fallback_text=fallback_text)
    row = PreprocessedText.query.filter_by(record_type=record_type, raw_id=processed["raw_id"]).first()
    if not row:
        row = PreprocessedText(record_type=record_type, raw_id=processed["raw_id"])

    row.raw_text = processed["raw_text"]
    row.clean_text = processed["clean_text"]
    row.set_tokens(processed["tokens"])
    row.preprocessing_status = processed["preprocessing_status"]
    row.error_message = processed["error_message"]
    return row, processed
