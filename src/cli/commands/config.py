"""Config command for viewing and modifying LLM configuration."""
import sys
from pathlib import Path
from typing import Annotated, Optional

import tomllib
import typer
from rich.table import Table

from src.cli.output import console, print_error, print_json, print_success
from src.cli.utils import EXIT_BAD_ARGS, EXIT_SUCCESS
from src.llm.config import load_config

# Mapping of valid config keys to their types and descriptions
VALID_CONFIG_KEYS = {
    "cloud.endpoint": {"type": str, "desc": "Cloud Ollama endpoint URL"},
    "cloud.api_key": {"type": str, "desc": "Cloud Ollama API key", "sensitive": True},
    "local.endpoint": {"type": str, "desc": "Local Ollama endpoint URL"},
    "local.auto_start": {"type": bool, "desc": "Auto-start local Ollama"},
    "local.models": {"type": list, "desc": "Local model fallback chain"},
    "embeddings.models": {"type": list, "desc": "Embeddings model names"},
    "retry.max_attempts": {"type": int, "desc": "Max retry attempts"},
    "retry.delay_seconds": {"type": int, "desc": "Retry delay in seconds"},
    "timeout.request_seconds": {"type": int, "desc": "Request timeout"},
    "quota.warning_threshold": {"type": float, "desc": "Quota warning threshold (0-1)"},
    "quota.rate_limit_cooldown_seconds": {"type": int, "desc": "Rate limit cooldown"},
    "queue.max_size": {"type": int, "desc": "Request queue max size"},
    "queue.item_ttl_hours": {"type": int, "desc": "Queue item TTL in hours"},
    "reranking.enabled": {"type": bool, "desc": "Enable cross-encoder reranking"},
    "reranking.backend": {"type": str, "desc": "Reranking backend (none, bge, openai)"},
    "capture.mode": {
        "type": str,
        "desc": "Capture mode (decisions-only, decisions-and-patterns)",
        "allowed_values": ["decisions-only", "decisions-and-patterns"],
    },
    "retention.retention_days": {
        "type": int,
        "desc": "Days before a node is considered stale (min 30)",
    },
    "ui.api_port": {"type": int, "desc": "FastAPI UI server port (default 8765)"},
    "ui.port": {"type": int, "desc": "UI dev server port (reserved, default 3000)"},
}


def _get_config_path() -> Path:
    """Get the path to the LLM config file."""
    return Path.home() / ".graphiti" / "llm.toml"


def _get_nested_value(config_dict: dict, key_path: str):
    """Get value from nested dict using dotted key path.

    Args:
        config_dict: Nested dictionary to query
        key_path: Dotted key path (e.g., "cloud.endpoint")

    Returns:
        Value at key path, or None if not found
    """
    parts = key_path.split(".")
    value = config_dict
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    return value


def _set_nested_value(config_dict: dict, key_path: str, value):
    """Set value in nested dict using dotted key path.

    Args:
        config_dict: Nested dictionary to modify
        key_path: Dotted key path (e.g., "cloud.endpoint")
        value: Value to set
    """
    parts = key_path.split(".")
    current = config_dict

    # Navigate/create nested structure
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]

    # Set final value
    current[parts[-1]] = value


def _parse_value(value_str: str, target_type: type):
    """Parse string value according to target type.

    Args:
        value_str: String value to parse
        target_type: Expected type (str, int, float, bool, list)

    Returns:
        Parsed value

    Raises:
        ValueError: If parsing fails
    """
    if target_type == str:
        return value_str
    elif target_type == int:
        return int(value_str)
    elif target_type == float:
        return float(value_str)
    elif target_type == bool:
        lower = value_str.lower()
        if lower in ("true", "1", "yes"):
            return True
        elif lower in ("false", "0", "no"):
            return False
        else:
            raise ValueError(f"Invalid boolean value: {value_str}")
    elif target_type == list:
        # Parse comma-separated values
        return [v.strip() for v in value_str.split(",")]
    else:
        raise ValueError(f"Unsupported type: {target_type}")


