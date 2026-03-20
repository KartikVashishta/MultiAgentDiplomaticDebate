from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch

from madd.core.schemas import CountryFacts, CountryProfile
from madd.stores.profile_store import (
    get_profile_path,
    load_profile,
    make_scenario_key,
    save_profile,
)
from madd.stores.run_store import create_run_dir


def test_profile_path():
    path = get_profile_path("United States")
    assert "united_states.json" in str(path)


def test_profile_path_with_scenario_key():
    key = make_scenario_key("Test Scenario", "Desc")
    path = get_profile_path("United States", scenario_key=key)
    assert key in str(path)


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


def test_create_run_dir_uses_configured_default(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "madd.stores.run_store.get_settings",
        lambda: SimpleNamespace(output_dir=str(tmp_path)),
    )

    run_dir = create_run_dir()

    assert run_dir.parent == tmp_path
    assert run_dir.exists()


def test_create_run_dir_is_collision_safe(tmp_path, monkeypatch):
    fixed_now = datetime(2026, 3, 21, 12, 0, 0, 123456, tzinfo=UTC)

    class _FixedDatetime:
        @staticmethod
        def now(_tz):
            return fixed_now

    monkeypatch.setattr("madd.stores.run_store.datetime", _FixedDatetime)

    first = create_run_dir(tmp_path)
    second = create_run_dir(tmp_path)

    assert first != second
    assert first.exists()
    assert second.exists()
