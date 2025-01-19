from agentscope.memory import TemporaryMemory
from agentscope.message import Msg
from agentscope.models import OpenAIChatWrapper

from src.builder.builder import CountryProfileBuilder
from src.prompts.strategic_analysis_prompt import STRATEGIC_ANALYSIS_PROMPT
from src.utils.utils import print_green, BASIC_MODEL_CONFIG
from src.parsers.parsers import MemoryStreamParser

from dataclasses import dataclass

@dataclass
class DiplomaticMemoryStream:
    """A memory management system for diplomatic agents that handles multiple types of diplomatic memory.

    This class maintains three distinct memory streams for each country agent:
    1. General Memory: Stores country profile and basic information (constant size)
    2. Debate Memory: Records all diplomatic exchanges (grows with debate)
    3. Strategy Memory: Contains strategic analysis of diplomatic interactions

    Time Complexity:
        - Memory Access: O(1) for recent memory retrieval
        - Memory Addition: O(1) amortized for adding new memories
        - Strategic Analysis: O(1) for LLM API call, though I/O bound
        - Overall Memory Usage: O(N) where N is number of debate rounds

    Attributes:
        country_name (str): Name of the country this memory stream belongs to
        general_memory (TemporaryMemory): Stores country profile and basic info
        debate_memory (TemporaryMemory): Records diplomatic exchanges
        strategy_memory (TemporaryMemory): Stores strategic analysis

    Examples:
        >>> memory_stream = DiplomaticMemoryStream("France")
        >>> msg = Msg(name="Germany", content="Diplomatic statement", role="user")
        >>> memory_stream.add(msg)  # Adds message and generates strategic analysis
        >>> print(len(memory_stream.debate_memory.get_memory()))
    """

    country_name: str
    general_memory: TemporaryMemory
    debate_memory: TemporaryMemory
    strategy_memory: TemporaryMemory

    def __init__(self, country_name: str):
        """Initialize memory streams for a country.

        Args:
            country_name (str): The name of the country to create memory streams for.
        """
        self.country_name = country_name
        self.general_memory = TemporaryMemory()
        self.general_memory.add(
            Msg(
                name=f"{country_name} General Knowledge",
                content = CountryProfileBuilder(country_name).model_dump(),
                role="system"
            )
        )
        self.debate_memory = TemporaryMemory()
        self.strategy_memory = TemporaryMemory()
    
    def add(self, opposition_country_position: Msg):
        """Process and store a diplomatic message with strategic analysis.

        This method:
        1. Checks if the message is from a foreign country
        2. If foreign, generates strategic analysis using LLM
        3. Stores both the message and analysis in appropriate memory streams

        Time Complexity:
            - Message Storage: O(1)
            - Strategic Analysis: O(1) for API call, I/O bound
            - Overall: O(1) excluding API latency

        Args:
            opposition_country_position (Msg): Message containing:
                - name: Opposition country name
                - content: Diplomatic statement
                - role: Role in diplomatic exchange
        """
        is_foreign = (opposition_country_position.name != self.country_name)

        if is_foreign:
            print_green(f"[INFO]: {self.country_name} strategizing")
            prompt = STRATEGIC_ANALYSIS_PROMPT.format(
                country_name=self.country_name,
                opposition_statement=opposition_country_position.content,
                opposition_country=opposition_country_position.name
            )
            
            parser = MemoryStreamParser

            messages = [
                {"role": "system", "content": "You are a strategic advisor. Analyze the diplomatic statement and provide a structured JSON response."},
                {"role": "user", "content": prompt}
            ]
            
            model = OpenAIChatWrapper(**BASIC_MODEL_CONFIG)
            response = model(messages=messages)

            parsed_response = parser.parse(response)
            self.strategy_memory.add(
                Msg(
                    name=f"{('_'.join(self.country_name.split(' ')).lower())}_strategy",
                    content=parsed_response.parsed,
                    role="system"
                )
            )
        
        self.debate_memory.add(opposition_country_position)

    def __repr__(self):
        """Generate a detailed string representation of the memory stream.

        Returns a formatted string containing:
        - Country name
        - Most recent general memory entry
        - Current debate and strategy memory states
        - Message counts for each memory type

        Returns:
            str: Detailed multi-line representation of the memory stream state
        """
        general_memory = self.general_memory.get_memory(recent_n=1)[0]
        return f"""
        DiplomaticMemoryStream(
            country name: {self.country_name},
            general memory: {general_memory},
            debate memory: {self.debate_memory},
            strategy memory: {self.strategy_memory}),
            Messages in general memory: {len(self.general_memory.get_memory())}
            Messages in debate memory: {len(self.debate_memory.get_memory())}
            Messages in strategy memory: {len(self.strategy_memory.get_memory())}
        )
        """
    
    def __str__(self):
        """Return a string representation of the memory stream.

        Delegates to __repr__ for a consistent string representation.

        Returns:
            str: Same output as __repr__
        """
        return self.__repr__()
