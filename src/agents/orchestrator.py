import os
from agentscope import msghub
from agentscope.message import Msg

from src.agents.country_agent import CountryAgent
from src.agents.judge_agent import JudgeAgent
from src.utils.utils import BASIC_MODEL_CONFIG, MODEL_CONFIG

class DebateOrchestrator:
    """Orchestrates a multi-country diplomatic debate simulation from start to finish.

    This class manages the entire debate process including:
    1. Agent initialization for countries and judge
    2. Round management and turn-taking
    3. Message broadcasting and collection
    4. Scoring and verdict generation
    5. Conversation logging

    Time Complexity:
        - Initialization: O(C) where C is number of countries
        - Per Round: O(C) for country responses + O(1) for judge
        - Total Runtime: O(R * C) where R is number of rounds
        - Memory Usage: O(R * C) for storing all exchanges
        - File I/O: O(R * C) for logging all messages

    Attributes:
        countries (List[str]): List of participating country names
        problem_statement (str): The diplomatic issue being debated
        num_rounds (int): Number of debate rounds
        log_file (str): Path to conversation transcript file
        country_agents (List[CountryAgent]): List of country agent instances
        judge_agent (JudgeAgent): The debate judge instance
        all_agents (List[Union[CountryAgent, JudgeAgent]]): All participating agents

    Examples:
        >>> countries = ["USA", "China", "Russia"]
        >>> problem = "Nuclear disarmament treaty negotiations"
        >>> orchestrator = DebateOrchestrator(countries, problem, num_rounds=3)
        >>> orchestrator.run_debate()
        # Runs a 3-round debate between USA, China, and Russia
    """
    def __init__(
        self,
        countries,
        problem_statement: str,
        num_rounds: int,
        log_file_path: str = "debate_log.txt"
    ):
        """Initialize the debate orchestrator with countries and parameters.

        Args:
            countries (List[str]): List of participating country names
            problem_statement (str): The diplomatic issue to be debated
            num_rounds (int): Number of debate rounds to conduct
            log_file_path (str, optional): Path for saving debate transcript.
                Defaults to "debate_log.txt"
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
        """Execute the complete diplomatic debate simulation.

        This method:
        1. Introduces the debate topic and participants
        2. Conducts specified number of rounds
        3. Gets final verdict from judge
        4. Logs entire conversation

        Time Complexity:
            - Per Round: O(C) where C is number of countries
            - Total: O(R * C) where R is number of rounds
            - Logging: O(M) where M is total message count

        Side Effects:
            - Creates/updates log file at self.log_file
            - Broadcasts messages to all agents
            - Updates agent memory streams
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
            if final_verdict.metadata and "summary_insights" in final_verdict.metadata:
                summary_insights = final_verdict.metadata["summary_insights"]
                
                professional_summary_msg = Msg(
                    name="System",
                    role="system",
                    content=(
                        f"=== PROFESSIONAL SUMMARY ===\n"
                        f"Below are the key highlights and professional insights:\n\n"
                        f"{summary_insights}\n"
                        f"=== END OF PROFESSIONAL SUMMARY ==="
                    )
                )
                self._log_message(professional_summary_msg)
                
        self._write_transcript_to_file()

    def _log_message(self, msg: Msg):
        """Record a message in the debate transcript.

        Args:
            msg (Msg): Message to log, containing timestamp, role, sender, and content

        Time Complexity:
            - String Formatting: O(1)
            - List Append: O(1) amortized
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
        """Write the complete debate transcript to a file.

        Writes all accumulated messages from self._transcript_lines to the file
        specified in self.log_file. Each line includes timestamp, role, sender,
        and content of the message.

        Side Effects:
            - Creates or overwrites file at self.log_file
            - Each line format: "<Timestamp> [<Role>] <Sender>: <Content>"

        Note:
            - File is opened in write mode, overwriting any existing content
            - Uses UTF-8 encoding for universal character support
        """
        with open(self.log_file, "w", encoding="utf-8") as f:
            for line in self._transcript_lines:
                f.write(line + "\n")

