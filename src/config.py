from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

_CONFIG_PATH = Path.home() / ".recall" / "config.toml"
_VALID_LLM_PROVIDERS = {"claude", "ollama", "openai"}
_VALID_EMBED_PROVIDERS = {"ollama", "openai"}


@dataclass(frozen=True)
class LLMConfig:
    provider: str = "claude"
    model: str = "claude-3-5-sonnet-20241022"
    url: str = ""
    api_key: str = ""


@dataclass(frozen=True)
class EmbeddingsConfig:
    provider: str = "ollama"
    model: str = "nomic-embed-text"
    url: str = "http://localhost:11434"
    api_key: str = ""


@dataclass(frozen=True)
class DBConfig:
    path: str = ".recall/recall.db"


@dataclass(frozen=True)
class IntegrationConfig:
    github_token: str = ""
    gitlab_token: str = ""


@dataclass(frozen=True)
class Config:
    llm: LLMConfig = None  # type: ignore[assignment]
    embeddings: EmbeddingsConfig | None = None
    db: DBConfig = None  # type: ignore[assignment]
    integrations: IntegrationConfig = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.llm is None:
            object.__setattr__(self, "llm", LLMConfig())
        if self.db is None:
            object.__setattr__(self, "db", DBConfig())
        if self.integrations is None:
            object.__setattr__(self, "integrations", IntegrationConfig())


def load_config(config_path: Path | None = None) -> Config:
    """Load config from config.toml. Missing file returns defaults."""
    path = config_path if config_path is not None else _CONFIG_PATH

    if not path.exists():
        return Config()

    with open(path, "rb") as f:
        data = tomllib.load(f)

    llm_section = data.get("llm", {})
    provider = llm_section.get("provider", "claude")
    if provider not in _VALID_LLM_PROVIDERS:
        raise ValueError(
            f"Invalid LLM provider '{provider}'. Valid: {', '.join(sorted(_VALID_LLM_PROVIDERS))}"
        )

    url = llm_section.get("url", "")
    if provider == "ollama" and not url:
        url = "http://localhost:11434"

    llm = LLMConfig(
        provider=provider,
        model=llm_section.get("model", "claude-3-5-sonnet-20241022"),
        url=url,
        api_key=llm_section.get("api_key", ""),
    )

    embeddings: EmbeddingsConfig | None = None
    if "embeddings" in data:
        emb = data["embeddings"]
        embeddings = EmbeddingsConfig(
            provider=emb.get("provider", "ollama"),
            model=emb.get("model", "nomic-embed-text"),
            url=emb.get("url", "http://localhost:11434"),
            api_key=emb.get("api_key", ""),
        )

    db_section = data.get("db", {})
    db = DBConfig(path=db_section.get("path", ".recall/recall.db"))

    integ_section = data.get("integrations", {})
    integrations = IntegrationConfig(
        github_token=integ_section.get("github_token", ""),
        gitlab_token=integ_section.get("gitlab_token", ""),
    )

    return Config(llm=llm, embeddings=embeddings, db=db, integrations=integrations)
