from langchain_core.prompts import PromptTemplate

BASIC_INFO_PROMPT = PromptTemplate.from_template(
    "You are a JSON formatting assistant. Your task is to extract information about {country_name} from the following snippets and format it as JSON.\n"
    "Snippets about geographical region ensure that you just get the regions either in a List of strings or a string:\n{region_snippets}\n\n"
    "Snippets about population:\n{population_snippets}\n\n"
    "Format your response as valid JSON with these exact keys:\n"
    "{{\n"
    "  \"region\": \"string value\",\n"
    "  \"population\": number or \"\n"
    "}}\n"
    "IMPORTANT: Return ONLY the JSON object, no other text. Ensure it's properly formatted with quotes around strings."
)

GOVERNMENT_TYPE_PROMPT = PromptTemplate.from_template(
    "You are a JSON formatting assistant analyzing the government of {country_name}.\n\n"
    "Consider these aspects when analyzing the government type:\n"
    "- Traditional/indigenous governance systems if applicable\n"
    "- Religious or cultural influences on governance\n"
    "- Federal vs. unitary system\n"
    "- Constitutional framework\n\n"
    "Snippets about government:\n{government_snippets}\n\n"
    "If you think any of the snippets are outdated, use your knowledge to generate plausible information.\n\n"
    "Format your response as valid JSON like this:\n"
    "{{\n"
    "  \"government_type\": \"detailed description including traditional and modern elements\"\n"
    "}}\n"
    "IMPORTANT: Return ONLY the JSON object. Ensure proper formatting with quotes."
)

LEADERSHIP_PROMPT = PromptTemplate.from_template(
    "You are a JSON formatting assistant. Extract the current leadership of {country_name}.\n\n"
    "Consider these leadership roles:\n"
    "- Head of State (monarch, president, etc.)\n"
    "- Head of Government (prime minister, chancellor, etc.)\n"
    "- Traditional/Religious leaders if applicable\n"
    "- Key cabinet positions\n\n"
    "Snippets about leadership:\n{leadership_snippets}\n\n"
    "If you think any of the snippets are outdated, use your knowledge to generate plausible information.\n\n"
    "Format your response as valid JSON like this:\n"
    "{{\n"
    "  \"current_leadership\": [\n"
    "    \"Leader 1 with role and context\",\n"
    "    \"Leader 2 with role and context\"\n"
    "  ]\n"
    "}}\n"
    "IMPORTANT: Return ONLY the JSON object. Ensure proper formatting with quotes."
)

IDEOLOGIES_PROMPT = PromptTemplate.from_template(
    "You are a JSON formatting assistant. Extract the political ideologies of {country_name} from these snippets:\n\n{ideologies_snippets}\n\n"
    "Format your response as valid JSON like this:\n"
    "If you think any of the snippets are outdated, use your knowledge to generate plausible information.\n\n"
    "{{\n"
    "  \"political_ideologies\": [\"ideology 1\", \"ideology 2\"]\n"
    "}}\n"
    "IMPORTANT: Return ONLY the JSON object, no other text. Ensure it's properly formatted with quotes around strings and array elements."
)

COLONIAL_HISTORY_PROMPT = PromptTemplate.from_template(
    "You are a JSON formatting assistant. Extract {country_name}'s colonial history from these snippets:\n\n{colonial_snippets}\n\n"
    "If you think any of the snippets are outdated, use your knowledge to generate plausible information.\n\n"
    "Format your response as valid JSON like this:\n"
    "{{\n"
    "  \"colonial_history\": \"detailed description of colonial history\"\n"
    "}}\n"
    "IMPORTANT: Return ONLY the JSON object, no other text. Ensure it's properly formatted with quotes around strings."
)

    # Major Conflicts with improved prompt
MAJOR_CONFLICTS_PROMPT = PromptTemplate.from_template(
    "You are a JSON formatting assistant. Extract {country_name}'s major historical conflicts from these snippets:\n\n{conflicts_snippets}\n\n"
    "If you think any of the snippets are outdated, use your knowledge to generate plausible information.\n\n"
    "Format your response as valid JSON like this:\n"
    "{{\n"
    "  \"major_conflicts\": [\n"
    "    \"First major conflict description\",\n"
    "    \"Second major conflict description\"\n"
    "  ]\n"
    "}}\n"
    "IMPORTANT: Return ONLY the JSON object, no other text. Ensure it's properly formatted with quotes around strings and array elements."
)

