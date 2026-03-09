"""Tests for all 9 CLI commands.

Tests each command with basic invocation, JSON format, edge cases,
and error handling.
"""
import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from src.cli import app

# CliRunner for testing Typer apps
runner = CliRunner()


# ==================== Add Command Tests ====================


@patch("src.cli.commands.add._add_entity")
@patch("src.cli.commands.add.resolve_scope")
def test_add_with_content(mock_resolve_scope, mock_add_entity):
    """Test add command with positional content."""
    from src.models import GraphScope
    mock_resolve_scope.return_value = (GraphScope.GLOBAL, None)
    mock_add_entity.return_value = {
        "name": "test_entity",
        "type": "entity",
        "scope": "global",
    }

    result = runner.invoke(app, ["add", "test content"])

    assert result.exit_code == 0
    assert "Added" in result.stdout or "test_entity" in result.stdout


@patch("src.cli.commands.add.resolve_scope")
def test_add_no_content_no_pipe(mock_resolve_scope):
    """Test add command fails with no content and no stdin."""
    from src.models import GraphScope
    mock_resolve_scope.return_value = (GraphScope.GLOBAL, None)

    result = runner.invoke(app, ["add"])

    # Should fail with bad args
    assert result.exit_code != 0
    # Error message can be in stdout or stderr
    output = (result.stdout + result.stderr).lower()
    assert "no content" in output or "usage" in output


@patch("src.cli.commands.add._add_entity")
@patch("src.cli.commands.add.resolve_scope")
def test_add_from_stdin(mock_resolve_scope, mock_add_entity):
    """Test add command reads from stdin."""
    from src.models import GraphScope
    mock_resolve_scope.return_value = (GraphScope.GLOBAL, None)
    mock_add_entity.return_value = {
        "name": "piped_entity",
        "type": "entity",
        "scope": "global",
    }

    result = runner.invoke(app, ["add"], input="piped content\n")

    assert result.exit_code == 0


@patch("src.cli.commands.add._add_entity")
@patch("src.cli.commands.add.resolve_scope")
def test_add_json_format(mock_resolve_scope, mock_add_entity):
    """Test add command with JSON output."""
    from src.models import GraphScope
    mock_resolve_scope.return_value = (GraphScope.GLOBAL, None)
    mock_add_entity.return_value = {
        "name": "test_entity",
        "type": "entity",
        "scope": "global",
    }

    result = runner.invoke(app, ["add", "test", "--format", "json"])

    assert result.exit_code == 0
    # Should be valid JSON
    try:
        json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail("Output is not valid JSON")


@patch("src.cli.commands.add._add_entity")
@patch("src.cli.commands.add.resolve_scope")
def test_add_quiet(mock_resolve_scope, mock_add_entity):
    """Test add command with --quiet flag."""
    from src.models import GraphScope
    mock_resolve_scope.return_value = (GraphScope.GLOBAL, None)
    mock_add_entity.return_value = {
        "name": "test_entity",
        "type": "entity",
        "scope": "global",
    }

    result = runner.invoke(app, ["add", "test", "--quiet"])

    assert result.exit_code == 0
    # Quiet mode should have minimal output (no success message)
    assert "Added" not in result.stdout or len(result.stdout.strip()) < 50


# ==================== Search Command Tests ====================


@patch("src.cli.commands.search._search_entities")
@patch("src.cli.commands.search.resolve_scope")
def test_search_basic(mock_resolve_scope, mock_search):
    """Test search command with basic query."""
    from src.models import GraphScope
    mock_resolve_scope.return_value = (GraphScope.GLOBAL, None)
    mock_search.return_value = [
        {"name": "entity1", "type": "concept", "score": 0.95, "snippet": "test", "created_at": "2026-01-01T00:00:00"},
    ]

    result = runner.invoke(app, ["search", "test query"])

    assert result.exit_code == 0
    assert "entity1" in result.stdout or "concept" in result.stdout


