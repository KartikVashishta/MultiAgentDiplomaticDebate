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
        self.scoreboard = []
    
    def run_debate(self):
        """Execute the complete diplomatic debate simulation.

        This method:
        1. Introduces the debate topic and participants
        2. Conducts specified number of rounds, including:
           - Gathering proposals from countries
           - Processing responses to proposals
           - Collecting country statements
           - Getting judge's evaluation
        3. Records scores and rankings each round
        4. Gets final verdict and professional summary
        5. Logs entire conversation 

        Time Complexity:
            - Introduction: O(1)
            - Per Round: O(C^2) where C is number of countries
                - Proposals: O(C)
                - Responses: O(C^2) in worst case
                - Statements: O(C)
                - Judgment: O(1)
            - Final Verdict: O(1)
            - Total: O(R * C^2) where R is number of rounds
            - Logging: O(M) where M is total message count

        Side Effects:
            - Creates/updates log file at self.log_file
            - Broadcasts messages to all agents 
            - Updates agent memory streams
            - Maintains scoreboard with rankings and scores
            - Generates professional summary of debate
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

                # Gather proposals from each country
                proposals = []
                for country_agent in self.country_agents:
                    proposal_msg = getattr(country_agent, "make_proposal", lambda: None)()
                    if proposal_msg:
                        hub.broadcast(proposal_msg)
                        self._log_message(proposal_msg)
                        proposals.append(proposal_msg)

                # Let each country respond to each proposal
                for prop in proposals:
                    for country_agent in self.country_agents:
                        if country_agent.name != prop.name:
                            resp_msg = getattr(country_agent, "respond_to_proposal", lambda x: None)(prop)
                            if resp_msg:
                                hub.broadcast(resp_msg)
                                self._log_message(resp_msg)

                for country_agent in self.country_agents:
                    response_msg = country_agent()
                    self._log_message(response_msg)

                round_judgment = self.judge_agent(None)
                self._log_message(round_judgment)

                # Log scoreboard 
                if round_judgment and round_judgment.metadata and "scores" in round_judgment.metadata:
                    import json
                    scoreboard_str = json.dumps(round_judgment.metadata["scores"], indent=2)
                    scoreboard_msg = Msg(
                        name="System",
                        role="system",
                        content=(
                            f"Round {round_idx} Scoreboard:\n{scoreboard_str}\n"
                            f"Rankings: {round_judgment.metadata.get('rankings', [])}"
                        )
                    )
                    self._log_message(scoreboard_msg)

                if round_judgment.metadata and "rankings" in round_judgment.metadata:
                    round_data = {
                        "round": round_judgment.metadata.get("round"),
                        "scores": round_judgment.metadata.get("scores"),
                        "rankings": round_judgment.metadata.get("rankings")
                    }
                    self.scoreboard.append(round_data)

            final_verdict = self.judge_agent(None)
            self._log_message(final_verdict)

            if final_verdict and final_verdict.metadata and "final_scores" in final_verdict.metadata:
                import json
                final_scores_str = json.dumps(final_verdict.metadata["final_scores"], indent=2)
                final_rankings = final_verdict.metadata.get("rankings", [])
                final_msg = Msg(
                    name="System",
                    role="system",
                    content=(
                        f"=== Final Scores ===\n{final_scores_str}\n"
                        f"Rankings: {final_rankings}"
                    )
                )
                self._log_message(final_msg)

            # Professional summary if present
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

        log_line = (
            "\n"
            "--------------------------------------------------\n"
            f"Timestamp: {stamp}\n"
            f"Role:      {role}\n"
            f"Sender:    {sender}\n"
            "--------------------------------------------------\n"
            f"{text}\n"
            "==================================================\n"
        )
        self._transcript_lines.append(log_line)
    
    def _write_transcript_to_file(self):
        """Write the complete debate transcript to a file.

        Writes all accumulated messages from self._transcript_lines to the file
        specified in self.log_file. Each line includes timestamp, role, sender,
        and content of the message.

        Time Complexity:
            - File Write: O(N) where N is total number of lines
            - String Operations: O(1) per line
            - Overall: O(N) where N is total transcript length

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
