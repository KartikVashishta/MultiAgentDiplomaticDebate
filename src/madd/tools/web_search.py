import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from openai import OpenAI

from madd.core.config import get_settings
from madd.core.schemas import Citation

logger = logging.getLogger(__name__)

DEFAULT_LAW_DOMAINS = ["un.org", "icj-cij.org", "itlos.org", "pca-cpa.org"]
DEFAULT_SECURITY_DOMAINS = ["nato.int", "state.gov", "defense.gov", "gov.uk", "europa.eu", "un.org"]
DEFAULT_ECON_DOMAINS = ["worldbank.org", "imf.org", "oecd.org", "data.worldbank.org"]
DEFAULT_ENV_DOMAINS = ["unep.org", "ipcc.ch", "un.org"]
DEFAULT_RIGHTS_DOMAINS = ["ohchr.org", "ilo.org", "un.org", "icrc.org"]

DEFAULT_ECONOMIC_DOMAINS = DEFAULT_ECON_DOMAINS


def _citation_id_from_url(url: str) -> str:
    return f"cite_{hashlib.sha256(url.encode()).hexdigest()[:10]}"


def _pick(obj, keys: list[str]) -> str:
    if isinstance(obj, dict):
        for key in keys:
            val = obj.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        return ""
    for key in keys:
        val = getattr(obj, key, None)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def _title_from_url(url: str) -> str:
    if not url:
        return "Source"
    host = urlparse(url).netloc
    return host or "Source"


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
    fallback_text = _extract_text_from_response(response)

    output_items = getattr(response, "output", None) or []
    for item in output_items:
        if getattr(item, "type", "") == "web_search_call":
            action = getattr(item, "action", None)
            sources = getattr(action, "sources", None) or []
            for src in sources:
                url = _pick(src, ["url", "link", "href"])
                title = _pick(src, ["title", "name", "source", "site", "site_name", "publisher"])
                snippet = _pick(src, ["snippet", "summary", "description", "text", "content", "excerpt"])
                if not title:
                    title = _title_from_url(url)
                if not snippet and fallback_text:
                    snippet = fallback_text[:300]
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
            annotations = getattr(block, "annotations", None) or []
            for ann in annotations:
                ann_type = ann.get("type", "") if isinstance(ann, dict) else getattr(ann, "type", "")
                if ann_type != "url_citation":
                    continue
                url = _pick(ann, ["url", "link", "href"])
                title = _pick(ann, ["title", "name", "source", "site", "site_name", "publisher"])
                if not title:
                    title = _title_from_url(url)
                snippet = ""
                if fallback_text:
                    snippet = fallback_text[:300]
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
    scenario_context: str | None = None,
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
    topic_domains = {
        "economy": DEFAULT_ECON_DOMAINS,
        "leaders": DEFAULT_SECURITY_DOMAINS,
        "alliances": DEFAULT_SECURITY_DOMAINS,
        "history": DEFAULT_SECURITY_DOMAINS,
        "law": DEFAULT_LAW_DOMAINS,
        "environment": DEFAULT_ENV_DOMAINS,
        "human_rights": DEFAULT_RIGHTS_DOMAINS,
        "defense_posture": DEFAULT_SECURITY_DOMAINS,
        "confidence_building": DEFAULT_SECURITY_DOMAINS,
        "incident_history": DEFAULT_SECURITY_DOMAINS,
        "defense_agreements": DEFAULT_SECURITY_DOMAINS,
        "border_law": DEFAULT_LAW_DOMAINS,
        "treaty_law": DEFAULT_LAW_DOMAINS,
        "mining_law": DEFAULT_ECON_DOMAINS,
        "critical_minerals": DEFAULT_ECON_DOMAINS,
        "supply_chain": DEFAULT_ECON_DOMAINS,
        "esg": DEFAULT_ECON_DOMAINS,
        "trade_policy": DEFAULT_ECON_DOMAINS,
        "sanctions": DEFAULT_ECON_DOMAINS,
        "investment_screening": DEFAULT_ECON_DOMAINS,
        "monitoring": DEFAULT_ENV_DOMAINS,
        "grievance": DEFAULT_RIGHTS_DOMAINS,
        "cyber_policy": DEFAULT_SECURITY_DOMAINS,
        "technology_transfer": DEFAULT_ECON_DOMAINS,
        "water_sharing": DEFAULT_LAW_DOMAINS,
        "energy_grid": DEFAULT_ECON_DOMAINS,
        "food_security": DEFAULT_ECON_DOMAINS,
    }
    domains = allowed_domains or topic_domains.get(topic_key)

    hint = query_hint or topic_key
    prefix = f"{scenario_context} " if scenario_context else ""
    query = f"{prefix}{country_name} {hint} latest most recent official data"
    return web_search(
        query=query,
        max_results=5,
        allowed_domains=domains,
        topic=topic_key,
        use_cache=True,
    )
