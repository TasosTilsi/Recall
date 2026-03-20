"""Retention integration tests covering all 6 RETN requirements.

Tests verify CLI plumbing at the command level using CliRunner and mocks.
No live graph or Ollama connections required.

Requirements covered:
- RETN-01: compact --expire archives stale nodes
- RETN-02: stale command previews nodes with 25-row cap
- RETN-03: retention_days config loaded from llm.toml [retention] section
- RETN-04: pin command protects a node
- RETN-05: unpin command removes protection
- RETN-06: access recording increments access_count
"""

import pytest
from typer.testing import CliRunner
from unittest.mock import MagicMock, patch
from pathlib import Path


@pytest.fixture()
def runner() -> CliRunner:
    """Shared CliRunner for CLI invocation."""
    return CliRunner()


def _fake_stale_nodes(n: int) -> list[dict]:
    """Build n fake stale node dicts matching GraphService.list_stale() output."""
    return [
        {
            "uuid": f"uuid-stale-{i:04d}",
            "name": f"StaleNode{i}",
            "age_days": 120 + i,
            "score": round(0.9 - i * 0.01, 2),
        }
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# RETN-01: compact --expire archives stale nodes
# ---------------------------------------------------------------------------

class TestRetn01CompactExpire:
    def test_compact_expire_archives_stale_nodes(self, runner: CliRunner):
        """RETN-01: list --compact calls archive_nodes and prints 'Archived N'.

        Phase 16: `compact --expire` absorbed into `list --compact`.
        """
        from src.cli import app

        stale = _fake_stale_nodes(2)
        mock_service = MagicMock()

        with (
            patch("src.cli.commands.list_cmd.get_service", return_value=mock_service),
            patch(
                "src.cli.commands.list_cmd.run_graph_operation",
                side_effect=[stale, 2],
            ),
            patch("src.cli.utils.confirm_action", return_value=True),
        ):
            result = runner.invoke(app, ["list", "--compact"])

        assert result.exit_code == 0, f"stdout:\n{result.stdout}"
        assert "Archived 2" in result.stdout

    def test_compact_expire_no_stale_nodes(self, runner: CliRunner):
        """RETN-01: list --compact exits cleanly when no stale nodes exist.

        Phase 16: `compact --expire` absorbed into `list --compact`.
        """
        from src.cli import app

        mock_service = MagicMock()

        with (
            patch("src.cli.commands.list_cmd.get_service", return_value=mock_service),
            patch("src.cli.commands.list_cmd.run_graph_operation", return_value=[]),
        ):
            result = runner.invoke(app, ["list", "--compact"])

        assert result.exit_code == 0
        assert "No stale nodes" in result.stdout


# ---------------------------------------------------------------------------
# RETN-02: stale command with display cap
# ---------------------------------------------------------------------------

class TestRetn02StalePreview:
    def test_stale_shows_node_names(self, runner: CliRunner):
        """RETN-02: list --stale displays stale node names.

        Phase 16: `stale` command absorbed into `list --stale`.
        """
        from src.cli import app

        stale = _fake_stale_nodes(3)
        mock_service = MagicMock()

        with (
            patch("src.cli.commands.list_cmd.get_service", return_value=mock_service),
            patch("src.cli.commands.list_cmd.run_graph_operation", return_value=stale),
        ):
            result = runner.invoke(app, ["list", "--stale"])

        assert result.exit_code == 0, f"stdout:\n{result.stdout}"
        assert "StaleNode0" in result.stdout
        assert "StaleNode2" in result.stdout
        # No cap summary line for <= 25 nodes
        assert "Showing 25 of" not in result.stdout

    def test_stale_shows_cap_summary_for_many_nodes(self, runner: CliRunner):
        """RETN-02: list --stale shows 'Showing 25 of 30' when results > 25.

        Phase 16: `stale` command absorbed into `list --stale`.
        """
        from src.cli import app

        stale = _fake_stale_nodes(30)
        mock_service = MagicMock()

        with (
            patch("src.cli.commands.list_cmd.get_service", return_value=mock_service),
            patch("src.cli.commands.list_cmd.run_graph_operation", return_value=stale),
        ):
            result = runner.invoke(app, ["list", "--stale"])

        assert result.exit_code == 0, f"stdout:\n{result.stdout}"
        assert "Showing 25 of 30" in result.stdout

    def test_stale_no_nodes_shows_success(self, runner: CliRunner):
        """RETN-02: list --stale shows success message when graph is fresh.

        Phase 16: `stale` command absorbed into `list --stale`.
        """
        from src.cli import app

        mock_service = MagicMock()

        with (
            patch("src.cli.commands.list_cmd.get_service", return_value=mock_service),
            patch("src.cli.commands.list_cmd.run_graph_operation", return_value=[]),
        ):
            result = runner.invoke(app, ["list", "--stale"])

        assert result.exit_code == 0
        assert "No stale nodes" in result.stdout


# ---------------------------------------------------------------------------
# RETN-03: retention_days config loaded from [retention] section
# ---------------------------------------------------------------------------

class TestRetn03RetentionConfig:
    def test_load_config_reads_retention_days_from_toml(self, tmp_path: Path):
        """RETN-03: load_config() reads retention_days=60 from [retention] section."""
        from src.llm.config import load_config

        config_file = tmp_path / "llm.toml"
        config_file.write_text(
            "[retention]\n"
            "retention_days = 60\n",
            encoding="utf-8",
        )

        config = load_config(config_file)
        assert config.retention_days == 60

    def test_load_config_defaults_to_90_days(self, tmp_path: Path):
        """RETN-03: load_config() defaults to 90 retention_days when section absent."""
        from src.llm.config import load_config

        config_file = tmp_path / "llm.toml"
        config_file.write_text("# empty config\n", encoding="utf-8")

        config = load_config(config_file)
        assert config.retention_days == 90

    def test_load_config_enforces_minimum_30_days(self, tmp_path: Path):
        """RETN-03: load_config() resets retention_days to 90 when configured < 30."""
        from src.llm.config import load_config

        config_file = tmp_path / "llm.toml"
        config_file.write_text(
            "[retention]\n"
            "retention_days = 5\n",
            encoding="utf-8",
        )

        config = load_config(config_file)
        assert config.retention_days == 90  # reset to default, not minimum


# ---------------------------------------------------------------------------
# RETN-04: pin command
# ---------------------------------------------------------------------------

class TestRetn04Pin:
    def test_pin_command_calls_pin_node(self, runner: CliRunner):
        """RETN-04: pin <uuid> calls RetentionManager.pin_node with correct uuid."""
        from src.cli import app

        retention = MagicMock()
        mock_service = MagicMock()
        mock_service._get_group_id.return_value = "global"

        with (
            patch("src.cli.commands.pin.get_service", return_value=mock_service),
            patch("src.cli.commands.pin.get_retention_manager", return_value=retention),
        ):
            result = runner.invoke(app, ["pin", "test-uuid-1234"])

        assert result.exit_code == 0, f"stdout:\n{result.stdout}"
        retention.pin_node.assert_called_once()
        call_kwargs = retention.pin_node.call_args
        args = call_kwargs.args
        kwargs = call_kwargs.kwargs
        called_uuid = kwargs.get("uuid") or (args[0] if args else None)
        assert called_uuid == "test-uuid-1234"

    def test_pin_command_prints_pinned_message(self, runner: CliRunner):
        """RETN-04: pin command output includes 'pinned'."""
        from src.cli import app

        retention = MagicMock()
        mock_service = MagicMock()
        mock_service._get_group_id.return_value = "global"

        with (
            patch("src.cli.commands.pin.get_service", return_value=mock_service),
            patch("src.cli.commands.pin.get_retention_manager", return_value=retention),
        ):
            result = runner.invoke(app, ["pin", "test-uuid-1234"])

        assert "pinned" in result.stdout.lower()


# ---------------------------------------------------------------------------
# RETN-05: unpin command
# ---------------------------------------------------------------------------

class TestRetn05Unpin:
    def test_unpin_command_calls_unpin_node(self, runner: CliRunner):
        """RETN-05: unpin <uuid> calls RetentionManager.unpin_node."""
        from src.cli import app

        retention = MagicMock()
        mock_service = MagicMock()
        mock_service._get_group_id.return_value = "global"

        with (
            patch("src.cli.commands.pin.get_service", return_value=mock_service),
            patch("src.cli.commands.pin.get_retention_manager", return_value=retention),
        ):
            result = runner.invoke(app, ["unpin", "test-uuid-1234"])

        assert result.exit_code == 0, f"stdout:\n{result.stdout}"
        retention.unpin_node.assert_called_once()
        call_kwargs = retention.unpin_node.call_args
        args = call_kwargs.args
        kwargs = call_kwargs.kwargs
        called_uuid = kwargs.get("uuid") or (args[0] if args else None)
        assert called_uuid == "test-uuid-1234"

    def test_unpin_command_prints_unpinned_message(self, runner: CliRunner):
        """RETN-05: unpin command output includes 'unpinned'."""
        from src.cli import app

        retention = MagicMock()
        mock_service = MagicMock()
        mock_service._get_group_id.return_value = "global"

        with (
            patch("src.cli.commands.pin.get_service", return_value=mock_service),
            patch("src.cli.commands.pin.get_retention_manager", return_value=retention),
        ):
            result = runner.invoke(app, ["unpin", "test-uuid-1234"])

        assert "unpinned" in result.stdout.lower()


# ---------------------------------------------------------------------------
# RETN-06: access recording increments access_count
# ---------------------------------------------------------------------------

class TestRetn06AccessRecording:
    def test_record_access_increments_count(self, tmp_path: Path):
        """RETN-06: record_access increments access_count for same uuid+scope."""
        from src.retention import RetentionManager

        db = RetentionManager(db_path=tmp_path / "retention.db")

        db.record_access(uuid="uuid-target", scope="project:/tmp/test")
        db.record_access(uuid="uuid-target", scope="project:/tmp/test")

        record = db.get_access_record(uuid="uuid-target", scope="project:/tmp/test")
        assert record is not None
        assert record["access_count"] == 2

    def test_record_access_separate_scopes_tracked_independently(self, tmp_path: Path):
        """RETN-06: access counts are per (uuid, scope) pair, not just uuid."""
        from src.retention import RetentionManager

        db = RetentionManager(db_path=tmp_path / "retention.db")

        db.record_access(uuid="uuid-shared", scope="scope-a")
        db.record_access(uuid="uuid-shared", scope="scope-a")
        db.record_access(uuid="uuid-shared", scope="scope-b")

        record_a = db.get_access_record(uuid="uuid-shared", scope="scope-a")
        record_b = db.get_access_record(uuid="uuid-shared", scope="scope-b")

        assert record_a is not None
        assert record_a["access_count"] == 2
        assert record_b is not None
        assert record_b["access_count"] == 1

    def test_record_access_first_access_count_is_one(self, tmp_path: Path):
        """RETN-06: first access creates a record with access_count=1."""
        from src.retention import RetentionManager

        db = RetentionManager(db_path=tmp_path / "retention.db")

        db.record_access(uuid="uuid-new", scope="global")
        record = db.get_access_record(uuid="uuid-new", scope="global")

        assert record is not None
        assert record["access_count"] == 1
