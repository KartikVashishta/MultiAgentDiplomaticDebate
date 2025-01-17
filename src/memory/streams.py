from agentscope.memory import TemporaryMemory
from agentscope.message import Msg
from agentscope.models import OpenAIChatWrapper
from agentscope.parsers import MarkdownJsonDictParser

from src.builder.builder import CountryProfileBuilder
from src.prompts.strategic_analysis_prompt import STRATEGIC_ANALYSIS_PROMPT
from src.utils.utils import print_green, BASIC_MODEL_CONFIG

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
                content = CountryProfileBuilder(country_name).model_dump(),
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
        """
        prompt = STRATEGIC_ANALYSIS_PROMPT.format(
            country_name=self.country_name,
            opposition_statement=opposition_country_position.content,
            opposition_country=opposition_country_position.name
        )
        
        
        parser = MarkdownJsonDictParser(
            content_hint='{"quick_analysis": "Brief assessment", "identified_intentions": ["intentions"], "potential_risks": ["risks"], "recommended_approach": {"tone": "tone", "key_points": ["points"], "leverage_points": ["points"]}, "long_term_considerations": ["considerations"]}',
            keys_to_memory=["quick_analysis", "identified_intentions", "potential_risks", "recommended_approach", "long_term_considerations"],
            keys_to_content=None
        )
        
        messages = [
            {"role": "system", "content": "You are a strategic advisor. Analyze the diplomatic statement and provide a structured JSON response."},
            {"role": "user", "content": prompt}
        ]
        
        model = OpenAIChatWrapper(**BASIC_MODEL_CONFIG)
        response = model(messages=messages)

        parsed_response = parser.parse(response)
        
        self.debate_memory.add(opposition_country_position)
        print_green(f"[INFO]: {self.country_name} strategizing")
        self.strategy_memory.add(
            Msg(
                name=f"{self.country_name} Strategy",
                content=parsed_response.parsed,
                role="system"
            )
        )
    
    def __repr__(self):
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
        return self.__repr__()
