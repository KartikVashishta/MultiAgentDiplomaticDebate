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
            if "citations" in data:
                citations = [Citation.model_validate(c) for c in data["citations"]]
                return {
                    "text": data.get("text", ""),
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
    citations = []
    
    if not hasattr(response, 'output') or not response.output:
        return citations
    
    for item in response.output:
        if hasattr(item, 'type') and item.type == 'web_search_call':
            if hasattr(item, 'action') and hasattr(item.action, 'sources'):
                for src in item.action.sources:
                    url = getattr(src, 'url', '')
                    if url:
                        citations.append(Citation(
                            id=_citation_id_from_url(url),
                            title=getattr(src, 'title', 'Source'),
                            url=url,
                            snippet=getattr(src, 'snippet', '')[:500],
                            retrieved_at=now,
                            topic=topic,
                        ))
        elif hasattr(item, 'content'):
            for block in getattr(item, 'content', []):
                if hasattr(block, 'annotations'):
                    for ann in block.annotations:
                        ann_type = getattr(ann, 'type', '')
                        if ann_type != 'url_citation':
                            continue
                        url = getattr(ann, 'url', '')
                        if url:
                            citations.append(Citation(
                                id=_citation_id_from_url(url),
                                title=getattr(ann, 'title', 'Source'),
                                url=url,
                                snippet="",
                                retrieved_at=now,
                                topic=topic,
                            ))
    
    return citations


def _extract_text_from_response(response) -> str:
    text_content = ""
    if hasattr(response, 'output') and response.output:
        for item in response.output:
            if hasattr(item, 'content'):
                for block in getattr(item, 'content', []):
                    if hasattr(block, 'text'):
                        text_content += block.text + "\n"
    return text_content.strip()


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
    topic: str,
    allowed_domains: list[str] | None = None,
) -> tuple[str, list[Citation]]:
    if topic in ("economy", "GDP economy trade industries"):
        domains = allowed_domains or DEFAULT_ECONOMIC_DOMAINS
    elif topic in ("leaders", "government president prime minister leaders"):
        domains = allowed_domains or DEFAULT_GOVERNMENT_DOMAINS
    else:
        domains = allowed_domains
    
    query = f"{country_name} {topic} latest most recent official data"
    return web_search(
        query=query,
        max_results=5,
        allowed_domains=domains,
        topic=topic,
        use_cache=True,
    )