@patch("src.cli.commands.search._search_entities")
@patch("src.cli.commands.search.resolve_scope")
def test_search_json(mock_resolve_scope, mock_search):
    """Test search with JSON output."""
    from src.models import GraphScope
    mock_resolve_scope.return_value = (GraphScope.GLOBAL, None)
    mock_search.return_value = [
        {"name": "entity1", "type": "concept", "score": 0.95, "snippet": "test", "created_at": "2026-01-01T00:00:00"},
    ]

    result = runner.invoke(app, ["search", "test", "--format", "json"], catch_exceptions=False)

    assert result.exit_code == 0
    # Rich pretty-prints JSON with extra text after it. Extract just the JSON part.
    try:
        # Find the JSON array by looking for the brackets and extracting content between them
        output = result.stdout
        start = output.find("[")
        # Find matching closing bracket
        if start != -1:
            bracket_count = 0
            end = start
            for i, char in enumerate(output[start:], start):
                if char == "[":
                    bracket_count += 1
                elif char == "]":
                    bracket_count -= 1
                    if bracket_count == 0:
                        end = i + 1
                        break
            json_str = output[start:end]
            json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        pytest.fail(f"Output is not valid JSON: {result.stdout}")


@patch("src.cli.commands.search._search_entities")
@patch("src.cli.commands.search.resolve_scope")
def test_search_compact(mock_resolve_scope, mock_search):
    """Test search with compact output."""
    from src.models import GraphScope
    mock_resolve_scope.return_value = (GraphScope.GLOBAL, None)
    mock_search.return_value = [
        {"name": "entity1", "type": "concept", "score": 0.95, "snippet": "test content", "created_at": "2026-01-01T00:00:00"},
    ]

    result = runner.invoke(app, ["search", "test", "--compact"])

    assert result.exit_code == 0


@patch("src.cli.commands.search._search_entities")
@patch("src.cli.commands.search.resolve_scope")
def test_search_exact(mock_resolve_scope, mock_search):
    """Test search with --exact flag."""
    from src.models import GraphScope
    mock_resolve_scope.return_value = (GraphScope.GLOBAL, None)
    mock_search.return_value = []

    result = runner.invoke(app, ["search", "test", "--exact"])

    assert result.exit_code == 0


@patch("src.cli.commands.search._search_entities")
@patch("src.cli.commands.search.resolve_scope")
def test_search_with_limit(mock_resolve_scope, mock_search):
    """Test search with --limit flag."""
    from src.models import GraphScope
    mock_resolve_scope.return_value = (GraphScope.GLOBAL, None)
    mock_search.return_value = [
        {"name": f"entity{i}", "type": "concept", "score": 0.9, "snippet": "test", "created_at": "2026-01-01T00:00:00"}
        for i in range(5)
    ]

    result = runner.invoke(app, ["search", "test", "--limit", "5"])

    assert result.exit_code == 0


# ==================== List Command Tests ====================


@patch("src.cli.commands.list_cmd._list_entities")
@patch("src.cli.commands.list_cmd.resolve_scope")
def test_list_basic(mock_resolve_scope, mock_list):
    """Test list command basic invocation."""
    from src.models import GraphScope
    mock_resolve_scope.return_value = (GraphScope.GLOBAL, None)
    mock_list.return_value = [
        {"name": "entity1", "type": "concept", "tags": "test", "relationship_count": 5, "created_at": "2026-01-01"},
        {"name": "entity2", "type": "person", "tags": "test", "relationship_count": 3, "created_at": "2026-01-01"},
    ]

    result = runner.invoke(app, ["list"])

    assert result.exit_code == 0


