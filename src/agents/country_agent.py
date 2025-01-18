from typing import Union, List, Dict, Any, Optional
from agentscope.message import Msg
from agentscope.models import OpenAIChatWrapper
from agentscope.parsers import MarkdownJsonDictParser
from agentscope.agents import DialogAgent


from src.memory.streams import DiplomaticMemoryStream
from src.agents.diplomatic_response_validator import DiplomaticResponseValidator
from src.utils.utils import BASIC_MODEL_CONFIG
from src.prompts import COUNTRY_INITIALIZATION_PROMPT


class CountryAgent(DialogAgent):
    def __init__(self, country_name: str, model_config: Optional[Dict[str, Any]] = BASIC_MODEL_CONFIG):
        self.country_name = country_name

        super().__init__(
            name=country_name,
            sys_prompt=COUNTRY_INITIALIZATION_PROMPT.format(country_name=country_name),
            model_config_name=BASIC_MODEL_CONFIG["config_name"]
        )

        self.memory_stream = DiplomaticMemoryStream(country_name)
        self.model = OpenAIChatWrapper(**model_config)
        self.parser = MarkdownJsonDictParser(
            content_hint='{"thought": "internal analysis", "diplomatic_response": "official statement", "key_points": ["main points"], "strategic_alignment": "alignment explanation"}',
            keys_to_memory=["thought", "diplomatic_response", "key_points", "strategic_alignment"],
            keys_to_content="diplomatic_response",
            keys_to_metadata=["key_points", "strategic_alignment"]
        )
        self.validator = DiplomaticResponseValidator(country_name)

    def __call__(self, msg: Optional[Msg] = None) -> Msg:
        if msg:
            self.observe(msg)
        return self.reply(msg)

    def observe(self, msg: Msg) -> None:
        isForeign = msg.name != self.country_name
        self.memory_stream.add(msg, include_strategy=isForeign)

    def reply(self, incoming_msg: Optional[Msg] = None) -> Msg:
        response = self.model(messages = self._construct_prompt(incoming_msg))
        parsed_response = self.parser.parse(response)
        validated = self.validator.validate(parsed_response)
        
        return Msg(
            name=self.country_name,
            content=validated["diplomatic_response"],
            role="assistant",
            metadata={
                "thought": validated.get("thought", ""),
                "key_points": validated.get("key_points", []),
                "strategic_alignment": validated.get("strategic_alignment", "")
            }
        )

    def _construct_prompt(self, incoming_msg: Msg = None) -> List[Dict[str, str]]:
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
                    strategy_text.append(f"Previous Analysis:\n- Internal Thoughts: {content.get('thought', '')}\n- Key Points: {', '.join(content.get('key_points', []))}\n- Strategic Alignment: {content.get('strategic_alignment', '')}")
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