from __future__ import annotations

from typing import Iterable
from urllib.parse import parse_qs, urlparse, urlunparse


_AMBIGUOUS = object()
_FACEBOOK_HOST_ALIASES = {
    "facebook.com",
    "www.facebook.com",
    "m.facebook.com",
    "mbasic.facebook.com",
}


def normalize_facebook_url(url: str | None) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""

    parsed = urlparse(raw)
    host = parsed.netloc.lower()
    if host not in _FACEBOOK_HOST_ALIASES:
        return raw.rstrip("/")

    host = "facebook.com"
    path = parsed.path.rstrip("/") or "/"
    query = parse_qs(parsed.query or "", keep_blank_values=False)

    kept_pairs = []
    for key in ("story_fbid", "fbid", "id"):
        for value in query.get(key, []):
            value = value.strip()
            if value:
                kept_pairs.append(f"{key}={value}")

    normalized_query = "&".join(kept_pairs)
    return urlunparse(("https", host, path, "", normalized_query, ""))


def collect_post_match_keys(url: str | None = None, external_id: str | None = None) -> list[str]:
    keys = []
    seen = set()

    def push(prefix: str, value: str | None):
        value = (value or "").strip()
        if not value:
            return
        key = f"{prefix}:{value}"
        if key not in seen:
            seen.add(key)
            keys.append(key)

    normalized = normalize_facebook_url(url)
    if normalized:
        push("url", normalized)
        parsed = urlparse(normalized)
        segments = [segment for segment in parsed.path.split("/") if segment]
        query = parse_qs(parsed.query or "", keep_blank_values=False)

        for segment in segments:
            if segment.startswith("pfbid"):
                push("pfbid", segment)

        for marker in ("posts", "videos", "reel"):
            if marker in segments:
                idx = segments.index(marker)
                if idx + 1 < len(segments):
                    push("path-id", segments[idx + 1])

        for key in ("story_fbid", "fbid"):
            for value in query.get(key, []):
                push("fbid", value)

    push("external", str(external_id or ""))
    return keys


def build_post_match_index(posts: Iterable[object]) -> dict[str, object]:
    index: dict[str, object] = {}

    for post in posts:
        keys = collect_post_match_keys(
            url=getattr(post, "source_url", None),
            external_id=getattr(post, "external_id", None),
        )
        keys.extend(
            key
            for key in collect_post_match_keys(url=getattr(post, "account_url", None))
            if key not in keys
        )

        for key in keys:
            existing = index.get(key)
            if existing is None:
                index[key] = post
            elif existing is not post:
                index[key] = _AMBIGUOUS

    return index


def find_post_match(index: dict[str, object], url: str | None = None, external_id: str | None = None):
    for key in collect_post_match_keys(url=url, external_id=external_id):
        match = index.get(key)
        if match is not None and match is not _AMBIGUOUS:
            return match
    return None
