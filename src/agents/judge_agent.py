import json
from agentscope.agents import DialogAgent
from agentscope.message import Msg
from agentscope.models import OpenAIChatWrapper
from agentscope.memory import TemporaryMemory

from src.parsers.parsers import FinalParser, RoundParser
from src.utils.utils import MODEL_CONFIG
from src.prompts import (
    JUDGE_INITIALIZATION_PROMPT,
    JUDGE_EVALUATION_PROMPT,
    JUDGE_VERDICT_PROMPT
)

from typing import Any, Dict, Optional, List

class JudgeAgent(DialogAgent):
    def __init__(self, 
                 num_rounds: int, 
                 num_countries: int, 
                 country_list: List[str], 
                 model_config: Optional[Dict[str, Any]] = MODEL_CONFIG):
        super().__init__(
            name='Judge',
            sys_prompt=JUDGE_INITIALIZATION_PROMPT,
            model_config_name=model_config["config_name"]
        )

        self.model = OpenAIChatWrapper(**model_config)
        self.memory = TemporaryMemory()
        self.current_round = 0
        self.round_scores = []
        self.num_rounds = num_rounds
        self.num_countries = num_countries
        self.round_parser = RoundParser
        self.final_parser = FinalParser
        self._country_list = country_list

    def observe(self, msg: Msg) -> None:
        self.memory.add(msg)

    def __call__(self, msg: Optional[Msg] = None) -> None:
        if msg:
            self.observe(msg)
            return None
        
        # If we've already evaluated all rounds, produce the final verdict
        if self.current_round >= self.num_rounds:
            return self._final_verdict()
        else:
            self.current_round += 1
            return self._evaluate_round(self.current_round)
        
    def _evaluate_round(self, round_number: int) -> Msg:

        raw_memory = self.memory.get_memory()

        country_messages = [m for m in raw_memory if m.name in self._country_list]

        start_idx = (round_number - 1) * self.num_countries
        end_idx   = round_number * self.num_countries
        current_round_exchanges = country_messages[start_idx:end_idx]

        if len(current_round_exchanges) != self.num_countries:
            raise ValueError(
                f"Expected {self.num_countries} exchanges for round {round_number}, "
                f"but got {len(current_round_exchanges)}"
            )
        
        evaluation_prompt = self._construct_evaluation_prompt(round_number, current_round_exchanges)
        response = self.model(messages=evaluation_prompt)
        parsed_response = self.round_parser.parse(response).parsed
        self.round_scores.append(parsed_response)

        return Msg(
            name = self.name,
            content = parsed_response["round_summary"],
            role = "assistant",
            metadata = {
                "round" : round_number,
                "scores" : parsed_response["scores"],
                "analysis" : parsed_response["analysis"]
            }
        )
    
    def _final_verdict(self) -> Msg:
        verdict_prompt = self._construct_verdict_prompt()
        response = self.model(messages = verdict_prompt)
        parsed_response = self.final_parser.parse(response).parsed

        return Msg(
            name = self.name,
            content = parsed_response["verdict_summary"],
            role = "assistant",
            metadata = {
                "final_scores" : parsed_response["final_scores"],
                "rankings" : parsed_response["rankings"],
                "country_performance" : parsed_response["country_performance"]
            }
        )
    
    def _construct_evaluation_prompt(self, round_number: int, exchanges: List[Msg]) -> List[Dict[str, str]]:
        messages = [
            {
                "role": "system",
                "content": JUDGE_EVALUATION_PROMPT.format(round_number=round_number, total_rounds=self.num_rounds)
            }
        ]

        if round_number > 1 and self.round_scores:
            prev_round = self.round_scores[-1]
            messages.append({
                "role": "system",
                "content": f"Previous Round {round_number-1} Summary: {prev_round['round_summary']}"
            })

        for msg in exchanges:
            messages.append({
                "role": "user",
                "content": f"{msg.name}'s Statement:\n{msg.content}"
            })
            
            if msg.metadata:
                messages.append({
                    "role": "system",
                    "content": (
                        f"{msg.name}'s Strategic Analysis:\n"
                        f"- Internal Thoughts: {msg.metadata.get('thought', '')}\n"
                        f"- Key Points: {', '.join(msg.metadata.get('key_points', []))}\n"
                        f"- Strategic Alignment: {msg.metadata.get('strategic_alignment', '')}"
                    )
                })
        
        return messages
    
    def _construct_verdict_prompt(self) -> List[Dict[str, str]]:
        """Construct prompt for final verdict using all round evaluations."""
        messages = [
            {
                "role": "system",
                "content": JUDGE_VERDICT_PROMPT.format(
                    num_countries=self.num_countries,
                    total_rounds=self.num_rounds
                )
            }
        ]

        for round_data in self.round_scores:
            messages.append({
                "role": "user",
                "content": (
                    f"Round {round_data['round_number']} Results:\n"
                    f"Scores: {json.dumps(round_data['scores'], indent=2)}\n"
                    f"Analysis: {json.dumps(round_data['analysis'], indent=2)}\n"
                    f"Summary: {round_data['round_summary']}"
                )
            })

        messages.append({
            "role": "system",
            "content": "Based on all rounds above, provide your final verdict in the exact JSON format specified."
        })
        
        return messages