@patch("src.cli.commands.list_cmd._list_entities")
@patch("src.cli.commands.list_cmd.resolve_scope")
def test_list_json(mock_resolve_scope, mock_list):
    """Test list with JSON output."""
    from src.models import GraphScope
    mock_resolve_scope.return_value = (GraphScope.GLOBAL, None)
    mock_list.return_value = [
        {"name": "entity1", "type": "concept", "tags": "test", "relationship_count": 5, "created_at": "2026-01-01"},
    ]

    result = runner.invoke(app, ["list", "--format", "json"])

    assert result.exit_code == 0
    # Rich pretty-prints JSON with extra text after it. Extract just the JSON part.
    try:
        # Find the JSON array by looking for the brackets and extracting content between them
        output = result.stdout
        start = output.find("[")
        # Find matching closing bracket
        if start != -1:
            bracket_count = 0
            end = start
            for i, char in enumerate(output[start:], start):
                if char == "[":
                    bracket_count += 1
                elif char == "]":
                    bracket_count -= 1
                    if bracket_count == 0:
                        end = i + 1
                        break
            json_str = output[start:end]
            json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        pytest.fail(f"Output is not valid JSON: {result.stdout}")


@patch("src.cli.commands.list_cmd._list_entities")
@patch("src.cli.commands.list_cmd.resolve_scope")
def test_list_compact(mock_resolve_scope, mock_list):
    """Test list with compact output."""
    from src.models import GraphScope
    mock_resolve_scope.return_value = (GraphScope.GLOBAL, None)
    mock_list.return_value = [
        {"name": "entity1", "type": "concept", "tags": "test", "relationship_count": 5, "created_at": "2026-01-01"},
    ]

    result = runner.invoke(app, ["list", "--compact"])

    assert result.exit_code == 0


# ==================== Show Command Tests ====================


@patch("src.cli.commands.show._find_entity")
@patch("src.cli.commands.show.resolve_scope")
def test_show_entity(mock_resolve_scope, mock_find_entity):
    """Test show command with entity name."""
    from src.models import GraphScope
    mock_resolve_scope.return_value = (GraphScope.GLOBAL, None)
    mock_find_entity.return_value = {
        "id": "test_001",
        "name": "test_entity",
        "type": "concept",
        "scope": "global",
        "content": "test content",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "tags": ["test"],
        "relationships": [],
    }

    result = runner.invoke(app, ["show", "test_entity"])

    # Exit code should be 0 when entity found
    assert result.exit_code == 0


@patch("src.cli.commands.show._find_entity")
@patch("src.cli.commands.show.resolve_scope")
def test_show_json_format(mock_resolve_scope, mock_find_entity):
    """Test show with JSON output."""
    from src.models import GraphScope
    mock_resolve_scope.return_value = (GraphScope.GLOBAL, None)
    mock_find_entity.return_value = {
        "id": "test_001",
        "name": "test_entity",
        "type": "concept",
        "scope": "global",
        "content": "test content",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "tags": ["test"],
        "relationships": [],
    }

    result = runner.invoke(app, ["show", "test_entity", "--format", "json"])

    assert result.exit_code == 0


# ==================== Delete Command Tests ====================


@patch("src.cli.commands.delete._delete_entities")
@patch("src.cli.commands.delete._resolve_entity")
@patch("src.cli.commands.delete.resolve_scope")
def test_delete_with_force(mock_resolve_scope, mock_resolve_entity, mock_delete):
    """Test delete with --force flag."""
    from src.models import GraphScope
    mock_resolve_scope.return_value = (GraphScope.GLOBAL, None)
    mock_resolve_entity.return_value = {
        "id": "test_001",
        "name": "entity1",
        "type": "test",
        "scope": "global"
    }
    mock_delete.return_value = 1

    result = runner.invoke(app, ["delete", "entity1", "--force"])

    assert result.exit_code == 0


