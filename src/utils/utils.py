import json
import os
import time
from typing import List, Dict, Any, Tuple, Optional
from duckduckgo_search.exceptions import DuckDuckGoSearchException
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from colorama import init as colorama_init

colorama_init(autoreset=True)

def print_green(msg): 
    print("\033[92m" + msg + "\033[0m")

def print_yellow(msg): 
    print("\033[93m" + msg + "\033[0m")

MODEL_NAME = "gpt-4o-mini"
SMART_MODEL_NAME = "gpt-4o"

REGION_DEFAULTS = {
    "Africa": {
        "core_goals": ["Pan-African unity", "Economic development through AfCFTA"],
        "treaties_and_agreements": ["African Continental Free Trade Area (AfCFTA)", "African Union treaties"],
        "cultural_values": ["Community-based society", "Respect for elders and traditions"],
        "governance_systems": ["Mix of modern and traditional authorities", "Tribal council influence"]
    },
    "Europe": {
        "core_goals": ["European integration", "Economic cooperation"],
        "treaties_and_agreements": ["European Union treaties", "Schengen Agreement"],
        "cultural_values": ["Individual rights", "Democratic values"],
        "governance_systems": ["Parliamentary democracy", "EU institutional framework"]
    },
    "Asia": {
        "core_goals": ["Regional stability", "Economic development"],
        "treaties_and_agreements": ["ASEAN agreements", "RCEP", "Belt and Road Initiative"],
        "cultural_values": ["Collective harmony", "Hierarchical respect"],
        "governance_systems": ["Mix of democratic and authoritarian systems"]
    },
    "Middle East": {
        "core_goals": ["Regional security", "Economic diversification"],
        "treaties_and_agreements": ["Gulf Cooperation Council", "Arab League agreements"],
        "cultural_values": ["Religious traditions", "Family honor"],
        "governance_systems": ["Monarchies", "Islamic law influence"]
    },
    "South America": {
        "core_goals": ["Regional integration", "Social equality"],
        "treaties_and_agreements": ["Mercosur", "Pacific Alliance"],
        "cultural_values": ["Social solidarity", "Cultural diversity"],
        "governance_systems": ["Presidential systems", "Democratic institutions"]
    },
    "North America": {
        "core_goals": ["Economic prosperity", "Democratic values"],
        "treaties_and_agreements": ["USMCA", "NATO"],
        "cultural_values": ["Individual freedom", "Multiculturalism"],
        "governance_systems": ["Federal democracy", "Constitutional systems"]
    },
    "Oceania": {
        "core_goals": ["Pacific cooperation", "Climate change action"],
        "treaties_and_agreements": ["Pacific Islands Forum", "ANZUS"],
        "cultural_values": ["Indigenous rights", "Environmental stewardship"],
        "governance_systems": ["Parliamentary democracy", "Indigenous governance"]
    }
}

def get_region_defaults(region: str) -> Dict[str, Any]:
    """Get default values for a given region."""
    for key in REGION_DEFAULTS:
        if key.lower() in region.lower():
            return REGION_DEFAULTS[key]
    return REGION_DEFAULTS["Asia"]

def format_gdp(gdp_value: float, unit: str = None, year: Optional[str] = None) -> str:
    """Format GDP value with unit and year."""
    if year:
        return f"{gdp_value:.2f} {unit} ({year})"
    return f"{gdp_value:.2f} {unit}"

def gather_snippets_and_links(
    search_tool: DuckDuckGoSearchAPIWrapper,
    query: str, 
    max_results: int = 5, 
    max_retries: int = 3, 
    cooldown: int = 2
) -> Tuple[str, List[str]]:
    """
    Gather search snippets and links using DuckDuckGo search.
    
    Args:
        search_tool: DuckDuckGo search wrapper instance
        query: Search query string
        max_results: Maximum number of results to return
        max_retries: Maximum number of retry attempts
        cooldown: Cooldown time between retries in seconds
        
    Returns:
        Tuple of (combined snippets string, list of source URLs)
    """
    for attempt in range(max_retries):
        try:
            results = search_tool.results(query, max_results=max_results)
            snippets = []
            sources = []
            for r in results:
                title = r.get('title', '')
                link = r.get('link', '')
                snippet = r.get('snippet', '')
                snippet_text = f"Title: {title}\nLink: {link}\nSnippet: {snippet}"
                snippets.append(snippet_text)
                sources.append(link)
            combined_snippets = "\n\n".join(snippets)
            time.sleep(cooldown)  # Add cooldown between searches
            return combined_snippets, sources
        except DuckDuckGoSearchException as e:
            print(f"[Search attempt {attempt + 1}/{max_retries} failed]: {str(e)}")
            if attempt < max_retries - 1:
                cooldown_time = (attempt + 1) * cooldown * 2  # Exponential backoff
                print(f"Cooling down for {cooldown_time} seconds...")
                time.sleep(cooldown_time)
            else:
                print(f"All retries failed for query: {query}")
                return "", []
        except Exception as e:
            print(f"[Unexpected error in search]: {str(e)}")
            return "", []

def clean_json_response(response: str) -> str:
    """Clean and extract JSON from a response string."""
    try:
        start_idx = response.find('{')
        end_idx = response.rfind('}') + 1
        if start_idx != -1 and end_idx != 0:
            response = response[start_idx:end_idx]
        return response
    except Exception:
        return response

PROFILE_DIR = os.path.join(os.getcwd(), "data", "country_profiles") 
BASIC_MODEL_CONFIG = {
    "model_type": "openai_chat",
    "config_name": "openai_config",
    "model_name": MODEL_NAME,
}
MODEL_CONFIG = {
    "model_type": "openai_chat",
    "config_name": "openai_config",
    "model_name": SMART_MODEL_NAME,
}
