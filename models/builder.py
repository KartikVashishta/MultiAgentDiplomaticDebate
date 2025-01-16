import os, json
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper

from models.country_profile import (
    CountryProfile, BasicInfo, Government, HistoricalContext, ForeignPolicy, 
    EconomicProfile, CulturalSocietal, DiplomaticBehavior, StrategicInterests, 
    RelationshipsAndAlliances, MemorySeeds
)
from models.utils.validator import ProfileValidator
from models.utils.utils import (
    get_region_defaults, format_gdp, gather_snippets_and_links, clean_json_response
)
from prompts import (
    PROFILE_VALIDATOR_PROMPT, BASIC_INFO_PROMPT, GOVERNMENT_TYPE_PROMPT, LEADERSHIP_PROMPT, 
    IDEOLOGIES_PROMPT, COLONIAL_HISTORY_PROMPT, MAJOR_CONFLICTS_PROMPT, FOREIGN_POLICY_PROMPT,
    CORE_GOALS_PROMPT, ALLIANCE_PROMPT, GLOBAL_ISSUES_PROMPT, TREATIES_PROMPT,
    ECONOMIC_PROFILE_PROMPT, BACKUP_ECONOMIC_PROFILE_PROMPT, CULTURAL_VALUES_PROMPT,
    PUBLIC_OPINION_PROMPT, COMMUNICATION_STYLE_PROMPT, BACKUP_CULTURAL_VALUES_PROMPT,
    DIPLOMATIC_BEHAVIOR_PROMPT, BACKUP_DIPLOMATIC_BEHAVIOR_PROMPT, SECURITY_PROMPT,
    ECONOMIC_PROMPT, CULTURAL_PROMPT, EVENTS_PROMPT, RESOLUTIONS_PROMPT, ALLIANCES_PROMPT,
    BACKUP_EVENTS_PROMPT, BACKUP_MEMORY_SEEDS_PROMPT, RELATIONSHIPS_AND_ALLIANCES_PROMPT,
    BACKUP_STRATEGIC_INTERESTS_PROMPT, BACKUP_RELATIONSHIPS_AND_ALLIANCES_PROMPT,
    BACKUP_CULTURAL_VALUES_PROMPT_GENERATE
)

from colorama import init as colorama_init
colorama_init(autoreset=True)

def print_green(msg): 
    print("\033[92m" + msg + "\033[0m")

def print_yellow(msg): 
    print("\033[93m" + msg + "\033[0m")

load_dotenv()

PROFILE_DIR = os.path.join(os.getcwd(), "profiles")
os.makedirs(PROFILE_DIR, exist_ok=True)

