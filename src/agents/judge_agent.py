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
    """An impartial judge agent that evaluates diplomatic exchanges between countries.

    This agent observes diplomatic exchanges, scores each country's performance,
    provides round-by-round analysis, and delivers a final verdict at the end
    of the debate.

    Attributes:
        model (OpenAIChatWrapper): LLM for evaluations and verdicts
        memory (TemporaryMemory): Stores all diplomatic exchanges
        current_round (int): Current round number
        round_scores (List): Scores and analysis for each round
        num_rounds (int): Total number of debate rounds
        num_countries (int): Number of participating countries
        round_parser (RoundParser): Parser for round evaluations
        final_parser (FinalParser): Parser for final verdict
        _country_list (List[str]): List of participating country names

    Examples:
        >>> judge = JudgeAgent(num_rounds=3, num_countries=2, 
        ...                   country_list=["USA", "China"])
        >>> msg = Msg(name="USA", content="Diplomatic statement")
        >>> judge.observe(msg)
        >>> evaluation = judge()  # Evaluates current round
    """

    def __init__(self, 
                 num_rounds: int, 
                 num_countries: int, 
                 country_list: List[str], 
                 model_config: Optional[Dict[str, Any]] = MODEL_CONFIG):
        """Initialize the judge agent.

        Args:
            num_rounds (int): Total number of debate rounds
            num_countries (int): Number of participating countries
            country_list (List[str]): Names of participating countries
            model_config (Optional[Dict[str, Any]], optional): LLM configuration. 
                Defaults to MODEL_CONFIG.
        """
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
        """Store a diplomatic message in memory.

        Args:
            msg (Msg): Message to store
        """
        self.memory.add(msg)

    def __call__(self, msg: Optional[Msg] = None) -> None:
        """Process messages and generate round evaluations or final verdict.

        When called without a message, evaluates the current round or
        produces the final verdict if all rounds are complete.

        Args:
            msg (Optional[Msg], optional): Message to observe. Defaults to None.

        Returns:
            Optional[Msg]: Round evaluation or final verdict message,
                or None if just observing a message
        """
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
        """Evaluate a single round of diplomatic exchanges.

        Analyzes all country statements in the current round and provides
        scores and analysis for each country's diplomatic performance.

        Args:
            round_number (int): The round number to evaluate

        Returns:
            Msg: Evaluation message containing:
                - round_summary: Overall analysis of the round
                - scores: Individual country scores with reasoning
                - analysis: Detailed analysis of each country's performance

        Raises:
            ValueError: If number of exchanges doesn't match number of countries
        """
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
        """Generate the final verdict for the entire debate.

        Analyzes all rounds and provides comprehensive evaluation of each
        country's overall performance and diplomatic effectiveness.

        Returns:
            Msg: Final verdict message containing:
                - verdict_summary: Overall debate analysis
                - final_scores: Final scores for each country
                - rankings: Ordered list of countries by performance
                - country_performance: Detailed performance analysis
                - summary_insights: Key highlights and lessons learned
        """
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
                "country_performance" : parsed_response["country_performance"],
                "summary_insights" : parsed_response["summary_insights"]
            }
        )
    
    def _construct_evaluation_prompt(self, round_number: int, exchanges: List[Msg]) -> List[Dict[str, str]]:
        """Construct a prompt for evaluating a debate round.

        Creates a prompt that includes:
        1. Round context and evaluation criteria
        2. Previous round summary if available
        3. Current round statements from each country
        4. Strategic analysis and metadata for each statement

        Args:
            round_number (int): Current round number
            exchanges (List[Msg]): List of diplomatic exchanges to evaluate

        Returns:
            List[Dict[str, str]]: List of messages for the LLM prompt
        """
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
        """Construct a prompt for the final debate verdict.

        Creates a prompt that includes:
        1. Overall debate context
        2. Results and analysis from all rounds
        3. Request for final verdict in specified format

        Returns:
            List[Dict[str, str]]: List of messages for the LLM prompt
        """
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