from agentscope.memory import TemporaryMemory
from agentscope.message import Msg

from src.builder.builder import CountryProfileBuilder
from src.prompts.strategic_analysis_prompt import STRATEGIC_ANALYSIS_PROMPT

from dataclasses import dataclass

@dataclass
class DiplomaticMemoryStream:
    """
    Manages diplomatic memory streams for a country, including general knowledge,
    debate history, and strategic analysis.

    This class maintains three types of memory:
    - General Memory: Stores country profile and basic information
    - Debate Memory: Records all diplomatic exchanges
    - Strategy Memory: Contains strategic analysis of diplomatic interactions
    """
    country_name: str
    general_memory: TemporaryMemory
    debate_memory: TemporaryMemory
    strategy_memory: TemporaryMemory

    def __init__(self, country_name: str):
        """
        Initialize the DiplomaticMemoryStream for a given country. It takes the country name and initializes the general memory with the country profile.
        Args:
            country_name (str): The name of the country.
        """
        self.country_name = country_name
        self.general_memory = TemporaryMemory()
        self.general_memory.add(
            Msg(
                name=f"{country_name} General Knowledge",
                content = CountryProfileBuilder(country_name),
                role="system"
            )
        )
        self.debate_memory = TemporaryMemory()
        self.strategy_memory = TemporaryMemory()
    
    def add(self, opposition_country_position: Msg):
        """
        Processes an opposition country's diplomatic statement and generates strategic analysis.

        Takes a diplomatic message from another country, stores it in debate memory,
        and generates a strategic analysis that is stored in strategy memory.

        Args:
            opposition_country_position (Msg): A message object containing:
                - name: The name of the opposition country
                - content: Their diplomatic statement
                - role: Their role in the diplomatic exchange

        Example:
            >>> memory_stream = DiplomaticMemoryStream("United States")
            >>> opposition_msg = Msg(
            ...     name="China",
            ...     content="We firmly oppose unilateral actions...",
            ...     role="diplomat"
            ... )
            >>> memory_stream.add(opposition_msg)
        """
        prompt = STRATEGIC_ANALYSIS_PROMPT.format(
            country_name=self.country_name,
            opposition_statement=opposition_country_position.content,
            opposition_country=opposition_country_position.name
        )

        self.debate_memory.add(opposition_country_position)

        self.strategy_memory.add(
            Msg(
                name=f"{self.country_name} Strategy",
                content=prompt,
                role="strategist"
            )
        )
