import os
from agentscope import msghub
from agentscope.message import Msg

from src.agents.country_agent import CountryAgent
from src.agents.judge_agent import JudgeAgent
from src.utils.utils import BASIC_MODEL_CONFIG, MODEL_CONFIG

class DebateOrchestrator:
    """
    The DebateOrchestrator manages a multi-country diplomatic debate end-to-end:
      1. Creates CountryAgent objects for each country
      2. Creates a JudgeAgent
      3. Introduces the debate and states the problem
      4. For each round, each country speaks once
      5. The Judge scores and summarizes each round
      6. After the final round, the Judge provides a final verdict
      7. Logs the entire conversation to a .txt file
    """
    def __init__(
        self,
        countries,
        problem_statement: str,
        num_rounds: int,
        log_file_path: str = "debate_log.txt"
    ):
        """
        Args:
            countries (List[str]): e.g. ["United States", "China", "France"]
            problem_statement (str): A short description of the diplomatic issue
            num_rounds (int): Number of debate rounds
            log_file_path (str): Where to write the conversation transcript
        """
        self.countries = countries
        self.problem_statement = problem_statement
        self.num_rounds = num_rounds
        self.log_file = log_file_path

        self.country_agents = []
        for name in self.countries:
            agent = CountryAgent(country_name=name, model_config=BASIC_MODEL_CONFIG)
            self.country_agents.append(agent)

        self.judge_agent = JudgeAgent(
            num_rounds=num_rounds,
            num_countries=len(countries),
            model_config=MODEL_CONFIG,
            country_list=self.countries
        )

        self.all_agents = self.country_agents + [self.judge_agent]

        self._transcript_lines = []
    
    def run_debate(self):
        """
        Runs the entire debate:
        - Introduces problem
        - Conducts N rounds
        - Gets final verdict
        - Writes everything to a .txt file
        """
        with msghub(self.all_agents) as hub:
            introduction_msg = Msg(
                name="Host",
                role="system",
                content=(
                    f"Welcome to this diplomatic debate. We have {len(self.countries)} "
                    f"countries participating: {', '.join(self.countries)}.\n\n"
                    f"Problem Statement:\n{self.problem_statement}\n\n"
                    "Please proceed with each country's opening statement."
                )
            )
            hub.broadcast(introduction_msg)
            self._log_message(introduction_msg)

            for round_idx in range(1, self.num_rounds + 1):
                round_header = Msg(
                    name="Host",
                    role="system",
                    content=f"--- Round {round_idx} of {self.num_rounds} ---"
                )
                hub.broadcast(round_header)
                self._log_message(round_header)

                for country_agent in self.country_agents:
                    response_msg = country_agent()
                    self._log_message(response_msg)

                round_judgment = self.judge_agent(None)
                self._log_message(round_judgment)

            final_verdict = self.judge_agent(None)  # triggers final verdict
            self._log_message(final_verdict)
        self._write_transcript_to_file()

    def _log_message(self, msg: Msg):
        """
        Records each message line for final write-out. 
        Format: "<Timestamp> [<Role>] <Name>: <Content>"
        """
        stamp = msg.timestamp
        role = msg.role
        sender = msg.name
        text = msg.content
        if isinstance(text, dict):
            import json
            text = json.dumps(text, indent=2)

        log_line = f"{stamp} [{role}] {sender}: {text}"
        self._transcript_lines.append(log_line)
    
    def _write_transcript_to_file(self):
        """
        Writes all lines from self._transcript_lines into a .txt file.
        """
        with open(self.log_file, "w", encoding="utf-8") as f:
            for line in self._transcript_lines:
                f.write(line + "\n")

