"""Test suite for LLM configuration management.

Tests configuration loading from TOML files with environment variable overrides,
config immutability, and state path resolution.
"""

import os
import tempfile
from pathlib import Path

import pytest

from src.llm.config import LLMConfig, load_config, get_state_path


class TestConfigDefaults:
    """Test default configuration values."""

    def test_load_config_defaults(self, monkeypatch, tmp_path):
        """Load config with no file present - should return all defaults."""
        # Point to non-existent config file
        nonexistent_path = tmp_path / "nonexistent" / "llm.toml"

        # Clear any environment variables that could affect config
        monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
        monkeypatch.delenv("OLLAMA_CLOUD_ENDPOINT", raising=False)
        monkeypatch.delenv("OLLAMA_LOCAL_ENDPOINT", raising=False)

        config = load_config(nonexistent_path)

        # Verify all defaults match LLMConfig dataclass defaults
        assert config.cloud_endpoint == "https://ollama.com"
        assert config.cloud_api_key is None
        assert config.local_endpoint == "http://localhost:11434"
        assert config.local_auto_start is False
        assert config.cloud_models == []
        assert config.local_models == ["gemma2:9b", "llama3.2:3b"]
        assert config.embeddings_models == ["nomic-embed-text"]
        assert config.retry_max_attempts == 3
        assert config.retry_delay_seconds == 10
        assert config.request_timeout_seconds == 180
        assert config.quota_warning_threshold == 0.8
        assert config.rate_limit_cooldown_seconds == 600
        assert config.failover_logging is True
        assert config.queue_max_size == 1000
        assert config.queue_item_ttl_hours == 24


class TestConfigFromTOML:
    """Test configuration loading from TOML files."""

    def test_load_config_from_toml(self, tmp_path, monkeypatch):
        """Load config from TOML file with custom values."""
        # Clear environment variables
        monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
        monkeypatch.delenv("OLLAMA_CLOUD_ENDPOINT", raising=False)
        monkeypatch.delenv("OLLAMA_LOCAL_ENDPOINT", raising=False)

        # Create temp TOML file with custom values
        config_file = tmp_path / "llm.toml"
        config_file.write_text("""
[cloud]
endpoint = "https://custom-ollama.example.com"
api_key = "toml_api_key_123"

[local]
endpoint = "http://localhost:9999"
auto_start = true
models = ["llama3.2:1b", "gemma2:2b"]

[embeddings]
models = ["all-minilm-l6-v2"]

[retry]
max_attempts = 5
delay_seconds = 15

[timeout]
request_seconds = 120

[quota]
warning_threshold = 0.9
rate_limit_cooldown_seconds = 900

[logging]
failover = false

[queue]
max_size = 500
item_ttl_hours = 48
""")

        config = load_config(config_file)

        # Verify values are read correctly from TOML
        assert config.cloud_endpoint == "https://custom-ollama.example.com"
        assert config.cloud_api_key == "toml_api_key_123"
        assert config.local_endpoint == "http://localhost:9999"
        assert config.local_auto_start is True
        assert config.local_models == ["llama3.2:1b", "gemma2:2b"]
        assert config.embeddings_models == ["all-minilm-l6-v2"]
        assert config.retry_max_attempts == 5
        assert config.retry_delay_seconds == 15
        assert config.request_timeout_seconds == 120
        assert config.quota_warning_threshold == 0.9
        assert config.rate_limit_cooldown_seconds == 900
        assert config.failover_logging is False
        assert config.queue_max_size == 500
        assert config.queue_item_ttl_hours == 48

    def test_load_partial_toml(self, tmp_path, monkeypatch):
        """Load config from partial TOML - missing sections use defaults."""
        monkeypatch.delenv("OLLAMA_API_KEY", raising=False)

        # Create TOML with only cloud section
        config_file = tmp_path / "llm.toml"
        config_file.write_text("""
[cloud]
endpoint = "https://partial.example.com"
""")

        config = load_config(config_file)

        # Cloud endpoint from TOML
        assert config.cloud_endpoint == "https://partial.example.com"
        # Other values should be defaults
        assert config.local_endpoint == "http://localhost:11434"
        assert config.retry_max_attempts == 3
        assert config.queue_max_size == 1000


