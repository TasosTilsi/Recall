from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import tomllib  # stdlib in Python 3.11+

_CONFIG_PATH = Path.home() / ".recall" / "config.toml"


@dataclass
class LLMConfig:
    provider: str = "claude"
    model: str = "claude-haiku-4-5-20251001"
    url: str = ""
    api_key: str = ""


@dataclass
class EmbeddingsConfig:
    provider: str = "ollama"
    model: str = "nomic-embed-text"
    url: str = "http://localhost:11434"
    api_key: str = ""


@dataclass
class DBConfig:
    path: str = ".recall/recall.db"


@dataclass
class Config:
    llm: LLMConfig = field(default_factory=LLMConfig)
    embeddings: Optional[EmbeddingsConfig] = None   # None when [embeddings] absent
    db: DBConfig = field(default_factory=DBConfig)


def load_config(path: Path = _CONFIG_PATH) -> Config:
    """Load config from ~/.recall/config.toml. Missing file -> defaults."""
    cfg = Config()
    if not path.exists():
        return cfg
    with open(path, "rb") as f:
        data = tomllib.load(f)
    if "llm" in data:
        cfg.llm = LLMConfig(**{k: v for k, v in data["llm"].items() if k in LLMConfig.__dataclass_fields__})
    if "embeddings" in data:
        cfg.embeddings = EmbeddingsConfig(**{k: v for k, v in data["embeddings"].items() if k in EmbeddingsConfig.__dataclass_fields__})
    if "db" in data:
        cfg.db = DBConfig(**{k: v for k, v in data["db"].items() if k in DBConfig.__dataclass_fields__})
    return cfg
