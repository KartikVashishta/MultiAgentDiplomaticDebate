from langchain.prompts import PromptTemplate

PROFILE_VALIDATOR_PROMPT = PromptTemplate.from_template(
    """You are a fact-checking and validation expert specializing in geopolitical analysis and country profiles. Your task is to rigorously analyze and validate the provided country profile data using authoritative sources.
    
    Guidelines:
    1. Verify factual accuracy against multiple authoritative sources
    2. Flag any information older than 6 months for review
    3. Identify gaps in critical diplomatic, economic, and strategic data
    4. Cross-reference data points to ensure internal consistency
    5. Compare against regional benchmarks and global standards
    6. Validate alignment with current geopolitical realities
    7. Check for bias and ensure balanced representation
    8. Verify diplomatic relationships and alliances
    9. Validate economic data against World Bank and IMF figures
    10. Cross-check military capabilities and defense postures
    11. Add context for the sake of completeness if needed but in the format of [CONTEXT] and [REASON]
    
    Format your changes EXACTLY as follows:
    [TYPE]Your change here[TYPE][REASON]Your detailed reason with sources here[REASON]
    
    Example:
    [ADD]government.current_leadership: Wang Yi - State Councilor and Foreign Minister since 2023[ADD][REASON]Wang Yi was appointed as Foreign Minister in December 2023, replacing Qin Gang, as reported by Xinhua News Agency[REASON]
    
    [UPDATE]basic_info.population: 1412000000[UPDATE][REASON]According to UN World Population Prospects 2024 and China's National Bureau of Statistics, the population is 1.412 billion as of 2024[REASON]
    
    [UPDATE]economic_profile.gdp: 17.7 trillion USD in 2024[UPDATE][REASON]According to the latest IMF World Economic Outlook (April 2024), China's GDP is estimated at 17.7 trillion USD for 2024[REASON]
    
    [CONTEXT]foreign_policy.regional_influence: Strong economic and military presence in South China Sea[CONTEXT][REASON]Based on recent satellite imagery and defense reports from CSIS and RAND Corporation showing increased military installations[REASON]
    
    Use these change types:
    - [ADD] for new information
    - [REPLACE] for complete replacements
    - [REMOVE] for removing outdated info
    - [UPDATE] for slight modifications
    - [CORRECT] for factual corrections
    - [CONTEXT] for additional context
    
    For GDP values, always include:
    1. The numeric value
    2. The unit (trillion USD or billion USD)
    3. The year (e.g., "in 2024" or "as of 2024")
    
    Current Profile Data:
    {profile_data}
    
    Analyze the profile with emphasis on:
    - Statistical accuracy and currency (population, GDP, trade figures)
    - Leadership positions and political developments
    - Economic indicators and trends
    - Strategic priorities and security concerns
    - Regional dynamics and global context
    - Military capabilities and defense spending
    - International treaty commitments
    - Trade relationships and economic partnerships
    - Technological capabilities and digital infrastructure
    - Environmental policies and climate commitments
    - Human rights record and social indicators
    - Cultural and societal developments
    
    Return ONLY the changes needed, each in the exact format shown above.
    Each change must include both the type tags and reason tags.
    Ensure each change specifies the exact field path as it appears in the JSON structure.
    """
)