def _format_toml_value(value) -> str:
    """Format a Python value as TOML string.

    Args:
        value: Python value to format

    Returns:
        TOML-formatted string
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, str):
        # Quote strings
        return f'"{value}"'
    elif isinstance(value, list):
        # Format as array
        formatted_items = [_format_toml_value(item) for item in value]
        return f'[{", ".join(formatted_items)}]'
    else:
        return str(value)


def _write_toml(config_dict: dict, path: Path):
    """Write config dict to TOML file.

    Uses simple TOML formatting for flat nested structure.

    Args:
        config_dict: Configuration dictionary to write
        path: Path to write TOML file
    """
    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    for section, values in sorted(config_dict.items()):
        lines.append(f"[{section}]")
        if isinstance(values, dict):
            for key, value in sorted(values.items()):
                lines.append(f"{key} = {_format_toml_value(value)}")
        lines.append("")  # Blank line between sections

    path.write_text("\n".join(lines))


def config_command(
    set_value: Annotated[
        Optional[str], typer.Option("--set", help="Set config value: key=value")
    ] = None,
    get_key: Annotated[
        Optional[str], typer.Option("--get", help="Get a specific config value")
    ] = None,
    format: Annotated[
        Optional[str], typer.Option("--format", "-f", help="Output format: json")
    ] = None,
):
    """View and modify LLM configuration.

    Examples:
        graphiti config                        # Show all settings
        graphiti config --get cloud.endpoint   # Get specific value
        graphiti config --set retry.max_attempts=5  # Set value
        graphiti config --format json          # JSON output
    """
    config = load_config()
    config_path = _get_config_path()

    # Load existing TOML file for modifications
    existing_toml = {}
    if config_path.exists():
        with open(config_path, "rb") as f:
            existing_toml = tomllib.load(f)

    # Handle --set flag
    if set_value:
        if "=" not in set_value:
            print_error(
                "Invalid format. Use: graphiti config --set key=value",
                suggestion="Example: graphiti config --set retry.max_attempts=5"
            )
            sys.exit(EXIT_BAD_ARGS)

        key, value_str = set_value.split("=", 1)
        key = key.strip()
        value_str = value_str.strip()

        # Validate key
        if key not in VALID_CONFIG_KEYS:
            print_error(
                f"Unknown config key '{key}'.",
                suggestion="Run 'graphiti config' to see valid keys."
            )
            sys.exit(EXIT_BAD_ARGS)

        # Parse value according to expected type
        key_info = VALID_CONFIG_KEYS[key]
        try:
            parsed_value = _parse_value(value_str, key_info["type"])
        except ValueError as e:
            print_error(
                f"Invalid value for {key}: {e}",
                suggestion=f"Expected type: {key_info['type'].__name__}"
            )
            sys.exit(EXIT_BAD_ARGS)

        # Validate allowed values if defined for this key
        if "allowed_values" in key_info and parsed_value not in key_info["allowed_values"]:
            print_error(
                f"Invalid value for {key}: '{parsed_value}'.",
                suggestion=f"Valid values: {', '.join(key_info['allowed_values'])}"
            )
            sys.exit(EXIT_BAD_ARGS)

        # Update config dict
        _set_nested_value(existing_toml, key, parsed_value)

        # Write back to file
        _write_toml(existing_toml, config_path)

        print_success(f"Set {key} = {parsed_value}")
        sys.exit(EXIT_SUCCESS)

    # Handle --get flag
    if get_key:
        if get_key not in VALID_CONFIG_KEYS:
            print_error(
                f"Unknown config key '{get_key}'.",
                suggestion="Run 'graphiti config' to see valid keys."
            )
            sys.exit(EXIT_BAD_ARGS)

        # Get value from loaded config
        value = _get_nested_value(existing_toml, get_key)
        if value is None:
            # Fall back to default from loaded config object
            # Map dotted key to config attribute
            attr_map = {
                "cloud.endpoint": "cloud_endpoint",
                "cloud.api_key": "cloud_api_key",
                "local.endpoint": "local_endpoint",
                "local.auto_start": "local_auto_start",
                "local.models": "local_models",
                "embeddings.models": "embeddings_models",
                "retry.max_attempts": "retry_max_attempts",
                "retry.delay_seconds": "retry_delay_seconds",
                "timeout.request_seconds": "request_timeout_seconds",
                "quota.warning_threshold": "quota_warning_threshold",
                "quota.rate_limit_cooldown_seconds": "rate_limit_cooldown_seconds",
                "queue.max_size": "queue_max_size",
                "queue.item_ttl_hours": "queue_item_ttl_hours",
                "reranking.enabled": "reranking_enabled",
                "reranking.backend": "reranking_backend",
                "capture.mode": "capture_mode",
                "retention.retention_days": "retention_days",
                "ui.api_port": "ui_api_port",
                "ui.port": "ui_port",
            }
            attr_name = attr_map.get(get_key)
            if attr_name:
                value = getattr(config, attr_name, None)

        if format == "json":
            print_json({get_key: value})
        else:
            console.print(f"{value}")

        sys.exit(EXIT_SUCCESS)

    # Show all settings (default behavior)
    if format == "json":
        # Build JSON structure from config object
        config_data = {
            "cloud": {
                "endpoint": config.cloud_endpoint,
                "api_key": config.cloud_api_key,
            },
            "local": {
                "endpoint": config.local_endpoint,
                "auto_start": config.local_auto_start,
                "models": config.local_models,
            },
            "embeddings": {
                "models": config.embeddings_models,
            },
            "retry": {
                "max_attempts": config.retry_max_attempts,
                "delay_seconds": config.retry_delay_seconds,
            },
            "timeout": {
                "request_seconds": config.request_timeout_seconds,
            },
            "quota": {
                "warning_threshold": config.quota_warning_threshold,
                "rate_limit_cooldown_seconds": config.rate_limit_cooldown_seconds,
            },
            "queue": {
                "max_size": config.queue_max_size,
                "item_ttl_hours": config.queue_item_ttl_hours,
            },
            "reranking": {
                "enabled": config.reranking_enabled,
                "backend": config.reranking_backend,
            },
            "capture": {
                "mode": config.capture_mode,
            },
            "retention": {
                "retention_days": config.retention_days,
            },
            "ui": {
                "api_port": config.ui_api_port,
                "port": config.ui_port,
            },
        }
        print_json(config_data)
    else:
        # Display as Rich table
        table = Table(
            title="LLM Configuration",
            show_header=True,
            header_style="bold cyan"
        )
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="white")
        table.add_column("Description", style="dim")

        # Build rows from config object
        rows = [
            ("cloud.endpoint", config.cloud_endpoint),
            ("cloud.api_key", "***" if config.cloud_api_key else "(not set)"),
            ("local.endpoint", config.local_endpoint),
            ("local.auto_start", str(config.local_auto_start)),
            ("local.models", ", ".join(config.local_models)),
            ("embeddings.models", ", ".join(config.embeddings_models)),
            ("retry.max_attempts", str(config.retry_max_attempts)),
            ("retry.delay_seconds", str(config.retry_delay_seconds)),
            ("timeout.request_seconds", str(config.request_timeout_seconds)),
            ("quota.warning_threshold", str(config.quota_warning_threshold)),
            ("quota.rate_limit_cooldown_seconds", str(config.rate_limit_cooldown_seconds)),
            ("queue.max_size", str(config.queue_max_size)),
            ("queue.item_ttl_hours", str(config.queue_item_ttl_hours)),
            ("reranking.enabled", str(config.reranking_enabled)),
            ("reranking.backend", config.reranking_backend),
        ]

        for key, value in rows:
            desc = VALID_CONFIG_KEYS.get(key, {}).get("desc", "")
            table.add_row(key, value, desc)

        table.add_row("[bold]Capture Settings[/bold]", "", "", style="dim")
        table.add_row("capture.mode", config.capture_mode, VALID_CONFIG_KEYS["capture.mode"]["desc"])
        table.add_row("[bold]Retention Settings[/bold]", "", "", style="dim")
        table.add_row("retention.retention_days", str(config.retention_days), VALID_CONFIG_KEYS["retention.retention_days"]["desc"])
        table.add_row("[bold]UI Settings[/bold]", "", "", style="dim")
        table.add_row("ui.api_port", str(config.ui_api_port), VALID_CONFIG_KEYS["ui.api_port"]["desc"])
        table.add_row("ui.port", str(config.ui_port), VALID_CONFIG_KEYS["ui.port"]["desc"])

        console.print(table)

    sys.exit(EXIT_SUCCESS)