# Evolution of Foreign Policy with improved prompt
FOREIGN_POLICY_PROMPT = PromptTemplate.from_template(
    "You are a JSON formatting assistant. Extract how {country_name}'s foreign policy has evolved from these snippets:\n\n{foreign_policy_snippets}\n\n"
    "If you think any of the snippets are outdated, use your knowledge to generate plausible information.\n\n"
    "Format your response as valid JSON like this:\n"
    "{{\n"
    "  \"evolution_of_foreign_policy\": \"detailed description of foreign policy evolution\"\n"
    "}}\n"
    "IMPORTANT: Return ONLY the JSON object, no other text. Ensure it's properly formatted with quotes around strings."
)

CORE_GOALS_PROMPT = PromptTemplate.from_template(
    "You are a JSON formatting assistant. Extract core foreign policy goals of {country_name} from these snippets:\n\n"
    "{core_goals_snippets}\n\n"
    "If you think any of the snippets are outdated, use your knowledge to generate plausible information.\n\n"
    "Format your response as valid JSON like this:\n"
    "{{\n"
    "  \"core_goals\": [\"goal 1 with context\", \"goal 2 with context\"]\n"
    "}}\n"
    "IMPORTANT: Return ONLY the JSON object, no other text. Ensure it's properly formatted with quotes around strings."
)

ALLIANCE_PROMPT = PromptTemplate.from_template(
    "You are a JSON formatting assistant. Extract alliance patterns of {country_name} from these snippets:\n\n"
    "{alliance_snippets}\n\n"
    "If you think any of the snippets are outdated, use your knowledge to generate plausible information.\n\n"
    "Format your response as valid JSON like this:\n"
    "{{\n"
    "  \"alliance_patterns\": [\"pattern 1 with context\", \"pattern 2 with context\"]\n"
    "}}\n"
    "IMPORTANT: Return ONLY the JSON object, no other text. Ensure it's properly formatted with quotes around strings."
)

GLOBAL_ISSUES_PROMPT = PromptTemplate.from_template(
    "You are a JSON formatting assistant. Extract global issue positions of {country_name} from these snippets:\n\n"
    "{global_issues_snippets}\n\n"
    "If you think any of the snippets are outdated, use your knowledge to generate plausible information.\n\n"
    "Format your response as valid JSON like this:\n"
    "{{\n"
    "  \"global_issue_positions\": [\"position 1 with context\", \"position 2 with context\"]\n"
    "}}\n"
    "IMPORTANT: Return ONLY the JSON object, no other text. Ensure it's properly formatted with quotes around strings."
)

TREATIES_PROMPT = PromptTemplate.from_template(
    "You are a JSON formatting assistant. Extract treaties and agreements of {country_name} from these snippets:\n\n"
    "{treaties_snippets}\n\n"
    "If you think any of the snippets are outdated, use your knowledge to generate plausible information.\n\n"
    "Format your response as valid JSON like this:\n"
    "{{\n"
    "  \"treaties_and_agreements\": [\"treaty 1 with context\", \"treaty 2 with context\"]\n"
    "}}\n"
    "IMPORTANT: Return ONLY the JSON object, no other text. Ensure it's properly formatted with quotes around strings."
)

