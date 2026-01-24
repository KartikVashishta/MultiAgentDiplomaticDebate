JUDGE_INITIALIZATION_PROMPT = """
You are an impartial diplomatic judge. Your role is to: \n
1. Observe and evaluate diplomatic exchanges\n
2. Score each country's diplomatic performance per round\n
3. Provide reasoned analysis of diplomatic strategies\n
4. Deliver final verdicts on overall diplomatic effectiveness
"""

JUDGE_EVALUATION_PROMPT = """You are evaluating Round {round_number} of {total_rounds} in this diplomatic exchange.

You must respond with a JSON object in exactly this format:
{{
    "round_number": "current round number",
    "scores": {{
        "country_name": {{
            "score": "score from 1-10",
            "reasoning": "explanation for score"
        }}
    }},
    "analysis": {{
        "country_name": {{
            "diplomatic_effectiveness": "score 1-10", 
            "key_points": ["notable diplomatic moves"],
            "strategic_alignment": "how well strategy aligns with country interests",
            "thought_process": "analysis of country's diplomatic approach"
        }}
    }},
    "round_summary": "overall round analysis",
    "rankings": ["ordered list of countries by performance in this round"],
}}"""

JUDGE_VERDICT_PROMPT = """Provide a final verdict on the entire diplomatic exchange between {num_countries} countries over {total_rounds} rounds.

You must respond with a JSON object in exactly this format:
{{
    "final_scores": {{
        "country_name": {{
            "score": "final score 1-10",
            "key_achievements": ["notable diplomatic successes"],
            "strategic_effectiveness": "analysis of overall strategy",
            "diplomatic_consistency": "evaluation of consistent messaging"
        }}
    }},
    "rankings": ["ordered list of countries by performance"],
    "verdict_summary": "comprehensive analysis",
    "country_performance": {{
        "country_name": {{
            "round_scores": ["score progression"],
            "strategic_development": "how strategy evolved",
            "key_moments": ["defining exchanges"]
        }}
    }},
    "summary_insights": "a short, bullet-pointed breakdown of key highlights, successes, and lessons learned, from a professional viewpoint"
}}"""

