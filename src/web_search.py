from __future__ import annotations

import logging
import time
import re
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

_WIKI_API = "https://en.wikipedia.org/w/api.php"
_BING_URL = "https://www.bing.com/search?q={q}&count=10"
_LAST_REQ = 0.0


def _throttle(seconds: float = 1.5):
    global _LAST_REQ
    elapsed = time.time() - _LAST_REQ
    if elapsed < seconds:
        time.sleep(seconds - elapsed)


def _get(url: str, timeout: int = 10) -> requests.Response | None:
    global _LAST_REQ
    _throttle()
    try:
        r = requests.get(url, headers=_HEADERS, timeout=timeout)
        r.raise_for_status()
        _LAST_REQ = time.time()
        return r
    except Exception as exc:
        logger.warning("GET %s failed: %s", url[:80], exc)
        _LAST_REQ = time.time()
        return None


def _wiki_opensearch(query: str, limit: int = 5) -> list[dict]:
    """Use opensearch API (lighter, gives direct title matches)."""
    params = {
        "action": "opensearch",
        "search": query,
        "limit": limit,
        "namespace": 0,
        "format": "json",
    }
    _throttle(2.0)
    try:
        r = requests.get(_WIKI_API, params=params, headers=_HEADERS, timeout=10)
        r.raise_for_status()
        _LAST_REQ = time.time()
        data = r.json()
    except Exception as exc:
        logger.warning("Wikipedia opensearch error: %s", exc)
        _LAST_REQ = time.time()
        return []
    if not data or len(data) < 4:
        return []
    titles, descs, urls = data[1], data[2], data[3]
    results = []
    for title, desc, url in zip(titles, descs, urls):
        results.append({"title": title, "snippet": desc, "url": url})
    return results


def _wiki_search_api(query: str, limit: int = 5) -> list[dict]:
    """Use search API."""
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": limit,
        "format": "json",
    }
    data = _rate_limited_api(params)
    if not data:
        return []
    results = []
    for item in data.get("query", {}).get("search", []):
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        clean = BeautifulSoup(snippet, "html.parser").get_text() if snippet else ""
        url = f"https://en.wikipedia.org/wiki/{quote_plus(title.replace(' ', '_'))}"
        results.append({"title": title, "snippet": clean, "url": url})
    return results


def _rate_limited_api(params: dict, timeout: int = 10) -> dict | None:
    """Wikipedia API call with rate limiting."""
    _throttle(2.0)
    try:
        r = requests.get(_WIKI_API, params=params, headers=_HEADERS, timeout=timeout)
        r.raise_for_status()
        _LAST_REQ = time.time()
        return r.json()
    except requests.exceptions.HTTPError as exc:
        if exc.response.status_code == 429:
            logger.warning("Wikipedia 429, waiting 15s...")
            time.sleep(15)
            _LAST_REQ = time.time()
        else:
            _LAST_REQ = time.time()
        return None
    except Exception as exc:
        logger.warning("Wikipedia API error: %s", exc)
        _LAST_REQ = time.time()
        return None


def _search_bing(query: str, max_results: int = 5) -> list[dict]:
    resp = _get(_BING_URL.format(q=quote_plus(query)))
    if not resp:
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    for li in soup.select("li.b_algo"):
        h2 = li.select_one("h2")
        a = h2.select_one("a") if h2 else None
        title = a.get_text(strip=True) if a else ""
        href = a.get("href", "") if a else ""
        snippet_el = li.select_one(".b_caption p")
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
        if title:
            results.append({"title": title, "snippet": snippet, "url": href})
        if len(results) >= max_results:
            break
    return results


def _clean_query(query: str) -> str:
    stop_words = {
        "give", "tell", "what", "about", "review", "show", "find", "search",
        "need", "want", "please", "can", "you", "do", "does", "is", "are",
        "the", "a", "an", "some",
    }
    words = [w for w in query.split() if w.lower() not in stop_words]
    return " ".join(words) if words else query


def search_web(query: str, max_results: int = 5) -> list[dict]:
    cleaned = _clean_query(query)
    base = cleaned or query
    # Build query variants
    variants = [base]
    if query != base:
        variants.append(query)
    # Add year for media topics
    if any(w in base.lower() for w in ("movie", "film", "peddi")):
        for year in ("2026", "2025"):
            if year not in base:
                variants.append(f"{base} {year}")

    # Strategy 1: Wikipedia search API (best for finding articles by topic)
    for v in variants:
        results = _wiki_search_api(v, limit=5)
        if results:
            return results[:max_results]

    # Strategy 2: Wikipedia opensearch (fast prefix match)
    for v in variants:
        results = _wiki_opensearch(v, limit=5)
        if results:
            return results[:max_results]

    # Strategy 3: Bing fallback
    for v in variants:
        results = _search_bing(v, max_results)
        if results:
            return results

    return []


def format_search_results(results: list[dict]) -> str:
    if not results:
        return ""
    lines = ["Web search results:"]
    for i, r in enumerate(results, 1):
        title = r.get("title", "")
        snippet = r.get("snippet", "")
        url = r.get("url", "")
        lines.append(f"{i}. {title}")
        if snippet:
            clean = snippet[:600].replace("\n", " ").encode("ascii", "ignore").decode("ascii")
            lines.append(f"   {clean}")
        if url:
            lines.append(f"   Source: {url}")
    return "\n".join(lines)
