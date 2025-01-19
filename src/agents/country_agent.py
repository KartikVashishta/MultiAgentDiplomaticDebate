from typing import Union, List, Dict, Any, Optional
from agentscope.message import Msg
from agentscope.models import OpenAIChatWrapper
from agentscope.agents import DialogAgent

from src.memory.streams import DiplomaticMemoryStream
from src.agents.diplomatic_response_validator import DiplomaticResponseValidator
from src.utils.utils import BASIC_MODEL_CONFIG
from src.prompts import COUNTRY_INITIALIZATION_PROMPT
from src.parsers.parsers import CountryParser

class CountryAgent(DialogAgent):
    """An agent representing a country in diplomatic negotiations.

    This agent maintains its own diplomatic memory stream, processes incoming
    messages, and generates appropriate diplomatic responses based on its
    country's profile and strategic interests.

    Attributes:
        country_name (str): Name of the country this agent represents
        memory_stream (DiplomaticMemoryStream): Memory management system
        model (OpenAIChatWrapper): LLM for generating responses
        parser (CountryParser): Parser for response formatting
        validator (DiplomaticResponseValidator): Validator for responses

    Examples:
        >>> agent = CountryAgent("France")
        >>> msg = Msg(name="Germany", content="Proposal for trade agreement")
        >>> response = agent(msg)
        >>> print(response.content)  # Diplomatic response from France
    """

    def __init__(self, country_name: str, model_config: Optional[Dict[str, Any]] = BASIC_MODEL_CONFIG):
        """Initialize a country agent with its memory and processing components.

        Args:
            country_name (str): Name of the country to represent
            model_config (Optional[Dict[str, Any]], optional): LLM configuration. 
                Defaults to BASIC_MODEL_CONFIG.
        """
        self.country_name = country_name

        super().__init__(
            name=country_name,
            sys_prompt=COUNTRY_INITIALIZATION_PROMPT.format(country_name=country_name),
            model_config_name=BASIC_MODEL_CONFIG["config_name"]
        )

        self.memory_stream = DiplomaticMemoryStream(country_name)
        self.model = OpenAIChatWrapper(**model_config)
        self.parser = CountryParser
        self.validator = DiplomaticResponseValidator(country_name)

    def __call__(self, msg: Optional[Msg] = None) -> Msg:
        """Process an incoming message and generate a diplomatic response.

        Args:
            msg (Optional[Msg], optional): Incoming diplomatic message. 
                Defaults to None.

        Returns:
            Msg: Diplomatic response message
        """
        if msg:
            self.observe(msg)
        return super().__call__()

    def observe(self, msg: Msg) -> None:
        """Add a message to the agent's memory stream.

        Args:
            msg (Msg): Message to store in memory
        """
        self.memory_stream.add(msg)

    def reply(self, incoming_msg: Optional[Msg] = None) -> Msg:
        """Generate a diplomatic response to an incoming message.

        Processes the incoming message through the LLM, parses and validates
        the response, and formats it as a diplomatic message.

        Args:
            incoming_msg (Optional[Msg], optional): Message to respond to. 
                Defaults to None.

        Returns:
            Msg: Formatted diplomatic response with metadata including:
                - thought: Internal strategic analysis
                - key_points: Main points of the response
                - strategic_alignment: How response aligns with country's interests
        """
        response = self.model(messages = self._construct_prompt(incoming_msg))
        parsed_response = self.parser.parse(response)
        validated = self.validator.validate(parsed_response.parsed)
        
        return Msg(
            name=self.name,
            content=validated["diplomatic_response"],
            role="assistant",
            metadata={
                "thought": validated.get("thought", ""),
                "key_points": validated.get("key_points", []),
                "strategic_alignment": validated.get("strategic_alignment", "")
            }
        )

    def _construct_prompt(self, incoming_msg: Msg = None) -> List[Dict[str, str]]:
        """Construct a prompt for the LLM incorporating relevant memory and context.

        Builds a prompt that includes:
        1. System prompt with country initialization
        2. Country profile from general memory
        3. Recent debate history (last 5 messages)
        4. Strategic analysis (last 3 analyses)
        5. Current incoming message if any

        Args:
            incoming_msg (Msg, optional): Current message to respond to. 
                Defaults to None.

        Returns:
            List[Dict[str, str]]: List of message dictionaries for the LLM,
                each containing 'role' and 'content'
        """
        messages = []
        
        messages.append({
            "role": "system",
            "content": str(self.sys_prompt)
        })
        
        general_memory = self.memory_stream.general_memory.get_memory()
        if general_memory and general_memory[0].content:
            content = general_memory[0].content
            if isinstance(content, dict):
                content = str(content)
            messages.append({
                "role": "system",
                "content": f"Country Profile:\n{content}"
            })
        
        debate_memory = self.memory_stream.debate_memory.get_memory(recent_n=5)
        for msg in debate_memory:
            content = msg.content
            if isinstance(content, dict):
                content = str(content)
            messages.append({
                "role": "user" if msg.name != self.country_name else "assistant",
                "content": content
            })

        strategy_memory = self.memory_stream.strategy_memory.get_memory(recent_n=3)
        if strategy_memory:
            strategy_text = []
            for msg in strategy_memory:
                content = msg.content
                if isinstance(content, dict):
                    strategy_text.append(
                    f"Previous Analysis:\n"
                    f"- Quick Analysis: {content.get('quick_analysis', '')}\n"
                    f"- Identified Intentions: {', '.join(content.get('identified_intentions', []))}\n"
                    f"- Potential Risks: {', '.join(content.get('potential_risks', []))}\n"
                    f"- Recommended Approach: {content.get('recommended_approach', {})}\n"
                    f"- Long Term Considerations: {', '.join(content.get('long_term_considerations', []))}"
                )
                else:
                    strategy_text.append(str(content))
            
            if strategy_text:
                messages.append({
                    "role": "system",
                    "content": "\n\n".join(strategy_text)
                })

        if incoming_msg:
            content = incoming_msg.content
            if isinstance(content, dict):
                content = str(content)
            messages.append({
                "role": "user",
                "content": content
            })

        return messages