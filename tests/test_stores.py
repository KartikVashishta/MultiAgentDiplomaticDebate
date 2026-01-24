import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from madd.stores.profile_store import load_profile, save_profile, get_profile_path
from madd.core.schemas import CountryProfile, CountryFacts, CountryStrategy


def test_profile_path():
    path = get_profile_path("United States")
    assert "united_states.json" in str(path)


def test_save_and_load_profile(tmp_path):
    with patch("madd.core.config.get_settings") as mock_settings:
        mock_settings.return_value.profiles_dir = str(tmp_path)
        
        facts = CountryFacts(name="TestLand")
        profile = CountryProfile(facts=facts)
        
        save_profile(profile)
        
        loaded = load_profile("TestLand")
        assert loaded is not None
        assert loaded.facts.name == "TestLand"


def test_load_nonexistent(tmp_path):
    with patch("madd.core.config.get_settings") as mock_settings:
        mock_settings.return_value.profiles_dir = str(tmp_path)
        
        loaded = load_profile("NonExistent")
        assert loaded is None
