import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI

from madd.core.config import get_settings
from madd.core.schemas import Citation

logger = logging.getLogger(__name__)

DEFAULT_ECONOMIC_DOMAINS = [
    "worldbank.org",
    "imf.org",
    "un.org",
    "oecd.org",
    "cia.gov",
    "data.gov",
    "statista.com",
]

DEFAULT_GOVERNMENT_DOMAINS = [
    "gov.uk",
    "state.gov",
    "europa.eu",
    "foreignaffairs.gov",
]


def _citation_id_from_url(url: str) -> str:
    return f"cite_{hashlib.sha256(url.encode()).hexdigest()[:10]}"


def _cache_key(query: str, allowed_domains: list[str] | None, user_location: str | None = None) -> str:
    parts = [query, str(sorted(allowed_domains) if allowed_domains else ""), user_location or ""]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _load_cache(cache_key: str, max_results: int) -> dict | None:
    settings = get_settings()
    if not settings.search_cache_enabled:
        return None
    cache_path = Path(settings.search_cache_dir) / f"{cache_key}.json"
    if cache_path.exists():
        try:
            with open(cache_path) as f:
                data = json.load(f)
                c_raw = data.get("citations") or []
                if not isinstance(c_raw, list):
                    c_raw = []
                citations = [Citation.model_validate(c) for c in c_raw if c]
                return {
                    "text": data.get("text", "") or "",
                    "citations": citations[:max_results],
                }
        except Exception:
            return None
    return None


def _save_cache(cache_key: str, text: str, citations: list[Citation]) -> None:
    settings = get_settings()
    if not settings.search_cache_enabled:
        return
    cache_dir = Path(settings.search_cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{cache_key}.json"
    with open(cache_path, "w") as f:
        json.dump({
            "text": text,
            "citations": [c.model_dump(mode="json") for c in citations],
        }, f)


def _parse_sources_from_response(response, topic: str | None, now: datetime) -> list[Citation]:
    citations: list[Citation] = []

    output_items = getattr(response, "output", None) or []
    for item in output_items:
        if getattr(item, "type", "") == "web_search_call":
            action = getattr(item, "action", None)
            sources = getattr(action, "sources", None) or []
            for src in sources:
                if isinstance(src, dict):
                    url = src.get("url") or ""
                    title = src.get("title") or "Source"
                    snippet = src.get("snippet") or ""
                else:
                    url = getattr(src, "url", "") or ""
                    title = getattr(src, "title", "") or "Source"
                    snippet = getattr(src, "snippet", "") or ""
                if url:
                    citations.append(
                        Citation(
                            id=_citation_id_from_url(url),
                            title=title,
                            url=url,
                            snippet=snippet[:500],
                            retrieved_at=now,
                            topic=topic,
                        )
                    )
            continue

        for block in (getattr(item, "content", None) or []):
            for ann in (getattr(block, "annotations", None) or []):
                ann_type = ann.get("type", "") if isinstance(ann, dict) else getattr(ann, "type", "")
                if ann_type != "url_citation":
                    continue
                if isinstance(ann, dict):
                    url = ann.get("url") or ""
                    title = ann.get("title") or "Source"
                else:
                    url = getattr(ann, "url", "") or ""
                    title = getattr(ann, "title", "") or "Source"
                if url:
                    citations.append(
                        Citation(
                            id=_citation_id_from_url(url),
                            title=title,
                            url=url,
                            snippet="",
                            retrieved_at=now,
                            topic=topic,
                        )
                    )

    return citations


def _extract_text_from_response(response) -> str:
    """Extract text from OpenAI response.
    
    Uses the canonical SDK accessor response.output_text (avoids iterating
    output items where content can be None). Falls back to manual extraction
    for older response shapes.
    """
    text = getattr(response, "output_text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()
    chunks: list[str] = []
    for item in (getattr(response, "output", None) or []):
        for block in (getattr(item, "content", None) or []):
            t = getattr(block, "text", None)
            if isinstance(t, str) and t:
                chunks.append(t)
    return "\n".join(chunks).strip()


def _synthesize_text_from_citations(citations: list[Citation]) -> str:
    if not citations:
        return ""
    return "\n".join(f"- {c.title}: {c.snippet}" for c in citations if c.snippet)


def web_search(
    query: str,
    max_results: int = 5,
    allowed_domains: list[str] | None = None,
    user_location: str | None = None,
    topic: str | None = None,
    use_cache: bool = True,
) -> tuple[str, list[Citation]]:
    cache_key = _cache_key(query, allowed_domains, user_location)
    
    if use_cache:
        cached = _load_cache(cache_key, max_results)
        if cached:
            text = cached["text"]
            citations = cached["citations"]
            if not text and citations:
                text = _synthesize_text_from_citations(citations)
            logger.debug(f"Cache hit for query: {query[:50]}...")
            return text, citations
    
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)
    
    tool_config: dict = {"type": "web_search"}
    if allowed_domains:
        tool_config["filters"] = {"allowed_domains": allowed_domains}
    if user_location:
        tool_config["user_location"] = {"type": "approximate", "country": user_location}
    
    try:
        response = client.responses.create(
            model=settings.search_model,
            tools=[tool_config],
            input=query,
            include=["web_search_call.action.sources"],
        )
    except Exception as e:
        logger.warning(f"Web search failed: {e}")
        return "", []
    
    now = datetime.now(timezone.utc)
    citations = _parse_sources_from_response(response, topic, now)
    text_content = _extract_text_from_response(response)
    
    seen_urls = set()
    unique = []
    for c in citations:
        if c.url and c.url not in seen_urls:
            seen_urls.add(c.url)
            unique.append(c)
    
    if use_cache and unique:
        _save_cache(cache_key, text_content, unique)
    
    return text_content, unique[:max_results]


def search_country_info(
    country_name: str,
    topic_key: str,
    query_hint: str | None = None,
    allowed_domains: list[str] | None = None,
) -> tuple[str, list[Citation]]:
    """Search for country information with domain filtering by topic.
    
    Args:
        country_name: Name of the country to search for.
        topic_key: Short topic identifier (e.g. "economy", "leaders") for domain selection.
        query_hint: Optional expanded query terms (defaults to topic_key if not provided).
        allowed_domains: Optional override for allowed domains.
    
    Returns:
        Tuple of (text_content, citations).
    """
    if topic_key == "economy":
        domains = allowed_domains or DEFAULT_ECONOMIC_DOMAINS
    elif topic_key == "leaders":
        domains = allowed_domains or DEFAULT_GOVERNMENT_DOMAINS
    else:
        domains = allowed_domains

    hint = query_hint or topic_key
    query = f"{country_name} {hint} latest most recent official data"
    return web_search(
        query=query,
        max_results=5,
        allowed_domains=domains,
        topic=topic_key,
        use_cache=True,
    )
