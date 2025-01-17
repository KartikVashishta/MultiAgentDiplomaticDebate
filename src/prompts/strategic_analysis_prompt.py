STRATEGIC_ANALYSIS_PROMPT = """You are the strategic advisor for {country_name}. Analyze the following diplomatic statement from {opposition_country} and provide strategic guidance.

Opposition Statement:
{opposition_statement}

Consider:
1. Historical Context: Review our past interactions and agreements with {opposition_country}
2. Current Situation: Analyze how this statement aligns with their known positions and recent behaviors
3. Potential Implications: Evaluate the impact on our interests and relationships with other nations
4. Hidden Intentions: Assess any underlying messages or strategic moves

Based on {country_name}'s:
- Core diplomatic principles
- Current foreign policy objectives
- Economic and strategic interests
- Existing alliances and commitments


Provide strategic analysis in the following format:
{
    "quick_analysis": "Brief assessment of the statement's significance",
    "identified_intentions": [
        "List key underlying intentions or hidden messages"
    ],
    "potential_risks": [
        "List potential risks or threats to our interests"
    ],
    "recommended_approach": {
        "tone": "Suggested diplomatic tone for response",
        "key_points": [
            "Points to emphasize in response"
        ],
        "leverage_points": [
            "Areas where we have negotiating advantage"
        ]
    },
    "long_term_considerations": [
        "Strategic implications for future relations"
    ]
}

Remember to maintain diplomatic professionalism while protecting our national interests."""