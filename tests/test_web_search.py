import pytest
import hashlib
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from madd.core.schemas import Citation
from madd.tools.web_search import (
    web_search, _cache_key, _citation_id_from_url, _parse_sources_from_response,
    _synthesize_text_from_citations, DEFAULT_ECONOMIC_DOMAINS,
)


def test_citation_id_deterministic():
    url = "https://example.com/page"
    id1 = _citation_id_from_url(url)
    id2 = _citation_id_from_url(url)
    assert id1 == id2
    assert id1.startswith("cite_")
    assert len(id1) == 15


def test_citation_id_different_urls():
    id1 = _citation_id_from_url("https://a.com")
    id2 = _citation_id_from_url("https://b.com")
    assert id1 != id2


def test_cache_key_deterministic():
    key1 = _cache_key("test query", None, None)
    key2 = _cache_key("test query", None, None)
    assert key1 == key2


def test_cache_key_different_domains():
    key1 = _cache_key("test", ["a.com"], None)
    key2 = _cache_key("test", ["b.com"], None)
    assert key1 != key2


def test_cache_key_includes_location():
    key1 = _cache_key("test", None, "US")
    key2 = _cache_key("test", None, "UK")
    assert key1 != key2


def test_synthesize_text_from_citations():
    citations = [
        Citation(id="c1", title="Title A", url="https://a.com", snippet="Snippet A", topic="test"),
        Citation(id="c2", title="Title B", url="https://b.com", snippet="Snippet B", topic="test"),
    ]
    text = _synthesize_text_from_citations(citations)
    assert "Title A" in text
    assert "Snippet A" in text
    assert "Title B" in text


def test_synthesize_text_empty():
    text = _synthesize_text_from_citations([])
    assert text == ""


def test_default_economic_domains():
    assert "worldbank.org" in DEFAULT_ECONOMIC_DOMAINS
    assert "imf.org" in DEFAULT_ECONOMIC_DOMAINS


@patch("madd.tools.web_search.OpenAI")
@patch("madd.core.config.get_settings")
def test_web_search_calls_with_include_sources(mock_settings, mock_openai):
    mock_settings.return_value.openai_api_key = "test"
    mock_settings.return_value.search_model = "gpt-4o"
    mock_settings.return_value.search_cache_enabled = False
    mock_settings.return_value.search_cache_dir = ".cache/test"
    
    mock_response = MagicMock()
    mock_response.output = []
    mock_client = MagicMock()
    mock_client.responses.create.return_value = mock_response
    mock_openai.return_value = mock_client
    
    web_search("test query", use_cache=False)
    
    mock_client.responses.create.assert_called_once()
    call_kwargs = mock_client.responses.create.call_args.kwargs
    assert call_kwargs["include"] == ["web_search_call.action.sources"]


@patch("madd.tools.web_search.OpenAI")
@patch("madd.core.config.get_settings")
def test_web_search_with_allowed_domains(mock_settings, mock_openai):
    mock_settings.return_value.openai_api_key = "test"
    mock_settings.return_value.search_model = "gpt-4o"
    mock_settings.return_value.search_cache_enabled = False
    mock_settings.return_value.search_cache_dir = ".cache/test"
    
    mock_response = MagicMock()
    mock_response.output = []
    mock_client = MagicMock()
    mock_client.responses.create.return_value = mock_response
    mock_openai.return_value = mock_client
    
    web_search("test query", allowed_domains=["gov.uk", "gov.us"], use_cache=False)
    
    call_kwargs = mock_client.responses.create.call_args.kwargs
    tools = call_kwargs["tools"]
    assert len(tools) == 1
    assert tools[0]["type"] == "web_search"
    assert tools[0]["filters"]["allowed_domains"] == ["gov.uk", "gov.us"]


@patch("madd.tools.web_search.OpenAI")
@patch("madd.core.config.get_settings")
def test_web_search_max_results_slicing(mock_settings, mock_openai):
    mock_settings.return_value.openai_api_key = "test"
    mock_settings.return_value.search_model = "gpt-4o"
    mock_settings.return_value.search_cache_enabled = False
    mock_settings.return_value.search_cache_dir = ".cache/test"
    
    mock_action = MagicMock()
    mock_action.sources = [
        MagicMock(url=f"https://example.com/{i}", title=f"Title {i}", snippet=f"Snippet {i}")
        for i in range(10)
    ]
    mock_item = MagicMock()
    mock_item.type = "web_search_call"
    mock_item.action = mock_action
    
    mock_response = MagicMock()
    mock_response.output = [mock_item]
    mock_client = MagicMock()
    mock_client.responses.create.return_value = mock_response
    mock_openai.return_value = mock_client
    
    _, citations = web_search("test", max_results=3, use_cache=False)
    
    assert len(citations) == 3


@patch("madd.tools.web_search._load_cache")
@patch("madd.core.config.get_settings")
def test_cache_hit_returns_text_and_citations(mock_settings, mock_load_cache):
    mock_settings.return_value.search_cache_enabled = True
    
    cached_citations = [
        Citation(id="cite_abc", title="Cached Title", url="https://cached.com", snippet="Cached snippet", topic="test")
    ]
    mock_load_cache.return_value = {
        "text": "Cached research text",
        "citations": cached_citations,
    }
    
    text, citations = web_search("test", use_cache=True)
    
    assert text == "Cached research text"
    assert len(citations) == 1
    assert citations[0].title == "Cached Title"


@patch("madd.tools.web_search._load_cache")
@patch("madd.core.config.get_settings")
def test_cache_hit_synthesizes_text_if_empty(mock_settings, mock_load_cache):
    mock_settings.return_value.search_cache_enabled = True
    
    cached_citations = [
        Citation(id="cite_abc", title="Title", url="https://a.com", snippet="Important snippet", topic="test")
    ]
    mock_load_cache.return_value = {
        "text": "",
        "citations": cached_citations,
    }
    
    text, citations = web_search("test", use_cache=True)
    
    assert "Title" in text
    assert "Important snippet" in text


def test_parse_sources_handles_none_sources():
    mock_action = MagicMock()
    mock_action.sources = None
    mock_item = MagicMock()
    mock_item.type = "web_search_call"
    mock_item.action = mock_action
    mock_response = MagicMock()
    mock_response.output = [mock_item]
    
    citations = _parse_sources_from_response(mock_response, "economy", datetime.now(timezone.utc))
    
    assert citations == []


def test_parse_sources_handles_none_annotations():
    mock_block = MagicMock()
    mock_block.annotations = None
    mock_item = MagicMock()
    mock_item.content = [mock_block]
    mock_response = MagicMock()
    mock_response.output = [mock_item]
    
    citations = _parse_sources_from_response(mock_response, "leaders", datetime.now(timezone.utc))
    
    assert citations == []


def test_parse_sources_key_mapping_populates_title_snippet():
    mock_action = MagicMock()
    mock_action.sources = [
        {"link": "https://un.org/los", "name": "UNCLOS", "text": "Law of the Sea framework."}
    ]
    mock_item = MagicMock()
    mock_item.type = "web_search_call"
    mock_item.action = mock_action
    mock_response = MagicMock()
    mock_response.output = [mock_item]
    
    citations = _parse_sources_from_response(mock_response, "maritime_law", datetime.now(timezone.utc))
    
    assert citations
    assert citations[0].title == "UNCLOS"
    assert citations[0].snippet.startswith("Law of the Sea")