ECONOMIC_PROFILE_PROMPT = PromptTemplate.from_template(
    "You are a JSON formatting assistant. Your task is to analyze economic aspects of {country_name}.\n\n"
    "If provided, use these snippets:\n"
    "GDP Information:\n{gdp_snippets}\n\n"
    "Industry Information:\n{industry_snippets}\n\n"
    "Trade Information:\n{trade_snippets}\n\n"
    "Development Goals:\n{dev_snippets}\n\n"
    "If the snippets are empty or insufficient, use your knowledge to generate plausible information.\n\n"
    "Format your response as valid JSON like this:\n"
    "{{\n"
    "  \"gdp\": {{\n"
    "    \"value\": 1234.56,\n"
    "    \"unit\": \"billion USD\",\n"
    "    \"year\": \"2024\"\n"
    "  }},\n"
    "  \"major_industries\": [\n"
    "    \"Industry name: Brief description of importance and role\",\n"
    "    \"Another industry: Its significance and impact\"\n"
    "  ],\n"
    "  \"trade_relations\": [\n"
    "    \"Partner/Agreement name: Key details about the relationship\",\n"
    "    \"Another partner: Important aspects of trade\"\n"
    "  ],\n"
    "  \"development_goals\": [\n"
    "    \"Specific goal with context and timeline\",\n"
    "    \"Another development objective with details\"\n"
    "  ]\n"
    "}}\n"
    "IMPORTANT:\n"
    "1. Return ONLY the JSON object\n"
    "2. GDP value should be a number (float)\n"
    "3. GDP unit should be the unit followed by currency e.g. 'billion USD' or 'trillion AUD'\n"
    "4. GDP year should be the latest available year\n"
    "5. All array elements must be plain strings (not objects)\n"
    "6. Include brief descriptions within the strings themselves\n"
    "7. Use colon (:) to separate titles from descriptions in the strings"
)

BACKUP_ECONOMIC_PROFILE_PROMPT = PromptTemplate.from_template(
    "As an economic expert on {region}, generate economic information for {country_name}.\n"
    "Consider these regional characteristics:\n"
    "- Common development goals: {regional_goals}\n"
    "- Typical trade agreements: {regional_treaties}\n\n"
    "Format as JSON:\n"
    "{{\n"
    "  \"gdp\": {{\n"
    "    \"value\": estimated GDP value,\n"
    "    \"unit\": \"trillion USD\",\n"
    "    \"year\": \"2024\"\n"
    "  }},\n"
    "  \"major_industries\": [\"industry 1 with regional context\", \"industry 2 with regional context\"],\n"
    "  \"trade_relations\": [\"trade relation 1 with regional focus\", \"trade relation 2 with regional focus\"],\n"
    "  \"development_goals\": [\"development goal 1 based on regional priorities\", \"development goal 2 based on regional priorities\"]\n"
    "}}"
)

CULTURAL_VALUES_PROMPT = PromptTemplate.from_template(
    "You are a JSON formatting assistant. Extract cultural values of {country_name} from these snippets:\n\n"
    "{cultural_snippets}\n\n"
    "If you think any of the snippets are outdated, use your knowledge to generate plausible information.\n\n"
    "Format your response as valid JSON like this:\n"
    "{{\n"
    "  \"cultural_values\": [\n"
    "    \"value 1 with brief explanation\",\n"
    "    \"value 2 with brief explanation\"\n"
    "  ]\n"
    "}}\n"
    "IMPORTANT: Return ONLY the JSON object, no other text. Ensure proper formatting with quotes."
)

PUBLIC_OPINION_PROMPT = PromptTemplate.from_template(
    "You are a JSON formatting assistant. Extract public opinion trends of {country_name} from these snippets:\n\n"
    "{opinion_snippets}\n\n"
    "If you think any of the snippets are outdated, use your knowledge to generate plausible information.\n\n"
    "Format your response as valid JSON like this:\n"
    "{{\n"
    "  \"public_opinion\": \"comprehensive description of public attitudes and views\"\n"
    "}}\n"
    "IMPORTANT: Return ONLY the JSON object, no other text. Ensure proper formatting with quotes."
)

