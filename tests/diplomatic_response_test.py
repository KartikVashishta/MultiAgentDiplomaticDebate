import pytest
from src.agents import DiplomaticResponseValidator

@pytest.fixture
def validator():
    return DiplomaticResponseValidator(country_name="United States")

@pytest.fixture
def test_response():
    return {
        "diplomatic_response": "China is the enemy of United States",
        "thought": "I need to validate the response",
        "key_points": ["China is the enemy of United States"],
        "strategic_alignment": "This response aligns with the United States' interests"
    }

def test_validator_returns_required_fields(validator, test_response):
    validated = validator.validate(test_response)
    assert "diplomatic_response" in validated
    assert "validation_notes" in validated

def test_validator_preserves_response_structure(validator, test_response):
    validated = validator.validate(test_response)
    assert isinstance(validated["diplomatic_response"], str)
    assert isinstance(validated["validation_notes"], list)

def test_validator_processes_hostile_response(validator):
    hostile_response = {
        "diplomatic_response": "China is the enemy of United States",
        "thought": "Hostile thought",
        "key_points": ["Hostility"],
        "strategic_alignment": "Aggressive stance"
    }
    validated = validator.validate(hostile_response)
    assert validated["diplomatic_response"] != hostile_response["diplomatic_response"]