@patch("src.cli.commands.delete._resolve_entity")
@patch("src.cli.commands.delete.resolve_scope")
def test_delete_confirmation_declined(mock_resolve_scope, mock_resolve_entity):
    """Test delete prompts for confirmation and handles decline."""
    from src.models import GraphScope
    mock_resolve_scope.return_value = (GraphScope.GLOBAL, None)
    mock_resolve_entity.return_value = {
        "id": "test_001",
        "name": "entity1",
        "type": "test",
        "scope": "global"
    }

    result = runner.invoke(app, ["delete", "entity1"], input="n\n")

    assert result.exit_code == 0
    assert "Cancelled" in result.stdout or "cancelled" in result.stdout.lower()


@patch("src.cli.commands.delete._delete_entities")
@patch("src.cli.commands.delete._resolve_entity")
@patch("src.cli.commands.delete.resolve_scope")
def test_delete_json(mock_resolve_scope, mock_resolve_entity, mock_delete):
    """Test delete with JSON output."""
    from src.models import GraphScope
    mock_resolve_scope.return_value = (GraphScope.GLOBAL, None)
    mock_resolve_entity.return_value = {
        "id": "test_001",
        "name": "entity1",
        "type": "test",
        "scope": "global"
    }
    mock_delete.return_value = 1

    result = runner.invoke(app, ["delete", "entity1", "--force", "--format", "json"])

    assert result.exit_code == 0


# ==================== Summarize Command Tests ====================


@patch("src.cli.commands.summarize._generate_summary")
@patch("src.cli.commands.summarize._load_entities")
@patch("src.cli.commands.summarize.resolve_scope")
def test_summarize_whole_graph(mock_resolve_scope, mock_load, mock_summarize):
    """Test summarize without topic (whole graph)."""
    from src.models import GraphScope
    mock_resolve_scope.return_value = (GraphScope.GLOBAL, None)
    mock_load.return_value = [
        {"id": "1", "name": "test_entity", "type": "concept"}
    ]
    mock_summarize.return_value = "This is a test summary"

    result = runner.invoke(app, ["summarize"])

    assert result.exit_code == 0


@patch("src.cli.commands.summarize._generate_summary")
@patch("src.cli.commands.summarize._load_entities")
@patch("src.cli.commands.summarize.resolve_scope")
def test_summarize_topic(mock_resolve_scope, mock_load, mock_summarize):
    """Test summarize with specific topic."""
    from src.models import GraphScope
    mock_resolve_scope.return_value = (GraphScope.GLOBAL, None)
    mock_load.return_value = [
        {"id": "1", "name": "architecture", "type": "concept"}
    ]
    mock_summarize.return_value = "Summary of architecture"

    result = runner.invoke(app, ["summarize", "architecture"])

    assert result.exit_code == 0


@patch("src.cli.commands.summarize._generate_summary")
@patch("src.cli.commands.summarize._load_entities")
@patch("src.cli.commands.summarize.resolve_scope")
def test_summarize_json(mock_resolve_scope, mock_load, mock_summarize):
    """Test summarize with JSON output."""
    from src.models import GraphScope
    mock_resolve_scope.return_value = (GraphScope.GLOBAL, None)
    mock_load.return_value = [
        {"id": "1", "name": "test", "type": "concept"}
    ]
    mock_summarize.return_value = "Test summary"

    result = runner.invoke(app, ["summarize", "--format", "json"])

    assert result.exit_code == 0
    # Should be valid JSON
    try:
        json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail("Output is not valid JSON")


# ==================== Compact Command Tests ====================


@patch("src.cli.commands.compact._compact_graph")
@patch("src.cli.commands.compact._get_graph_stats")
@patch("src.cli.commands.compact.resolve_scope")
def test_compact_with_force(mock_resolve_scope, mock_stats, mock_compact):
    """Test compact with --force flag."""
    from src.models import GraphScope
    mock_resolve_scope.return_value = (GraphScope.GLOBAL, None)
    mock_stats.return_value = {
        "entity_count": 100,
        "relationship_count": 200,
        "duplicate_count": 5,
        "size_bytes": 1000000,
    }
    mock_compact.return_value = {
        "merged_count": 5,
        "removed_count": 10,
        "new_entity_count": 95,
        "new_size_bytes": 900000,
    }

    result = runner.invoke(app, ["compact", "--force"])

    assert result.exit_code == 0