BACKUP_ECONOMIC_PROFILE_PROMPT = PromptTemplate.from_template(
    "As an economic expert on {region}, generate a complete economic profile for {country_name}.\n"
    "Format as JSON:\n"
    "{{\n"
    "  \"gdp\": {{\n"
    "    \"value\": estimated GDP value,\n"
    "    \"unit\": \"trillion USD\",\n"
    "    \"year\": \"2024\"\n"
    "  }},\n"
    "  \"major_industries\": [\"detailed industry 1\", \"detailed industry 2\"],\n"
    "  \"trade_relations\": [\"detailed trade relation 1\", \"detailed trade relation 2\"],\n"
    "  \"development_goals\": [\"detailed goal 1\", \"detailed goal 2\"]\n"
    "}}"
)
COMMUNICATION_STYLE_PROMPT = PromptTemplate.from_template(
    "You are a JSON formatting assistant. Extract communication style of {country_name} from these snippets:\n\n"
    "{comm_snippets}\n\n"
    "If you think any of the snippets are outdated, use your knowledge to generate plausible information.\n\n"
    "Format your response as valid JSON like this:\n"
    "{{\n"
    "  \"communication_style\": \"detailed description of communication and negotiation approach\"\n"
    "}}\n"
    "IMPORTANT: Return ONLY the JSON object, no other text. Ensure proper formatting with quotes."
)

BACKUP_CULTURAL_VALUES_PROMPT = PromptTemplate.from_template(
    "As a cultural expert on {region}, generate cultural information for {country_name}.\n"
    "Consider these regional characteristics:\n"
    "- Common cultural values: {regional_values}\n"
    "- Typical governance systems: {governance_systems}\n\n"
    "Format as JSON:\n"
    "{{\n"
    "  \"cultural_values\": [\"value 1 with context\", \"value 2 with context\"],\n"
    "  \"public_opinion\": \"description considering regional context\",\n"
    "  \"communication_style\": \"description based on regional norms\"\n"
    "}}"
)

# Diplomatic Behavior with improved prompt and backup
DIPLOMATIC_BEHAVIOR_PROMPT = PromptTemplate.from_template(
    "You are a JSON formatting assistant. Your task is to analyze diplomatic behavior of {country_name}.\n\n"
    "If provided, use these snippets:\n"
    "Diplomatic Style Information:\n{diplomatic_snippets}\n\n"
    "Negotiation Information:\n{negotiation_snippets}\n\n"
    "Objectives Information:\n{objectives_snippets}\n\n"
    "If the snippets are empty or insufficient, use your knowledge to generate plausible information.\n\n"
    "Format your response as valid JSON like this:\n"
    "{{\n"
    "  \"style\": \"detailed description of diplomatic style\",\n"
    "  \"negotiation_tactics\": [\"tactic 1 with context\", \"tactic 2 with context\"],\n"
    "  \"decision_making_process\": \"detailed description of how decisions are made\",\n"
    "  \"short_term_objectives\": [\"objective 1\", \"objective 2\"],\n"
    "  \"long_term_vision\": [\"vision 1\", \"vision 2\"]\n"
    "}}\n"
    "IMPORTANT: Return ONLY the JSON object. Ensure proper formatting with quotes."
)

BACKUP_DIPLOMATIC_BEHAVIOR_PROMPT = PromptTemplate.from_template(
    "As a diplomatic expert, generate plausible diplomatic behavior information for {country_name}.\n"
    "Format as JSON:\n"
    "{{\n"
    "  \"style\": \"diplomatic style description\",\n"
    "  \"negotiation_tactics\": [\"tactic 1\", \"tactic 2\"],\n"
    "  \"decision_making_process\": \"process description\",\n"
    "  \"short_term_objectives\": [\"objective 1\", \"objective 2\"],\n"
    "  \"long_term_vision\": [\"vision 1\", \"vision 2\"]\n"
    "}}"
)
SECURITY_PROMPT = PromptTemplate.from_template(
    "You are a JSON formatting assistant. Analyze security concerns for {country_name} based on these snippets:\n{security_snippets}\n\n"
    "If the snippets are empty or insufficient, use your knowledge to generate plausible information.\n\n"
    "Format your response as a valid JSON object like this:\n"
    "{{\n"
    "  \"concerns\": [\n"
    "    \"First security concern with context\",\n"
    "    \"Second security concern with context\"\n"
    "  ]\n"
    "}}\n"
    "IMPORTANT: Return ONLY the JSON object with proper formatting and quotes."
)

