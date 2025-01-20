from agentscope.message import Msg
from agentscope.models import OpenAIChatWrapper
from agentscope.models import ModelResponse

from src.utils.utils import BASIC_MODEL_CONFIG
from src.prompts import VALIDATE_DIPLOMATIC_PROTOCOL_PROMPT
from src.parsers.parsers import ResponseValidatorParser, CountryParser

from typing import Union

class DiplomaticResponseValidator:

    def __init__(self, country_name: str):
        self.country_name = country_name
        self.model = OpenAIChatWrapper(**BASIC_MODEL_CONFIG)
        self.parser = ResponseValidatorParser
        self.country_parser = CountryParser

    def validate(self, response: Union[ModelResponse, dict]) -> dict:
        if isinstance(response, dict):
            res = response
        else:
            res = self.country_parser.parse(response).parsed
            
        # Carry over "thought", "key_points", and "strategic_alignment" to validated
        validated = {}
        validated["thought"] = res.get("thought", "")
        validated["key_points"] = res.get("key_points", [])
        validated["strategic_alignment"] = res.get("strategic_alignment", "")

        diplomatic_text = res.get("diplomatic_response", "")
        if not diplomatic_text:
            # Fallback or raise a more descriptive error if you prefer
            diplomatic_text = "No official statement is provided at this time."
        protocol_result = self._validate_diplomatic_protocol(diplomatic_text)

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