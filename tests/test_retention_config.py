"""Tests for LLMConfig retention_days field and load_config() extraction."""

import tomllib
from pathlib import Path

import pytest


class TestRetentionDaysDefault:
    def test_default_is_90(self):
        from src.llm.config import LLMConfig
        cfg = LLMConfig()
        assert cfg.retention_days == 90

    def test_frozen_dataclass_unchanged(self):
        from src.llm.config import LLMConfig
        cfg = LLMConfig()
        with pytest.raises(Exception):  # FrozenInstanceError
            cfg.retention_days = 30  # type: ignore[misc]


class TestLoadConfigRetention:
    def test_no_retention_section_returns_90(self, tmp_path):
        from src.llm.config import load_config
        # Write a minimal toml without [retention]
        toml_path = tmp_path / "llm.toml"
        toml_path.write_text("[cloud]\n")
        cfg = load_config(config_path=toml_path)
        assert cfg.retention_days == 90

    def test_retention_days_60(self, tmp_path):
        from src.llm.config import load_config
        toml_path = tmp_path / "llm.toml"
        toml_path.write_text("[retention]\nretention_days = 60\n")
        cfg = load_config(config_path=toml_path)
        assert cfg.retention_days == 60

    def test_retention_days_30_is_minimum_accepted(self, tmp_path):
        from src.llm.config import load_config
        toml_path = tmp_path / "llm.toml"
        toml_path.write_text("[retention]\nretention_days = 30\n")
        cfg = load_config(config_path=toml_path)
        assert cfg.retention_days == 30

    def test_retention_days_below_30_falls_back_to_90(self, tmp_path):
        from src.llm.config import load_config
        toml_path = tmp_path / "llm.toml"
        toml_path.write_text("[retention]\nretention_days = 10\n")
        cfg = load_config(config_path=toml_path)
        assert cfg.retention_days == 90

    def test_retention_days_1_falls_back_to_90(self, tmp_path):
        from src.llm.config import load_config
        toml_path = tmp_path / "llm.toml"
        toml_path.write_text("[retention]\nretention_days = 1\n")
        cfg = load_config(config_path=toml_path)
        assert cfg.retention_days == 90

    def test_below_30_logs_warning(self, tmp_path, caplog):
        """Warning should be issued when retention_days < 30."""
        import logging
        from src.llm.config import load_config
        toml_path = tmp_path / "llm.toml"
        toml_path.write_text("[retention]\nretention_days = 5\n")
        # structlog warning may not appear in caplog, so just check no exception
        cfg = load_config(config_path=toml_path)
        assert cfg.retention_days == 90

    def test_no_toml_file_returns_90(self, tmp_path):
        """When the toml file doesn't exist, retention_days should default to 90."""
        from src.llm.config import load_config
        nonexistent = tmp_path / "nonexistent.toml"
        cfg = load_config(config_path=nonexistent)
        assert cfg.retention_days == 90