ECONOMIC_PROMPT = PromptTemplate.from_template(
    "You are a JSON formatting assistant. Analyze economic interests for {country_name} based on these snippets:\n{economic_snippets}\n\n"
    "If the snippets are empty or insufficient, use your knowledge to generate plausible information.\n\n"
    "Format your response as a valid JSON object like this:\n"
    "{{\n"
    "  \"interests\": [\"interest 1 with explanation\", \"interest 2 with explanation\"]\n"
    "}}\n"
    "IMPORTANT: Return ONLY the JSON object with proper formatting and quotes."
)

CULTURAL_PROMPT = PromptTemplate.from_template(
    "You are a JSON formatting assistant. Analyze cultural promotion aspects for {country_name} based on these snippets:\n{cultural_snippets}\n\n"
    "If the snippets are empty or insufficient, use your knowledge to generate plausible information.\n\n"
    "Format your response as a valid JSON object like this:\n"
    "{{\n"
    "  \"promotion\": [\"promotion aspect 1\", \"promotion aspect 2\"]\n"
    "}}\n"
    "IMPORTANT: Return ONLY the JSON object with proper formatting and quotes."
)

# Historical Events prompt
EVENTS_PROMPT = PromptTemplate.from_template(
    "You are a JSON formatting assistant. Extract memorable historical events of {country_name} from these snippets:\n\n"
    "{historical_snippets}\n\n"
    "If you think any of the snippets are outdated, use your knowledge to generate plausible information.\n\n"
    "Format your response as valid JSON like this:\n"
    "{{\n"
    "  \"memorable_events\": [\"event 1 with significance\", \"event 2 with significance\"]\n"
    "}}\n"
    "IMPORTANT: Return ONLY the JSON object. Ensure proper formatting with quotes."
)

# Resolutions prompt
RESOLUTIONS_PROMPT = PromptTemplate.from_template(
    "You are a JSON formatting assistant. Extract previous resolutions and agreements of {country_name} from these snippets:\n\n"
    "{resolution_snippets}\n\n"
    "If you think any of the snippets are outdated, use your knowledge to generate plausible information.\n\n"
    "Format your response as valid JSON like this:\n"
    "{{\n"
    "  \"previous_resolutions\": [\"resolution 1 with context\", \"resolution 2 with context\"]\n"
    "}}\n"
    "IMPORTANT: Return ONLY the JSON object. Ensure proper formatting with quotes."
)

# Alliances prompt
ALLIANCES_PROMPT = PromptTemplate.from_template(
    "You are a JSON formatting assistant. Extract alliances and deals of {country_name} from these snippets:\n\n"
    "{alliance_deal_snippets}\n\n"
    "If you think any of the snippets are outdated, use your knowledge to generate plausible information.\n\n"
    "Format your response as valid JSON like this:\n"
    "{{\n"
    "  \"alliances_and_deals\": [\"deal 1 with impact\", \"deal 2 with impact\"]\n"
    "}}\n"
    "IMPORTANT: Return ONLY the JSON object. Ensure proper formatting with quotes."
)

BACKUP_CULTURAL_VALUES_PROMPT_GENERATE = PromptTemplate.from_template(
    "As an expert on {country_name}, generate plausible cultural and societal information.\n"
    "Format as JSON:\n"
    "{{\n"
    "  \"cultural_values\": [\n"
    "    \"key cultural value 1 with context\",\n"
    "    \"key cultural value 2 with context\"\n"
    "  ],\n"
    "  \"public_opinion\": \"comprehensive description of likely public attitudes\",\n"
    "  \"communication_style\": \"detailed description of probable communication patterns\"\n"
    "}}"
)

BACKUP_EVENTS_PROMPT = PromptTemplate.from_template(
    "As a historical expert focused on {region}, generate historical memory points for {country_name}.\n"
    "Consider regional characteristics:\n"
    "- Regional treaties: {regional_treaties}\n"
    "- Regional goals: {regional_goals}\n"
    "- Regional values: {regional_values}\n\n"
    "Format as JSON:\n"
    "{{\n"
    "  \"previous_resolutions\": [\"resolution 1 with regional context\", \"resolution 2 with regional context\"],\n"
    "  \"memorable_events\": [\"event 1 with regional significance\", \"event 2 with regional significance\"],\n"
    "  \"alliances_and_deals\": [\"deal 1 with regional impact\", \"deal 2 with regional impact\"]\n"
    "}}"
)

