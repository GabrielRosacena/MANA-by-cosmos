"""
One-time script: build a Tagalog wordlist and save it to
backend/models/tagalog_wordlist.json.

Sources tried in order:
  1. tagalog.com/dictionary/  (palaganaskurl approach — blocked by 403 on most servers)
  2. Wiktionary API — Category:Tagalog_lemmas  (open API, no auth required)

Run once from the backend/ directory:
    pip install requests beautifulsoup4
    python scripts/build_tagalog_dict.py

The output file is committed to the repo and loaded at startup by preprocessing.py.
Re-run only when you want to refresh the wordlist.
"""
from __future__ import annotations

import json
import os
import sys
import time

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Missing dependencies. Run: pip install requests beautifulsoup4", file=sys.stderr)
    sys.exit(1)

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "tagalog_wordlist.json")

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

_WORD_SELECTORS = [
    "a.dictionary-word",
    "a.word",
    "td.word a",
    "div.dictionary-entry a",
    "li.word a",
]


# ── Source 1: tagalog.com ─────────────────────────────────────────────────────

def _scrape_tagalog_com() -> list[str]:
    base = "https://www.tagalog.com/dictionary/"
    all_words: set[str] = set()
    blocked = 0

    for letter in "abcdefghijklmnopqrstuvwxyz":
        url = f"{base}{letter}/"
        try:
            resp = requests.get(url, headers=BROWSER_HEADERS, timeout=15)
            if resp.status_code == 403:
                blocked += 1
                continue
            resp.raise_for_status()
        except requests.RequestException:
            blocked += 1
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        words = []
        for selector in _WORD_SELECTORS:
            items = soup.select(selector)
            if items:
                words = [a.get_text(strip=True).lower() for a in items if a.get_text(strip=True)]
                break
        all_words.update(words)
        print(f"  [{letter}] {len(words)} words")
        time.sleep(0.6)

    if blocked > 20:
        print("  tagalog.com blocked most requests — switching to Wiktionary.", file=sys.stderr)
        return []

    return sorted(all_words)


# ── Source 2: Wiktionary API ─────────────────────────────────────────────────

WIKTIONARY_API = "https://en.wiktionary.org/w/api.php"


def _fetch_wiktionary_tagalog() -> list[str]:
    """Fetch all Tagalog lemmas from Wiktionary's open API (paginated)."""
    words: set[str] = set()
    params: dict = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": "Category:Tagalog_lemmas",
        "cmlimit": "500",
        "cmnamespace": "0",
        "format": "json",
    }
    page = 0

    while True:
        try:
            resp = requests.get(WIKTIONARY_API, params=params, headers=BROWSER_HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            print(f"  Wiktionary request failed: {exc}", file=sys.stderr)
            break

        members = data.get("query", {}).get("categorymembers", [])
        for m in members:
            title = m.get("title", "").strip().lower()
            # Skip entries with spaces (multi-word phrases) or non-alpha chars
            if title and " " not in title and title.isalpha():
                words.add(title)

        page += 1
        print(f"  page {page}: {len(members)} entries (total so far: {len(words)})")

        cont = data.get("continue", {}).get("cmcontinue")
        if not cont:
            break
        params["cmcontinue"] = cont
        time.sleep(0.3)

    return sorted(words)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Trying tagalog.com ...")
    words = _scrape_tagalog_com()

    if len(words) < 500:
        print(f"\ntagalog.com returned only {len(words)} words. Trying Wiktionary API ...")
        wikt_words = _fetch_wiktionary_tagalog()
        # Merge both sources
        combined = sorted(set(words) | set(wikt_words))
        words = combined
        print(f"\nWiktionary: {len(wikt_words)} words")

    if len(words) < 100:
        print(
            "\nWARNING: Very few words scraped. Check network access or inspect the sources.",
            file=sys.stderr,
        )

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=2)

    sys.stdout.buffer.write(f"\nSaved {len(words)} words to {OUT_PATH}\n".encode("utf-8"))
    sys.stdout.buffer.write(b"Review the file, then commit it to the repo.\n")
