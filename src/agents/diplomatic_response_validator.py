from agentscope.message import Msg
from agentscope.models import OpenAIChatWrapper
from agentscope.parsers import MarkdownJsonDictParser
from agentscope.models import ModelResponse

from src.utils.utils import BASIC_MODEL_CONFIG
from src.prompts import VALIDATE_DIPLOMATIC_PROTOCOL_PROMPT


class DiplomaticResponseValidator:

    def __init__(self, country_name: str):
        self.country_name = country_name
        self.model = OpenAIChatWrapper(**BASIC_MODEL_CONFIG)
        self.parser = MarkdownJsonDictParser(
            content_hint='{"validated_response": "response", "validation_notes": ["notes"]}',
            keys_to_memory=["validation_notes"],
            keys_to_content="validated_response"
        )

    def validate(self, response: ModelResponse) -> dict:

        validated = {}

        res = self.parser.parse(response).parsed
        diplomatic_response = res["diplomatic_response"]
        protocol_result = self._validate_diplomatic_protocol(diplomatic_response)

        validated["diplomatic_response"] = protocol_result["validated_response"]
        validated["validation_notes"] = protocol_result["validation_notes"]
        
        return validated

    def _validate_diplomatic_protocol(self, response_text: str) -> dict:
        messages = [
            {
                "role": "system",
                "content": VALIDATE_DIPLOMATIC_PROTOCOL_PROMPT.format(
                    country_name=self.country_name,
                    response=response_text
                )
            }
        ]
        
        validation_result = self.model(messages)
        parsed_result = self.parser.parse(validation_result)
        return parsed_result.parsed