import pytest
from src.memory.streams import DiplomaticMemoryStream
from agentscope.message import Msg

@pytest.fixture
def stream():
    return DiplomaticMemoryStream(country_name="United States")

def test_diplomatic_memory_stream_initialization(stream):
    assert isinstance(stream, DiplomaticMemoryStream)
    assert stream.country_name == "United States"

def test_diplomatic_memory_stream_initialization_with_general_memory(stream):
    assert len(stream.general_memory.get_memory()) == 1
    assert len(stream.strategy_memory.get_memory()) == 0
    assert len(stream.debate_memory.get_memory()) == 0

def test_diplomatic_memory_stream_add_message(stream):
    opposition_country_position = Msg(
        name="China", 
        content="Taiwan is considered as a part of China.",
        role="system"
    )
    stream.add(opposition_country_position)
    assert len(stream.debate_memory.get_memory()) == 1
    assert len(stream.strategy_memory.get_memory()) == 1
    assert stream.debate_memory.get_memory()[0] == opposition_country_position
    print(f"Strategy memory: {stream.strategy_memory.get_memory()[0]}")
    assert stream.strategy_memory.get_memory()[0].name == "United States Strategy"
    assert stream.strategy_memory.get_memory()[0].role == "system"

pytest.main([__file__])