BACKUP_MEMORY_SEEDS_PROMPT = PromptTemplate.from_template(
    "As a historical expert focused on {region}, generate a complete historical memory profile for {country_name}.\n"
    "Consider regional characteristics:\n"
    "- Regional treaties: {regional_treaties}\n"
    "- Regional goals: {regional_goals}\n"
    "- Regional values: {regional_values}\n"
    "Format as JSON:\n"
    "{{\n"
    "  \"previous_resolutions\": [\"detailed resolution 1 with regional context\", \"detailed resolution 2 with regional context\"],\n"
    "  \"memorable_events\": [\"detailed event 1 with regional significance\", \"detailed event 2 with regional significance\"],\n"
    "  \"alliances_and_deals\": [\"detailed deal 1 with regional impact\", \"detailed deal 2 with regional impact\"]\n"
    "}}"
)

RELATIONSHIPS_AND_ALLIANCES_PROMPT = PromptTemplate.from_template(
    "You are a JSON formatting assistant. Analyze the relationships and alliances of {country_name}.\n\n"
    "Consider these aspects:\n"
    "- Past alliances and treaties\n"
    "- Current diplomatic relations\n"
    "- Rivalries and conflicts\n"
    "- Reputation and standing in the international community\n\n"
    "Snippets about relationships and alliances:\n{alliance_snippets}\n{rivalry_snippets}\n{reputation_snippets}\n\n"
    "If you think any of the snippets are outdated, use your knowledge to generate plausible information.\n\n"
    "Format your response as a valid JSON object like this:\n"
    "{{\n"
    "  \"past_alliances\": [\"alliance 1 with context\", \"alliance 2 with context\"],\n"
    "  \"rivalries_conflicts\": [\"rivalry 1 with context\", \"rivalry 2 with context\"],\n"
    "  \"diplomatic_reputation\": \"detailed description of reputation and standing\"\n"
    "}}\n"
    "IMPORTANT: Return ONLY the JSON object. Ensure proper formatting with quotes."
)

BACKUP_STRATEGIC_INTERESTS_PROMPT = PromptTemplate.from_template(
    "You are a JSON formatting assistant. Analyze the strategic interests of {country_name}.\n\n"
    "Consider these aspects:\n"
    "- Security concerns\n"
    "- Economic interests\n"
    "- Cultural and ideological promotion\n\n"
    "Snippets about strategic interests:\n{security_snippets}\n{economic_snippets}\n{cultural_snippets}\n\n"
    "If you think any of the snippets are outdated, use your knowledge to generate plausible information.\n\n"
    "Format your response as a valid JSON object like this:\n"
    "{{\n"
    "  \"security_concerns\": [\"detailed security concern 1 with regional context\", \"detailed security concern 2 with regional context\"],\n"
    "  \"economic_interests\": [\"detailed economic interest 1 with regional context\", \"detailed economic interest 2 with regional context\"],\n"
    "  \"cultural_ideological_promotion\": [\"detailed cultural promotion 1 with regional context\", \"detailed cultural promotion 2 with regional context\"]\n"
    "}}\n"
    "IMPORTANT: Return ONLY the JSON object. Ensure proper formatting with quotes."
)

BACKUP_RELATIONSHIPS_AND_ALLIANCES_PROMPT = PromptTemplate.from_template(
    "You are a JSON formatting assistant. Generate complete relationships and alliances profile for {country_name}.\n\n"
    "Consider these aspects:\n"
    "- Historical alliances and partnerships\n"
    "- Major conflicts and rivalries\n"
    "- International reputation and influence\n\n"
    "Format your response as a valid JSON object like this:\n"
    "{{\n"
    "  \"past_alliances\": [\"detailed alliance 1 with context\", \"detailed alliance 2 with context\"],\n"
    "  \"rivalries_conflicts\": [\"detailed rivalry 1 with context\", \"detailed rivalry 2 with context\"],\n"
    "  \"diplomatic_reputation\": \"comprehensive description of diplomatic standing\"\n"
    "}}\n"
    "IMPORTANT: Return ONLY the JSON object. Ensure proper formatting with quotes."
)