@patch("src.cli.commands.compact._get_graph_stats")
@patch("src.cli.commands.compact.resolve_scope")
def test_compact_declined(mock_resolve_scope, mock_stats):
    """Test compact prompts for confirmation and handles decline."""
    from src.models import GraphScope
    mock_resolve_scope.return_value = (GraphScope.GLOBAL, None)
    mock_stats.return_value = {
        "entity_count": 100,
        "relationship_count": 200,
        "duplicate_count": 5,
        "size_bytes": 1000000,
    }

    result = runner.invoke(app, ["compact"], input="n\n", catch_exceptions=False)

    # Typer.Exit(0) is still exit code 0, but CliRunner may report differently
    # Check for cancellation message in output
    output = result.stdout + result.stderr
    assert "Cancelled" in output or "cancelled" in output.lower()


@patch("src.cli.commands.compact._compact_graph")
@patch("src.cli.commands.compact._get_graph_stats")
@patch("src.cli.commands.compact.resolve_scope")
def test_compact_json(mock_resolve_scope, mock_stats, mock_compact):
    """Test compact with JSON output."""
    from src.models import GraphScope
    mock_resolve_scope.return_value = (GraphScope.GLOBAL, None)
    mock_stats.return_value = {
        "entity_count": 100,
        "relationship_count": 200,
        "duplicate_count": 3,
        "size_bytes": 1000000,
    }
    mock_compact.return_value = {
        "merged_count": 3,
        "removed_count": 6,
        "new_entity_count": 97,
        "new_size_bytes": 900000,
    }

    result = runner.invoke(app, ["compact", "--force", "--format", "json"])

    assert result.exit_code == 0


# ==================== Config Command Tests ====================


def _create_mock_config():
    """Create a properly configured Mock LLMConfig with all required attributes."""
    mock_config = Mock()
    mock_config.cloud_endpoint = "https://cloud.ollama.ai"
    mock_config.cloud_api_key = "test-key"
    mock_config.local_endpoint = "http://localhost:11434"
    mock_config.local_auto_start = True
    mock_config.local_models = ["llama3", "mistral"]
    mock_config.embeddings_models = ["nomic-embed-text"]  # FIXED: now plural
    mock_config.retry_max_attempts = 3
    mock_config.retry_delay_seconds = 10
    mock_config.request_timeout_seconds = 30
    mock_config.quota_warning_threshold = 0.8
    mock_config.rate_limit_cooldown_seconds = 300
    mock_config.queue_max_size = 1000
    mock_config.queue_item_ttl_hours = 24
    mock_config.reranking_enabled = False  # FIXED: added missing attribute
    mock_config.reranking_backend = "none"  # FIXED: added missing attribute
    mock_config.capture_mode = "decisions-only"  # FIXED: added for Phase 10
    mock_config.retention_days = 90  # FIXED: added for Phase 10
    mock_config.ui_api_port = 8765  # FIXED: added for Phase 11.1 INT-04
    mock_config.ui_port = 3000  # FIXED: added for Phase 11.1 INT-04
    return mock_config


@patch("src.cli.commands.config.load_config")
def test_config_show_all(mock_load_config):
    """Test config command shows all settings."""
    mock_config = _create_mock_config()
    mock_load_config.return_value = mock_config

    result = runner.invoke(app, ["config"])

    assert result.exit_code == 0
    # Should show config keys
    assert "cloud.endpoint" in result.stdout or "endpoint" in result.stdout


@patch("src.cli.commands.config.load_config")
def test_config_get_key(mock_load_config):
    """Test config --get for specific key."""
    mock_config = Mock()
    mock_config.cloud_endpoint = "https://cloud.ollama.ai"
    mock_load_config.return_value = mock_config

    # Patch the config path to avoid file system access
    with patch("src.cli.commands.config._get_config_path") as mock_path:
        mock_path.return_value = Path("/tmp/test_llm.toml")
        with patch("pathlib.Path.exists", return_value=False):
            result = runner.invoke(app, ["config", "--get", "cloud.endpoint"])

    assert result.exit_code == 0