def CountryProfileBuilder(country_name: str) -> CountryProfile:
    profile_path = os.path.join(PROFILE_DIR, f"{country_name.lower().replace(' ', '_')}.json")
    if os.path.isfile(profile_path):
        print_green(f"[INFO] Found existing profile for {country_name}, loading")
        with open(profile_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return CountryProfile(**data)
    
    print_yellow(f"[INFO] No existing profile found for {country_name}, building new profile")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    search_tool = DuckDuckGoSearchAPIWrapper()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # 1) BASIC INFO  (region, population)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    region_query = f"{country_name} world region continent"
    population_query = f"{country_name} total population 2024"
    region_snippets, region_sources = gather_snippets_and_links(search_tool, region_query, max_results=8)
    population_snippets, population_sources = gather_snippets_and_links(search_tool, population_query, max_results=8)

    basic_chain = BASIC_INFO_PROMPT | llm
    basic_info_response = basic_chain.invoke({
        "country_name": country_name, 
        "region_snippets": region_snippets, 
        "population_snippets": population_snippets
    }).content.strip()

    try:
        cleaned_response = clean_json_response(basic_info_response)
        basic_data = json.loads(cleaned_response)
        region = basic_data.get("region", "")
        # Ensure region is a string
        if isinstance(region, list):
            region = region[0] if region else ""
        elif not isinstance(region, str):
            region = str(region) if region else ""
        population = basic_data.get("population", None)
    except Exception as e:
        print_yellow(f"[ERROR parsing BASIC INFO]: {e}\nResponse was: {basic_info_response}")
        region = ""
        population = None

    basic_info = BasicInfo(
        name=country_name,
        region=region,
        population=int(population) if (population and str(population).isdigit()) else None
    )
    print_green(f"[BASIC INFO] found")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # 2) GOVERNMENT (government_type, current_leadership, political_ideologies)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    
    government_query = f"{country_name} government type"
    current_leadership_query = f"current leader of {country_name}"
    political_ideologies_query = f"{country_name} political ideology"
    
    government_snippets, _ = gather_snippets_and_links(search_tool, government_query, max_results=5)
    leadership_snippets, _ = gather_snippets_and_links(search_tool, current_leadership_query, max_results=5)
    ideologies_snippets, _ = gather_snippets_and_links(search_tool, political_ideologies_query, max_results=5)

    gov_type_chain = GOVERNMENT_TYPE_PROMPT | llm
    gov_type_response = gov_type_chain.invoke({
        "country_name": country_name,
        "government_snippets": government_snippets
    }).content.strip()


    leadership_chain = LEADERSHIP_PROMPT | llm
    leadership_response = leadership_chain.invoke({
        "country_name": country_name,
        "leadership_snippets": leadership_snippets
    }).content.strip()


    ideologies_chain = IDEOLOGIES_PROMPT | llm
    ideologies_response = ideologies_chain.invoke({
        "country_name": country_name,
        "ideologies_snippets": ideologies_snippets
    }).content.strip()

    try:
        gov_type_data = json.loads(clean_json_response(gov_type_response))
        leadership_data = json.loads(clean_json_response(leadership_response))
        ideologies_data = json.loads(clean_json_response(ideologies_response))

        government_type = gov_type_data.get("government_type", "")
        current_leadership = leadership_data.get("current_leadership", [])
        political_ideologies = ideologies_data.get("political_ideologies", [])
    except Exception as e:
        print_yellow(f"[ERROR parsing GOVERNMENT]: {e}\nResponses were:\nGov Type: {gov_type_response}\nLeadership: {leadership_response}\nIdeologies: {ideologies_response}")
        government_type = ""
        current_leadership = []
        political_ideologies = []

    government_info = Government(
        government_type=government_type,
        current_leadership=current_leadership,
        political_ideologies=political_ideologies
    )
    print_green(f"[GOVERNMENT] found")
    
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # 3) HISTORICAL CONTEXT (colonial_history, major_conflicts, evolution_of_foreign_policy)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    colonial_history_query = f"{country_name} colonial history and colonization"
    major_conflicts_query = f"{country_name} major wars and military conflicts"
    foreign_policy_query = f"{country_name} foreign policy changes and evolution"

    colonial_snippets, _ = gather_snippets_and_links(search_tool, colonial_history_query, max_results=10)
    conflicts_snippets, _ = gather_snippets_and_links(search_tool, major_conflicts_query, max_results=10)
    foreign_policy_snippets, _ = gather_snippets_and_links(search_tool, foreign_policy_query, max_results=10)

    colonial_chain = COLONIAL_HISTORY_PROMPT | llm
    colonial_response = colonial_chain.invoke({
        "country_name": country_name,
        "colonial_snippets": colonial_snippets
    }).content.strip()


    conflicts_chain = MAJOR_CONFLICTS_PROMPT | llm
    conflicts_response = conflicts_chain.invoke({
        "country_name": country_name,
        "conflicts_snippets": conflicts_snippets
    }).content.strip()


    foreign_policy_chain = FOREIGN_POLICY_PROMPT | llm
    foreign_policy_response = foreign_policy_chain.invoke({
        "country_name": country_name,
        "foreign_policy_snippets": foreign_policy_snippets
    }).content.strip()

    try:
        colonial_data = json.loads(clean_json_response(colonial_response))
        conflicts_data = json.loads(clean_json_response(conflicts_response))
        evolution_data = json.loads(clean_json_response(foreign_policy_response))

        colonial_history = colonial_data.get("colonial_history", "")
        major_conflicts = conflicts_data.get("major_conflicts", [])
        evolution_of_foreign_policy = evolution_data.get("evolution_of_foreign_policy", "")
    except Exception as e:
        print_yellow(f"[ERROR parsing HISTORICAL CONTEXT]: {e}\nResponses were:\nColonial: {colonial_response}\nConflicts: {conflicts_response}\nForeign Policy: {foreign_policy_response}")
        colonial_history = ""
        major_conflicts = []
        evolution_of_foreign_policy = ""

    historical_context = HistoricalContext(
        colonial_history=colonial_history,
        major_conflicts=major_conflicts,
        evolution_of_foreign_policy=evolution_of_foreign_policy
    )
    print_green(f"[HISTORICAL CONTEXT] found")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # 4) FOREIGN POLICY (core_goals, alliance_patterns, global_issue_positions, treaties_and_agreements)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    core_goals_query = f"{country_name} main foreign policy objectives and goals"
    alliance_query = f"{country_name} international alliances and partnerships"
    global_issues_query = f"{country_name} stance on global issues and international relations"
    treaties_query = f"{country_name} major international treaties and agreements"

    core_goals_snippets, _ = gather_snippets_and_links(search_tool, core_goals_query, max_results=8)
    alliance_snippets, _ = gather_snippets_and_links(search_tool, alliance_query, max_results=8)
    global_issues_snippets, _ = gather_snippets_and_links(search_tool, global_issues_query, max_results=8)
    treaties_snippets, _ = gather_snippets_and_links(search_tool, treaties_query, max_results=8)


    core_goals_chain = CORE_GOALS_PROMPT | llm
    alliance_chain = ALLIANCE_PROMPT | llm
    global_issues_chain = GLOBAL_ISSUES_PROMPT | llm
    treaties_chain = TREATIES_PROMPT | llm

    # Get responses
    core_goals_response = core_goals_chain.invoke({
        "country_name": country_name,
        "core_goals_snippets": core_goals_snippets
    }).content.strip()

    alliance_response = alliance_chain.invoke({
        "country_name": country_name,
        "alliance_snippets": alliance_snippets
    }).content.strip()

    global_issues_response = global_issues_chain.invoke({
        "country_name": country_name,
        "global_issues_snippets": global_issues_snippets
    }).content.strip()

    treaties_response = treaties_chain.invoke({
        "country_name": country_name,
        "treaties_snippets": treaties_snippets
    }).content.strip()

    try:
        core_goals_data = json.loads(clean_json_response(core_goals_response))
        alliance_data = json.loads(clean_json_response(alliance_response))
        global_issues_data = json.loads(clean_json_response(global_issues_response))
        treaties_data = json.loads(clean_json_response(treaties_response))

        core_goals = core_goals_data.get("core_goals", [])
        alliance_patterns = alliance_data.get("alliance_patterns", [])
        global_issue_positions = global_issues_data.get("global_issue_positions", [])
        treaties_and_agreements = treaties_data.get("treaties_and_agreements", [])
    except Exception as e:
        print_yellow(f"[ERROR parsing FOREIGN POLICY]: {e}\nResponses were:\nCore Goals: {core_goals_response}\nAlliances: {alliance_response}\nGlobal Issues: {global_issues_response}\nTreaties: {treaties_response}")
        core_goals = []
        alliance_patterns = []
        global_issue_positions = []
        treaties_and_agreements = []

    foreign_policy = ForeignPolicy(
        core_goals=core_goals,
        alliance_patterns=alliance_patterns,
        global_issue_positions=global_issue_positions,
        treaties_and_agreements=treaties_and_agreements
    )
    print_green(f"[FOREIGN POLICY] found")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # 5) ECONOMIC PROFILE (gdp, major_industries, trade_relations, development_goals)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Economy of
    gdp_queries = [
        f"Official GDP of {country_name} in 2024 or latest year (in USD billions)",
        f"{country_name} GDP growth rate and economic size",
        f"{country_name} GDP per capita and total GDP"
    ]
    industry_queries = [
        f"What are the major industries of {country_name}?",
        f"{country_name} key economic sectors",
        f"{country_name} industrial production and manufacturing"
    ]
    trade_queries = [
        f"What are the main trade partners of {country_name}?",
        f"{country_name} import export relationships",
        f"{country_name} international trade agreements"
    ]
    dev_goals_queries = [
        f"{country_name} national development goals or economic plans",
        f"{country_name} economic reform agenda",
        f"{country_name} future economic priorities"
    ]

    # Gather snippets with increased max_results where needed
    gdp_snippets = []
    for query in gdp_queries:
        snippets, _ = gather_snippets_and_links(search_tool, query, max_results=5)
        gdp_snippets.extend(snippets)

    industry_snippets = []
    for query in industry_queries:
        snippets, _ = gather_snippets_and_links(search_tool, query, max_results=5)
        industry_snippets.extend(snippets)

    trade_snippets = []
    for query in trade_queries:
        snippets, _ = gather_snippets_and_links(search_tool, query, max_results=5)
        trade_snippets.extend(snippets)

    dev_snippets = []
    for query in dev_goals_queries:
        snippets, _ = gather_snippets_and_links(search_tool, query, max_results=5)
        dev_snippets.extend(snippets)

    # Single comprehensive economic prompt

    econ_chain = ECONOMIC_PROFILE_PROMPT | llm
    econ_response = econ_chain.invoke({
        "country_name": country_name,
        "gdp_snippets": "\n".join(gdp_snippets) if gdp_snippets else "No direct GDP information available.",
        "industry_snippets": "\n".join(industry_snippets) if industry_snippets else "No direct industry information available.",
        "trade_snippets": "\n".join(trade_snippets) if trade_snippets else "No direct trade information available.",
        "dev_snippets": "\n".join(dev_snippets) if dev_snippets else "No direct development goals information available."
    }).content.strip()

    try:
        econ_data = json.loads(clean_json_response(econ_response))
        gdp_data = econ_data.get("gdp", {})
        if isinstance(gdp_data, dict):
            gdp = float(gdp_data.get("value", 0.0))
            gdp_unit = gdp_data.get("unit", "trillion USD")
            gdp_year = gdp_data.get("year")
        else:
            gdp = float(gdp_data) if gdp_data else 0.0
            gdp_unit = "trillion USD"
            gdp_year = None
            
        major_industries = econ_data.get("major_industries", [])
        trade_relations = econ_data.get("trade_relations", [])
        development_goals = econ_data.get("development_goals", [])
        
        # If any field is empty or GDP is 0, generate backup data using region defaults
        if gdp == 0.0 or not major_industries or not trade_relations or not development_goals:
            region_defaults = get_region_defaults(basic_info.region)

            backup_chain = BACKUP_ECONOMIC_PROFILE_PROMPT | llm
            backup_response = backup_chain.invoke({
                "country_name": country_name,
                "region": basic_info.region,
                "regional_goals": ", ".join(region_defaults["core_goals"]),
                "regional_treaties": ", ".join(region_defaults["treaties_and_agreements"])
            }).content.strip()
            backup_data = json.loads(clean_json_response(backup_response))
            
            if gdp == 0.0:
                gdp_data = backup_data.get("gdp", {})
                if isinstance(gdp_data, dict):
                    gdp = float(gdp_data.get("value", 100.0))
                    gdp_unit = gdp_data.get("unit", "trillion USD")
                    gdp_year = gdp_data.get("year", "2024")
                else:
                    gdp = float(gdp_data) if gdp_data else 100.0
                    gdp_unit = "trillion USD"
                    gdp_year = "2024"
            
            major_industries = major_industries or backup_data.get("major_industries", [])
            trade_relations = trade_relations or backup_data.get("trade_relations", [])
            development_goals = development_goals or backup_data.get("development_goals", [])

    except Exception as e:
        print_yellow(f"[ERROR parsing ECONOMIC PROFILE]: {e}\nResponse was: {econ_response}")
        # Generate complete backup data on error using region defaults
        region_defaults = get_region_defaults(basic_info.region)
        
        backup_chain = BACKUP_ECONOMIC_PROFILE_PROMPT | llm
        try:
            backup_response = backup_chain.invoke({
                "country_name": country_name,
                "region": basic_info.region,
                "regional_goals": ", ".join(region_defaults["core_goals"]),
                "regional_treaties": ", ".join(region_defaults["treaties_and_agreements"])
            }).content.strip()
            backup_data = json.loads(clean_json_response(backup_response))
            gdp_data = backup_data.get("gdp", {})
            if isinstance(gdp_data, dict):
                gdp = float(gdp_data.get("value"))
                gdp_unit = gdp_data.get("unit")
                gdp_year = gdp_data.get("year")

            print_green(f"-----[BACKUP GDP] found: {gdp_data} unit: {gdp_unit} year: {gdp_year}-----")

            major_industries = backup_data.get("major_industries", [])
            trade_relations = backup_data.get("trade_relations", [])
            development_goals = backup_data.get("development_goals", [])
        except Exception as backup_error:
            print_yellow(f"[ERROR in backup generation]: {backup_error}")
            gdp = 100.0  # Fallback value
            gdp_unit = "trillion USD"
            gdp_year = "2024"
            major_industries = [f"Generated major industry for {country_name}"]
            trade_relations = [f"Generated trade relation for {country_name}"]
            development_goals = [f"Generated development goal for {country_name}"]

    economic_profile = EconomicProfile(
        gdp=gdp,
        gdp_unit=gdp_unit,
        gdp_year=gdp_year,
        major_industries=major_industries,
        trade_relations=trade_relations,
        development_goals=development_goals
    )
    print_green(f"[ECONOMIC PROFILE] found")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # 6) CULTURAL & SOCIETAL
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    cultural_queries = [
        f"{country_name} cultural values and traditions",
        f"{country_name} societal norms",
        f"{country_name} cultural identity",
        f"{country_name} social values",
        f"{country_name} cultural practices"
    ]

    public_opinion_queries = [
        f"{country_name} public opinion on major issues",
        f"{country_name} social attitudes",
        f"{country_name} public sentiment analysis"
    ]
    communication_queries = [
        f"{country_name} communication style in diplomacy",
        f"{country_name} cultural communication patterns",
        f"{country_name} negotiation and dialogue approach"
    ]

    cultural_snippets = []
    for query in cultural_queries:
        snippets, _ = gather_snippets_and_links(search_tool, query, max_results=5)
        cultural_snippets.extend(snippets)

    opinion_snippets = []
    for query in public_opinion_queries:
        snippets, _ = gather_snippets_and_links(search_tool, query, max_results=5)
        opinion_snippets.extend(snippets)

    comm_snippets = []
    for query in communication_queries:
        snippets, _ = gather_snippets_and_links(search_tool, query, max_results=5)
        comm_snippets.extend(snippets)


    cultural_chain = CULTURAL_VALUES_PROMPT | llm
    cultural_response = cultural_chain.invoke({
        "country_name": country_name,
        "cultural_snippets": "\n".join(cultural_snippets) if cultural_snippets else "No direct cultural information available."
    }).content.strip()

    opinion_chain = PUBLIC_OPINION_PROMPT | llm
    opinion_response = opinion_chain.invoke({
        "country_name": country_name,
        "opinion_snippets": "\n".join(opinion_snippets) if opinion_snippets else "No direct public opinion information available."
    }).content.strip()


    comm_chain = COMMUNICATION_STYLE_PROMPT | llm
    comm_response = comm_chain.invoke({
        "country_name": country_name,
        "comm_snippets": "\n".join(comm_snippets) if comm_snippets else "No direct communication style information available."
    }).content.strip()

    try:
        cultural_data = json.loads(clean_json_response(cultural_response))
        opinion_data = json.loads(clean_json_response(opinion_response))
        comm_data = json.loads(clean_json_response(comm_response))

        cultural_values = cultural_data.get("cultural_values", [])
        public_opinion = str(opinion_data.get("public_opinion", ""))  # Convert to string explicitly
        communication_style = comm_data.get("communication_style", "")
        
        # If any field is empty, generate backup data using region defaults
        if not cultural_values or not public_opinion or not communication_style:
            region_defaults = get_region_defaults(basic_info.region)

            backup_chain = BACKUP_CULTURAL_VALUES_PROMPT | llm
            backup_response = backup_chain.invoke({
                "country_name": country_name,
                "region": basic_info.region,
                "regional_values": ", ".join(region_defaults["cultural_values"]),
                "governance_systems": ", ".join(region_defaults["governance_systems"])
            }).content.strip()
            backup_data = json.loads(clean_json_response(backup_response))
            
            cultural_values = cultural_values or backup_data.get("cultural_values", [])
            public_opinion = str(public_opinion or backup_data.get("public_opinion", ""))  # Convert to string explicitly
            communication_style = communication_style or backup_data.get("communication_style", "")
    except Exception as e:
        print_yellow(f"[ERROR parsing CULTURAL & SOCIETAL]: {e}\nResponse was: {cultural_response}, {opinion_response}, {comm_response}")
        # Generate complete backup data on error

        backup_chain = BACKUP_CULTURAL_VALUES_PROMPT_GENERATE | llm
        try:
            backup_response = backup_chain.invoke({"country_name": country_name}).content.strip()
            backup_data = json.loads(clean_json_response(backup_response))
            cultural_values = backup_data.get("cultural_values", [])
            public_opinion = str(backup_data.get("public_opinion", ""))  # Convert to string explicitly
            communication_style = backup_data.get("communication_style", "")
        except Exception as backup_error:
            print_yellow(f"[ERROR in backup generation]: {backup_error}")
            cultural_values = [f"Generated cultural value for {country_name}"]
            public_opinion = f"Generated public opinion for {country_name}"
            communication_style = f"Generated communication style for {country_name}"

    cultural_societal = CulturalSocietal(
        cultural_values=cultural_values,
        public_opinion=public_opinion,
        communication_style=communication_style
    )
    print_green(f"[CULTURAL & SOCIETAL] found")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # 7) DIPLOMATIC BEHAVIOR
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    diplomatic_queries = [
        f"{country_name} diplomatic style and approach",
        f"{country_name} international relations strategy",
        f"{country_name} foreign policy behavior"
    ]
    negotiation_queries = [
        f"{country_name} negotiation tactics in diplomacy",
        f"{country_name} diplomatic negotiations history",
        f"How does {country_name} handle international negotiations"
    ]
    objectives_queries = [
        f"{country_name} foreign policy objectives",
        f"{country_name} diplomatic goals and vision",
        f"{country_name} international ambitions"
    ]

    diplomatic_snippets = []
    for query in diplomatic_queries:
        snippets, _ = gather_snippets_and_links(search_tool, query, max_results=5)
        diplomatic_snippets.extend(snippets)

    negotiation_snippets = []
    for query in negotiation_queries:
        snippets, _ = gather_snippets_and_links(search_tool, query, max_results=5)
        negotiation_snippets.extend(snippets)

    objectives_snippets = []
    for query in objectives_queries:
        snippets, _ = gather_snippets_and_links(search_tool, query, max_results=5)
        objectives_snippets.extend(snippets)


    db_chain = DIPLOMATIC_BEHAVIOR_PROMPT | llm
    db_response = db_chain.invoke({
        "country_name": country_name,
        "diplomatic_snippets": "\n".join(diplomatic_snippets) if diplomatic_snippets else "No direct diplomatic style information available.",
        "negotiation_snippets": "\n".join(negotiation_snippets) if negotiation_snippets else "No direct negotiation information available.",
        "objectives_snippets": "\n".join(objectives_snippets) if objectives_snippets else "No direct objectives information available."
    }).content.strip()

    try:
        db_data = json.loads(clean_json_response(db_response))
        style = db_data.get("style", "")
        negotiation_tactics = db_data.get("negotiation_tactics", [])
        decision_making_process = db_data.get("decision_making_process", "")
        short_term_objectives = db_data.get("short_term_objectives", [])
        long_term_vision = db_data.get("long_term_vision", [])
        if isinstance(long_term_vision, str):
            long_term_vision = [long_term_vision]
            
        # If any field is empty, generate backup data
        if not style or not negotiation_tactics or not decision_making_process or not short_term_objectives or not long_term_vision:

            backup_chain = BACKUP_DIPLOMATIC_BEHAVIOR_PROMPT | llm
            backup_response = backup_chain.invoke({"country_name": country_name}).content.strip()
            backup_data = json.loads(clean_json_response(backup_response))
            
            style = style or backup_data.get("style", "")
            negotiation_tactics = negotiation_tactics or backup_data.get("negotiation_tactics", [])
            decision_making_process = decision_making_process or backup_data.get("decision_making_process", "")
            short_term_objectives = short_term_objectives or backup_data.get("short_term_objectives", [])
            long_term_vision = long_term_vision or backup_data.get("long_term_vision", [])
    except Exception as e:
        print_yellow(f"[ERROR parsing DIPLOMATIC BEHAVIOR]: {e}\nResponse was: {db_response}")

        backup_chain = BACKUP_DIPLOMATIC_BEHAVIOR_PROMPT | llm
        try:
            backup_response = backup_chain.invoke({"country_name": country_name}).content.strip()
            backup_data = json.loads(clean_json_response(backup_response))
            style = backup_data.get("style", f"Generated diplomatic style for {country_name}")
            negotiation_tactics = backup_data.get("negotiation_tactics", [f"Generated tactic for {country_name}"])
            decision_making_process = backup_data.get("decision_making_process", f"Generated process for {country_name}")
            short_term_objectives = backup_data.get("short_term_objectives", [f"Generated objective for {country_name}"])
            long_term_vision = backup_data.get("long_term_vision", [f"Generated vision for {country_name}"])
        except Exception as backup_error:
            print_yellow(f"[ERROR in backup generation]: {backup_error}")
            style = f"Generated diplomatic style for {country_name}"
            negotiation_tactics = [f"Generated tactic for {country_name}"]
            decision_making_process = f"Generated process for {country_name}"
            short_term_objectives = [f"Generated objective for {country_name}"]
            long_term_vision = [f"Generated vision for {country_name}"]

    diplomatic_behavior = DiplomaticBehavior(
        style=style,
        negotiation_tactics=negotiation_tactics,
        decision_making_process=decision_making_process,
        short_term_objectives=short_term_objectives,
        long_term_vision=long_term_vision
    )
    print_green(f"[DIPLOMATIC BEHAVIOR] found")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # 8) STRATEGIC INTERESTS with improved prompt and backup
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    security_queries = [
        f"{country_name} national security concerns",
        f"{country_name} military and defense priorities", 
        f"{country_name} security challenges",
        f"{country_name} strategic security concerns"
    ]
    economic_interest_queries = [
        f"{country_name} strategic economic interests",
        f"{country_name} economic priorities globally",
        f"{country_name} economic goals"
    ]
    cultural_promotion_queries = [
        f"{country_name} cultural diplomacy",
        f"{country_name} soft power projection",
        f"{country_name} ideological influence"
    ]

    security_snippets = []
    for query in security_queries:
        snippets, _ = gather_snippets_and_links(search_tool, query, max_results=10)
        security_snippets.extend(snippets)

    economic_interest_snippets = []
    for query in economic_interest_queries:
        snippets, _ = gather_snippets_and_links(search_tool, query, max_results=10)
        economic_interest_snippets.extend(snippets)

    cultural_promotion_snippets = []
    for query in cultural_promotion_queries:
        snippets, _ = gather_snippets_and_links(search_tool, query, max_results=10)
        cultural_promotion_snippets.extend(snippets)

    try:
        security_chain = SECURITY_PROMPT | llm
        security_response = security_chain.invoke({
            "country_name": country_name,
            "security_snippets": "\n".join(security_snippets) if security_snippets else "No direct security information available."
        }).content.strip()
        security_data = json.loads(clean_json_response(security_response))
        security_concerns = security_data.get("concerns", [])

        economic_chain = ECONOMIC_PROMPT | llm
        economic_response = economic_chain.invoke({
            "country_name": country_name,
            "economic_snippets": "\n".join(economic_interest_snippets) if economic_interest_snippets else "No direct economic information available."
        }).content.strip()
        economic_data = json.loads(clean_json_response(economic_response))
        economic_interests = economic_data.get("interests", [])

        cultural_chain = CULTURAL_PROMPT | llm
        cultural_response = cultural_chain.invoke({
            "country_name": country_name,
            "cultural_snippets": "\n".join(cultural_promotion_snippets) if cultural_promotion_snippets else "No direct cultural information available."
        }).content.strip()
        cultural_data = json.loads(clean_json_response(cultural_response))
        cultural_promotion = cultural_data.get("promotion", [])

    except Exception as e:
        print(f"[ERROR parsing STRATEGIC INTERESTS]: {e}")

        try:

            backup_chain = BACKUP_STRATEGIC_INTERESTS_PROMPT | llm
            backup_response = backup_chain.invoke({
                "country_name": country_name,
                "region": basic_info.region,
                "regional_goals": ", ".join(region_defaults["core_goals"]),
                "regional_treaties": ", ".join(region_defaults["treaties_and_agreements"]),
                "regional_values": ", ".join(region_defaults["cultural_values"])
            }).content.strip()
            backup_data = json.loads(clean_json_response(backup_response))
            
            security_concerns = backup_data.get("security_concerns", [])
            economic_interests = backup_data.get("economic_interests", [])
            cultural_promotion = backup_data.get("cultural_ideological_promotion", [])

        except Exception as backup_error:
            print(f"[ERROR in backup generation]: {backup_error}")
            security_concerns = [f"Generated security concern for {country_name} in {basic_info.region}"]
            economic_interests = [f"Generated economic interest for {country_name} in {basic_info.region}"]
            cultural_promotion = [f"Generated cultural promotion aspect for {country_name} in {basic_info.region}"]

    strategic_interests = StrategicInterests(
        security_concerns=security_concerns,
        economic_interests=economic_interests,
        cultural_ideological_promotion=cultural_promotion
    )
    print_green(f"[STRATEGIC INTERESTS] found")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # 9) RELATIONSHIPS & ALLIANCES with improved prompt and backup
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    alliance_queries = [
        f"{country_name} major alliances and partnerships",
        f"{country_name} historical allies",
        f"{country_name} military and defense agreements"
    ]
    rivalry_queries = [
        f"{country_name} international conflicts and disputes",
        f"{country_name} diplomatic tensions",
        f"{country_name} geopolitical rivalries"
    ]
    reputation_queries = [
        f"{country_name} diplomatic reputation and standing",
        f"{country_name} international credibility",
        f"{country_name} role in global diplomacy"
    ]

    alliance_snippets = []
    for query in alliance_queries:
        snippets, _ = gather_snippets_and_links(search_tool, query, max_results=10)
        alliance_snippets.extend(snippets)

    rivalry_snippets = []
    for query in rivalry_queries:
        snippets, _ = gather_snippets_and_links(search_tool, query, max_results=10)
        rivalry_snippets.extend(snippets)

    reputation_snippets = []
    for query in reputation_queries:
        snippets, _ = gather_snippets_and_links(search_tool, query, max_results=10)
        reputation_snippets.extend(snippets)


    ra_chain = RELATIONSHIPS_AND_ALLIANCES_PROMPT | llm
    ra_response = ra_chain.invoke({
        "country_name": country_name,
        "alliance_snippets": "\n".join(alliance_snippets) if alliance_snippets else "No direct alliance information available.",
        "rivalry_snippets": "\n".join(rivalry_snippets) if rivalry_snippets else "No direct rivalry information available.",
        "reputation_snippets": "\n".join(reputation_snippets) if reputation_snippets else "No direct reputation information available."
    }).content.strip()

    try:
        ra_data = json.loads(clean_json_response(ra_response))
        past_alliances = ra_data.get("past_alliances", [])
        rivalries_conflicts = ra_data.get("rivalries_conflicts", [])
        diplomatic_reputation = ra_data.get("diplomatic_reputation", "")
        
        # If any field is empty, generate backup data
        if not past_alliances or not rivalries_conflicts or not diplomatic_reputation:
            backup_chain = BACKUP_RELATIONSHIPS_AND_ALLIANCES_PROMPT | llm
            backup_response = backup_chain.invoke({"country_name": country_name}).content.strip()
            backup_data = json.loads(clean_json_response(backup_response))
            
            past_alliances = past_alliances or backup_data.get("past_alliances", [])
            rivalries_conflicts = rivalries_conflicts or backup_data.get("rivalries_conflicts", [])
            diplomatic_reputation = diplomatic_reputation or backup_data.get("diplomatic_reputation", "")
    except Exception as e:
        print_yellow(f"[ERROR parsing RELATIONSHIPS & ALLIANCES]: {e}\nResponse was: {ra_response}")

        backup_chain = BACKUP_RELATIONSHIPS_AND_ALLIANCES_PROMPT | llm
        try:
            backup_response = backup_chain.invoke({"country_name": country_name}).content.strip()
            backup_data = json.loads(clean_json_response(backup_response))
            past_alliances = backup_data.get("past_alliances", [])
            rivalries_conflicts = backup_data.get("rivalries_conflicts", [])
            diplomatic_reputation = backup_data.get("diplomatic_reputation", "")
        except Exception as backup_error:
            print_yellow(f"[ERROR in backup generation]: {backup_error}")
            past_alliances = [f"Generated alliance for {country_name}"]
            rivalries_conflicts = [f"Generated rivalry for {country_name}"]
            diplomatic_reputation = f"Generated diplomatic reputation for {country_name}"

    relationships_and_alliances = RelationshipsAndAlliances(
        past_alliances=past_alliances,
        rivalries_conflicts=rivalries_conflicts,
        diplomatic_reputation=diplomatic_reputation
    )
    print_green(f"[RELATIONSHIPS & ALLIANCES] found")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # 10) MEMORY SEEDS with improved prompt and backup
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    historical_queries = [
        f"{country_name} significant historical events",
        f"{country_name} major diplomatic achievements",
        f"{country_name} turning points in history"
    ]
    resolution_queries = [
        f"{country_name} UN resolutions and international agreements",
        f"{country_name} diplomatic resolutions",
        f"{country_name} peace agreements and treaties"
    ]
    alliance_deal_queries = [
        f"{country_name} strategic partnerships and deals",
        f"{country_name} economic cooperation agreements",
        f"{country_name} bilateral and multilateral agreements"
    ]

    historical_snippets = []
    for query in historical_queries:
        snippets, _ = gather_snippets_and_links(search_tool, query, max_results=10)
        historical_snippets.extend(snippets)

    resolution_snippets = []
    for query in resolution_queries:
        snippets, _ = gather_snippets_and_links(search_tool, query, max_results=10)
        resolution_snippets.extend(snippets)

    alliance_deal_snippets = []
    for query in alliance_deal_queries:
        snippets, _ = gather_snippets_and_links(search_tool, query, max_results=10)
        alliance_deal_snippets.extend(snippets)


    events_chain = EVENTS_PROMPT | llm
    events_response = events_chain.invoke({
        "country_name": country_name,
        "historical_snippets": "\n".join(historical_snippets) if historical_snippets else "No direct historical information available."
    }).content.strip()


    resolutions_chain = RESOLUTIONS_PROMPT | llm
    resolutions_response = resolutions_chain.invoke({
        "country_name": country_name,
        "resolution_snippets": "\n".join(resolution_snippets) if resolution_snippets else "No direct resolution information available."
    }).content.strip()


    alliances_chain = ALLIANCES_PROMPT | llm
    alliances_response = alliances_chain.invoke({
        "country_name": country_name,
        "alliance_deal_snippets": "\n".join(alliance_deal_snippets) if alliance_deal_snippets else "No direct alliance deals information available."
    }).content.strip()

    try:
        events_data = json.loads(clean_json_response(events_response))
        resolutions_data = json.loads(clean_json_response(resolutions_response))
        alliances_data = json.loads(clean_json_response(alliances_response))

        memorable_events = events_data.get("memorable_events", [])
        previous_resolutions = resolutions_data.get("previous_resolutions", [])
        alliances_and_deals = alliances_data.get("alliances_and_deals", [])
        
        if not previous_resolutions or not memorable_events or not alliances_and_deals:
            region_defaults = get_region_defaults(basic_info.region)

            backup_chain = BACKUP_EVENTS_PROMPT | llm
            backup_response = backup_chain.invoke({
                "country_name": country_name,
                "region": basic_info.region,
                "regional_treaties": ", ".join(region_defaults["treaties_and_agreements"]),
                "regional_goals": ", ".join(region_defaults["core_goals"]),
                "regional_values": ", ".join(region_defaults["cultural_values"])
            }).content.strip()
            backup_data = json.loads(clean_json_response(backup_response))
            
            previous_resolutions = previous_resolutions or backup_data.get("previous_resolutions", [])
            memorable_events = memorable_events or backup_data.get("memorable_events", [])
            alliances_and_deals = alliances_and_deals or backup_data.get("alliances_and_deals", [])
    except Exception as e:
        print_yellow(f"[ERROR parsing MEMORY SEEDS]: {e}\nResponse was: {events_response} {resolutions_response} {alliances_response}")
        # Generate complete backup data on error using region defaults
        region_defaults = get_region_defaults(basic_info.region)

        backup_chain = BACKUP_MEMORY_SEEDS_PROMPT | llm
        try:
            backup_response = backup_chain.invoke({
                "country_name": country_name,
                "region": basic_info.region,
                "regional_treaties": ", ".join(region_defaults["treaties_and_agreements"]),
                "regional_goals": ", ".join(region_defaults["core_goals"]),
                "regional_values": ", ".join(region_defaults["cultural_values"])
            }).content.strip()
            backup_data = json.loads(clean_json_response(backup_response))
            previous_resolutions = backup_data.get("previous_resolutions", [])
            memorable_events = backup_data.get("memorable_events", [])
            alliances_and_deals = backup_data.get("alliances_and_deals", [])
        except Exception as backup_error:
            print_yellow(f"[ERROR in backup generation]: {backup_error}")
            previous_resolutions = [f"Generated resolution for {country_name} in {basic_info.region}"]
            memorable_events = [f"Generated memorable event for {country_name} in {basic_info.region}"]
            alliances_and_deals = [f"Generated alliance/deal for {country_name} in {basic_info.region}"]

    memory_seeds = MemorySeeds(
        previous_resolutions=previous_resolutions,
        memorable_events=memorable_events,
        alliances_and_deals=alliances_and_deals
    )
    print_green(f"[MEMORY SEEDS] found: Resolutions: {len(previous_resolutions)}, Events: {len(memorable_events)}, Deals: {len(alliances_and_deals)}")
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # CountryProfile
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    profile = CountryProfile(
        basic_info=basic_info,
        government=government_info,
        historical_context=historical_context,
        foreign_policy=foreign_policy,
        economic_profile=economic_profile,
        cultural_societal=cultural_societal,
        diplomatic_behavior=diplomatic_behavior,
        strategic_interests=strategic_interests,
        relationships_alliances=relationships_and_alliances,
        memory_seeds=memory_seeds
    )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Validate and update profile before saving
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    print_green(f" {'-'*20} [VALIDATING] {'-'*20} ")

    validator = ProfileValidator(model_name="gpt-4o", temperature=0.2)
    profile, _ = validator.validate(
        model=profile,
        prompt_template=PROFILE_VALIDATOR_PROMPT,
        is_debug=True,
        overwrite=True,
        save_path=profile_path
    )

    print_green(f" {'-'*20} [VALIDATED] {'-'*20} ")

    return profile
    
def __main__():
    countries = [
        "India", "United States", "China", "Russia", "Japan", 
        "Germany", "France", "United Kingdom", "Italy", "Spain", 
        "Canada", "Australia", "Brazil", "Argentina", "Chile", 
        "Peru", "Colombia"
    ]
    
    print_yellow(f"[INFO] Starting sequential profile generation for {len(countries)} countries")
    
    completed_profiles = []
    failed_countries = []
    
    for country in countries:
        try:
            print_yellow(f"\n[INFO] Building profile for {country}...")
            profile = CountryProfileBuilder(country)
            if profile:
                completed_profiles.append(profile)
                print_green(f"[SUCCESS] Completed profile for {country}")
        except Exception as e:
            failed_countries.append(country)
            print_yellow(f"[ERROR] Failed to build profile for {country}: {str(e)}")
            continue
    
    print_green("\n======= BUILD SUMMARY =======")
    print_green(f"Successfully built {len(completed_profiles)} out of {len(countries)} profiles")
    if failed_countries:
        print_yellow(f"Failed countries: {', '.join(failed_countries)}")
    
    for profile in completed_profiles:
        print_green(f"\n--- {profile.basic_info.name} Profile ---")
        print(profile.model_dump_json(indent=2))

if __name__ == "__main__":
    __main__()
