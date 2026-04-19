"""Tests for src/config.py v3.0 Config module."""
import pytest
from pathlib import Path

from src.config import Config, LLMConfig, EmbeddingsConfig, DBConfig, load_config


def _write_toml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "config.toml"
    p.write_text(content)
    return p


def test_load_full_config(tmp_path):
    """Test 1: full toml returns Config with correct field values."""
    p = _write_toml(tmp_path, """
[llm]
provider = "claude"
model = "claude-haiku-4-5-20251001"
url = ""
api_key = "sk-test"

[embeddings]
provider = "ollama"
model = "nomic-embed-text"
url = "http://localhost:11434"
api_key = ""

[db]
path = ".recall/recall.db"
""")
    cfg = load_config(config_path=p)
    assert cfg.llm.provider == "claude"
    assert cfg.llm.model == "claude-haiku-4-5-20251001"
    assert cfg.llm.api_key == "sk-test"
    assert cfg.embeddings is not None
    assert cfg.embeddings.provider == "ollama"
    assert cfg.db.path == ".recall/recall.db"


def test_no_embeddings_section(tmp_path):
    """Test 2: no [embeddings] section returns Config with embeddings=None."""
    p = _write_toml(tmp_path, """
[llm]
provider = "claude"
""")
    cfg = load_config(config_path=p)
    assert cfg.embeddings is None


def test_missing_file_returns_defaults(tmp_path):
    """Test 3: missing file returns Config with sensible defaults."""
    cfg = load_config(config_path=tmp_path / "nonexistent.toml")
    assert cfg.llm.provider == "claude"
    assert cfg.llm.model == "claude-haiku-4-5-20251001"
    assert cfg.embeddings is None


def test_invalid_provider_raises(tmp_path):
    """Test 4: invalid provider raises ValueError naming valid choices."""
    p = _write_toml(tmp_path, """
[llm]
provider = "badvalue"
""")
    with pytest.raises(ValueError, match="badvalue"):
        load_config(config_path=p)


def test_ollama_empty_url_gets_default(tmp_path):
    """Test 5: ollama with url="" gets default http://localhost:11434."""
    p = _write_toml(tmp_path, """
[llm]
provider = "ollama"
url = ""
""")
    cfg = load_config(config_path=p)
    assert cfg.llm.url == "http://localhost:11434"


def test_config_field_types(tmp_path):
    """Test 6: Config.llm is LLMConfig, embeddings is EmbeddingsConfig|None, db is DBConfig."""
    p = _write_toml(tmp_path, """
[llm]
provider = "claude"

[embeddings]
provider = "ollama"
""")
    cfg = load_config(config_path=p)
    assert isinstance(cfg.llm, LLMConfig)
    assert isinstance(cfg.embeddings, EmbeddingsConfig)
    assert isinstance(cfg.db, DBConfig)
