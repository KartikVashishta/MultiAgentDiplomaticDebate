from agentscope.parsers import MarkdownJsonDictParser

MemoryStreamParser = MarkdownJsonDictParser(
    content_hint='{"quick_analysis": "Brief assessment", "identified_intentions": ["intentions"], "potential_risks": ["risks"], "recommended_approach": {"tone": "tone", "key_points": ["points"], "leverage_points": ["points"]}, "long_term_considerations": ["considerations"]}',
    keys_to_memory=["quick_analysis", "identified_intentions", "potential_risks", "recommended_approach", "long_term_considerations"],
    keys_to_content=None
)

RoundParser = MarkdownJsonDictParser(
            content_hint={
                "round_number": "current round number",
                "scores": {
                    "country_name": {
                        "score": "score from 1-10",
                        "reasoning": "explanation for score"
                    }
                },
                "analysis": {
                    "country_name": {
                        "diplomatic_effectiveness": "score 1-10",
                        "key_points": ["notable diplomatic moves"],
                        "strategic_alignment": "how well strategy aligns with country interests",
                        "thought_process": "analysis of country's diplomatic approach"
                    }
                },
                "round_summary": "overall round analysis"
            },
            keys_to_memory=["analysis", "round_summary"],
            keys_to_content="round_summary",
            keys_to_metadata=["scores", "round_number"]
        )

FinalParser = MarkdownJsonDictParser(
            content_hint={
                "final_scores": {
                    "country_name": {
                        "score": "final score 1-10",
                        "key_achievements": ["notable diplomatic successes"],
                        "strategic_effectiveness": "analysis of overall strategy",
                        "diplomatic_consistency": "evaluation of consistent messaging"
                    }
                },
                "rankings": ["ordered list of countries by performance"],
                "verdict_summary": "comprehensive analysis",
                "country_performance": {
                    "country_name": {
                        "round_scores": ["score progression"],
                        "strategic_development": "how strategy evolved",
                        "key_moments": ["defining exchanges"]
                    }
                }
            },
            keys_to_memory=["country_performance", "verdict_summary"],
            keys_to_content="verdict_summary",
            keys_to_metadata=["final_scores", "rankings"]
        )

CountryParser = MarkdownJsonDictParser(
            content_hint='{"thought": "internal analysis", "diplomatic_response": "official statement", "key_points": ["main points"], "strategic_alignment": "alignment explanation"}',
            keys_to_memory=["thought", "diplomatic_response", "key_points", "strategic_alignment"],
            keys_to_content="diplomatic_response",
            keys_to_metadata=["key_points", "strategic_alignment"]
        )

ResponseValidatorParser = MarkdownJsonDictParser(
            content_hint='{"validated_response": "response", "validation_notes": ["notes"]}',
            keys_to_memory=["validation_notes"],
            keys_to_content="validated_response"
        )