class TestEnvVarOverrides:
    """Test environment variable overrides."""

    def test_env_var_overrides(self, tmp_path, monkeypatch):
        """Environment variables override TOML values."""
        # Create TOML with values
        config_file = tmp_path / "llm.toml"
        config_file.write_text("""
[cloud]
endpoint = "https://toml-endpoint.com"
api_key = "toml_key"

[local]
endpoint = "http://localhost:8888"
""")

        # Set environment variables
        monkeypatch.setenv("OLLAMA_API_KEY", "env_api_key_456")
        monkeypatch.setenv("OLLAMA_CLOUD_ENDPOINT", "https://env-endpoint.com")
        monkeypatch.setenv("OLLAMA_LOCAL_ENDPOINT", "http://localhost:7777")

        config = load_config(config_file)

        # Environment variables should override TOML
        assert config.cloud_endpoint == "https://env-endpoint.com"
        assert config.cloud_api_key == "env_api_key_456"
        assert config.local_endpoint == "http://localhost:7777"

    def test_env_overrides_defaults(self, tmp_path, monkeypatch):
        """Environment variables override defaults when no TOML file."""
        nonexistent_path = tmp_path / "nonexistent.toml"

        monkeypatch.setenv("OLLAMA_API_KEY", "env_key_only")
        monkeypatch.setenv("OLLAMA_CLOUD_ENDPOINT", "https://env-only.com")

        config = load_config(nonexistent_path)

        assert config.cloud_endpoint == "https://env-only.com"
        assert config.cloud_api_key == "env_key_only"
        # Other values still defaults
        assert config.local_endpoint == "http://localhost:11434"


class TestConfigImmutability:
    """Test frozen dataclass immutability."""

    def test_config_immutable(self, monkeypatch):
        """Config is immutable after creation - modifications should fail."""
        monkeypatch.delenv("OLLAMA_API_KEY", raising=False)

        config = load_config()

        # Attempt to modify should raise FrozenInstanceError
        with pytest.raises(Exception):  # dataclasses.FrozenInstanceError
            config.cloud_endpoint = "https://modified.com"

        with pytest.raises(Exception):
            config.cloud_api_key = "new_key"

        with pytest.raises(Exception):
            config.retry_max_attempts = 10


class TestStatePath:
    """Test state path resolution."""

    def test_get_state_path(self):
        """Verify get_state_path returns correct path."""
        state_path = get_state_path()

        # Should be ~/.recall/llm_state.json (migrated from ~/.graphiti in Phase 14-01)
        expected = Path.home() / ".recall" / "llm_state.json"
        assert state_path == expected
        assert state_path.name == "llm_state.json"
        assert state_path.parent.name == ".recall"


# ---------------------------------------------------------------------------
# Phase 13: [llm] section tests
# ---------------------------------------------------------------------------

LLM_SECTION_TOML = """
[llm]
primary_url     = "https://api.openai.com/v1"
primary_api_key = "sk-test-key"
primary_models  = ["gpt-4o-mini"]
embed_url       = "https://api.openai.com/v1"
embed_models    = ["text-embedding-3-small"]
"""


def test_llm_section_sets_provider_mode(tmp_path, monkeypatch):
    """load_config() with [llm] section sets llm_mode='provider' and llm_* fields."""
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_CLOUD_ENDPOINT", raising=False)
    monkeypatch.delenv("OLLAMA_LOCAL_ENDPOINT", raising=False)

    config_file = tmp_path / "llm.toml"
    config_file.write_text(LLM_SECTION_TOML)

    config = load_config(config_path=config_file)

    assert config.llm_mode == "provider"
    assert config.llm_primary_url == "https://api.openai.com/v1"
    assert config.llm_primary_models == ["gpt-4o-mini"]


def test_legacy_mode_when_no_llm_section(tmp_path, monkeypatch):
    """load_config() with no [llm] section sets llm_mode='legacy', llm_* fields are None/empty."""
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)

    config_file = tmp_path / "llm.toml"
    config_file.write_text("[cloud]\nendpoint = \"https://ollama.com\"\n")

    config = load_config(config_path=config_file)

    assert config.llm_mode == "legacy"
    assert config.llm_primary_url is None
    assert config.llm_primary_api_key is None
    assert config.llm_primary_models == []
    assert config.llm_fallback_url is None
    assert config.llm_fallback_models == []
    assert config.llm_embed_url is None
    assert config.llm_embed_api_key is None
    assert config.llm_embed_models == []


def test_old_cloud_local_sections_work_with_llm_present(tmp_path, monkeypatch):
    """load_config() with both [llm] and [cloud]/[local] raises no exception; llm_mode='provider'."""
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)

    config_file = tmp_path / "llm.toml"
    config_file.write_text(
        LLM_SECTION_TOML
        + "\n[cloud]\nendpoint = \"https://ollama.com\"\n"
        + "\n[local]\nmodels = [\"gemma2:9b\"]\n"
    )

    config = load_config(config_path=config_file)  # must not raise

    assert config.llm_mode == "provider"


def test_embed_api_key_fallback(tmp_path, monkeypatch):
    """[llm] with primary_api_key but no embed_api_key → llm_embed_api_key == primary_api_key."""
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)

    # No embed_api_key in this TOML
    config_file = tmp_path / "llm.toml"
    config_file.write_text("""
[llm]
primary_url     = "https://api.openai.com/v1"
primary_api_key = "sk-test-key"
primary_models  = ["gpt-4o-mini"]
embed_url       = "https://api.openai.com/v1"
embed_models    = ["text-embedding-3-small"]
""")

    config = load_config(config_path=config_file)

    assert config.llm_embed_api_key == "sk-test-key"