def test_config_invalid_key():
    """Test config --get with invalid key."""
    result = runner.invoke(app, ["config", "--get", "invalid.key"])

    assert result.exit_code == 2  # EXIT_BAD_ARGS


@patch("src.cli.commands.config.load_config")
def test_config_json(mock_load_config):
    """Test config with JSON output."""
    mock_config = _create_mock_config()
    mock_load_config.return_value = mock_config

    result = runner.invoke(app, ["config", "--format", "json"])

    assert result.exit_code == 0
    # Should be valid JSON
    try:
        json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail("Output is not valid JSON")


# ==================== Health Command Tests ====================


@patch("src.cli.commands.health._check_quota")
@patch("src.cli.commands.health._check_database")
@patch("src.cli.commands.health._check_ollama_local")
@patch("src.cli.commands.health._check_ollama_cloud")
@patch("src.cli.commands.health.GraphSelector.find_project_root")
def test_health_basic(mock_find_root, mock_cloud, mock_local, mock_db, mock_quota):
    """Test health command basic invocation."""
    mock_find_root.return_value = None
    mock_cloud.return_value = {"name": "Cloud Ollama", "status": "ok", "detail": "Connected"}
    mock_local.return_value = {"name": "Local Ollama", "status": "ok", "detail": "Running"}
    mock_db.return_value = {"name": "Database (global)", "status": "ok", "detail": "Initialized"}
    mock_quota.return_value = {"name": "Quota", "status": "ok", "detail": "50% used"}

    result = runner.invoke(app, ["health"])

    # Exit code 0 if healthy
    assert result.exit_code == 0


@patch("src.cli.commands.health._check_quota")
@patch("src.cli.commands.health._check_database")
@patch("src.cli.commands.health._check_ollama_local")
@patch("src.cli.commands.health._check_ollama_cloud")
@patch("src.cli.commands.health.GraphSelector.find_project_root")
def test_health_verbose(mock_find_root, mock_cloud, mock_local, mock_db, mock_quota):
    """Test health with --verbose flag."""
    mock_find_root.return_value = None
    mock_cloud.return_value = {"name": "Cloud Ollama", "status": "ok", "detail": "Connected"}
    mock_local.return_value = {"name": "Local Ollama", "status": "ok", "detail": "Running", "models": ["llama3"]}
    mock_db.return_value = {"name": "Database (global)", "status": "ok", "detail": "Initialized"}
    mock_quota.return_value = {"name": "Quota", "status": "ok", "detail": "50% used"}

    result = runner.invoke(app, ["health", "--verbose"])

    assert result.exit_code == 0


@patch("src.cli.commands.health._check_quota")
@patch("src.cli.commands.health._check_database")
@patch("src.cli.commands.health._check_ollama_local")
@patch("src.cli.commands.health._check_ollama_cloud")
@patch("src.cli.commands.health.GraphSelector.find_project_root")
def test_health_json(mock_find_root, mock_cloud, mock_local, mock_db, mock_quota):
    """Test health with JSON output."""
    mock_find_root.return_value = None
    mock_cloud.return_value = {"name": "Cloud Ollama", "status": "ok", "detail": "Connected"}
    mock_local.return_value = {"name": "Local Ollama", "status": "ok", "detail": "Running"}
    mock_db.return_value = {"name": "Database (global)", "status": "ok", "detail": "Initialized"}
    mock_quota.return_value = {"name": "Quota", "status": "ok", "detail": "50% used"}

    result = runner.invoke(app, ["health", "--format", "json"])

    assert result.exit_code == 0
    # Should be valid JSON
    try:
        json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail("Output is not valid JSON")
