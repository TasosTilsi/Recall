"""Tests for Phase 15 Local Memory System hooks and installer.

Covers MEM-01 through MEM-05.

Run: pytest tests/test_hooks_phase15.py -x -q
Integration tests (require Ollama): pytest tests/test_hooks_phase15.py -x -q -m integration
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

# Project root (tests/ is one level below project root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SESSION_START = str(PROJECT_ROOT / "src/hooks/session_start.py")
INJECT_CONTEXT = str(PROJECT_ROOT / "src/hooks/inject_context.py")
CAPTURE_ENTRY = str(PROJECT_ROOT / "src/hooks/capture_entry.py")
SESSION_STOP = str(PROJECT_ROOT / "src/hooks/session_stop.py")


# ── helpers ───────────────────────────────────────────────────────────────────

def _run_hook(script_path: str, stdin_data: str, timeout: int = 10) -> subprocess.CompletedProcess:
    """Run a hook script with given stdin."""
    return subprocess.run(
        [sys.executable, script_path],
        input=stdin_data,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _extract_json_from_stdout(stdout: str) -> dict:
    """Extract JSON object from hook stdout.

    Hooks may emit structlog lines before the JSON payload.
    Parse the last non-empty line that starts with '{'.
    """
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    for line in reversed(lines):
        if line.startswith("{"):
            return json.loads(line)
    raise json.JSONDecodeError("No JSON object found in stdout", stdout, 0)


# ── MEM-01: hook timing and fail-open ─────────────────────────────────────────

def test_session_start_exits_zero():
    """SessionStart exits 0 with empty stdin (fail-open).

    Pass a non-git cwd so GitIndexer fails fast without loading an LLM —
    the fail-open contract (exit 0) is what matters here.
    """
    import json
    result = _run_hook(SESSION_START, json.dumps({"cwd": "/tmp", "session_id": "test-failopen"}))
    assert result.returncode == 0, f"Non-zero exit: {result.stderr}"


def test_session_start_produces_no_structured_stdout():
    """SessionStart must not write JSON context to stdout (would corrupt Claude Code session).

    Claude Code does not parse SessionStart stdout as JSON context.
    The hook may emit structlog debug lines; we verify no JSON object is emitted
    (which would be misinterpreted by Claude Code as hook output).
    """
    result = _run_hook(SESSION_START, json.dumps({"cwd": "/tmp", "session_id": "t"}))
    # If stdout exists, it must NOT be a JSON object (which Claude Code would parse)
    if result.stdout.strip():
        try:
            json.loads(result.stdout.strip())
            # If we get here, stdout is valid JSON — that would be a problem
            pytest.fail(
                f"SessionStart emitted parseable JSON to stdout "
                f"(would corrupt Claude Code context): {result.stdout!r}"
            )
        except json.JSONDecodeError:
            pass  # Non-JSON output (e.g. structlog lines) is acceptable


def test_capture_entry_exits_fast():
    """PostToolUse hook must complete in less than 1s for fire-and-forget contract."""
    hook_input = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "ls"},
        "tool_response": {"content": "file.txt"},
        "session_id": "test-uuid",
        "cwd": "/tmp",
    })
    start = time.monotonic()
    result = _run_hook(CAPTURE_ENTRY, hook_input, timeout=3)
    elapsed = time.monotonic() - start
    assert result.returncode == 0, f"Non-zero exit: {result.stderr}"
    assert elapsed < 1.0, f"capture_entry took {elapsed:.3f}s (budget: 1s)"


def test_inject_context_output_format():
    """UserPromptSubmit hook must output JSON with 'context' key on empty prompt (fast path).

    Uses empty prompt to exercise the fail-open path without triggering Ollama model loads.
    """
    # Empty prompt exercises the fail-open path: returns {"context": ""} immediately
    hook_input = json.dumps({"prompt": "", "cwd": "/tmp", "session_id": "t"})
    result = _run_hook(INJECT_CONTEXT, hook_input, timeout=8)
    assert result.returncode == 0, f"Non-zero exit: {result.stderr}"
    try:
        data = _extract_json_from_stdout(result.stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"No JSON object found in stdout: {result.stdout!r} error: {e}")
    assert "context" in data, f"Missing 'context' key in output: {data}"
    assert isinstance(data["context"], str), f"context must be str, got {type(data['context'])}"


@pytest.mark.integration
def test_inject_context_output_format_with_prompt():
    """UserPromptSubmit hook must output JSON with 'context' key for non-empty prompt.

    Marked integration: inject_context may load Ollama models when graph service
    is available and a non-empty prompt is provided.
    """
    hook_input = json.dumps({"prompt": "test query", "cwd": "/tmp", "session_id": "t"})
    result = _run_hook(INJECT_CONTEXT, hook_input, timeout=30)
    assert result.returncode == 0, f"Non-zero exit: {result.stderr}"
    try:
        data = _extract_json_from_stdout(result.stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"No JSON object found in stdout: {result.stdout!r} error: {e}")
    assert "context" in data, f"Missing 'context' key in output: {data}"
    assert isinstance(data["context"], str), f"context must be str, got {type(data['context'])}"


def test_all_hooks_fail_open_on_bad_input():
    """All 4 hooks must exit 0 when given invalid JSON stdin."""
    bad_input = "THIS IS NOT JSON {"
    for script, name in [
        (SESSION_START, "session_start"),
        (INJECT_CONTEXT, "inject_context"),
        (CAPTURE_ENTRY, "capture_entry"),
        (SESSION_STOP, "session_stop"),
    ]:
        result = _run_hook(script, bad_input, timeout=5)
        assert result.returncode == 0, (
            f"{name} failed with bad input (exit {result.returncode}): {result.stderr}"
        )


# ── MEM-02: capture pipeline ──────────────────────────────────────────────────

def test_capture_entry_writes_jsonl(tmp_path):
    """PostToolUse: Write tool appends 1 line to pending_tool_captures.jsonl."""
    (tmp_path / ".graphiti").mkdir(parents=True, exist_ok=True)
    hook_input = json.dumps({
        "tool_name": "Write",
        "tool_input": {"file_path": "/tmp/test.py"},
        "tool_response": {"content": "written"},
        "session_id": "test-uuid",
        "cwd": str(tmp_path),
    })
    result = _run_hook(CAPTURE_ENTRY, hook_input, timeout=3)
    assert result.returncode == 0

    jsonl_file = tmp_path / ".graphiti" / "pending_tool_captures.jsonl"
    assert jsonl_file.exists(), f"jsonl file not created at {jsonl_file}"

    lines = [line.strip() for line in jsonl_file.read_text().splitlines() if line.strip()]
    assert len(lines) == 1, f"Expected 1 line, got {len(lines)}: {lines}"

    entry = json.loads(lines[0])
    assert entry["tool_name"] == "Write"
    assert "session_id" in entry


def test_capture_entry_sanitizes_content(tmp_path):
    """PostToolUse: secret-containing content must be sanitized before writing."""
    (tmp_path / ".graphiti").mkdir(parents=True, exist_ok=True)
    hook_input = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "echo GRAPHITI_API_KEY=super_secret_value"},
        "tool_response": {"content": "GRAPHITI_API_KEY=super_secret_value"},
        "session_id": "test-uuid",
        "cwd": str(tmp_path),
    })
    result = _run_hook(CAPTURE_ENTRY, hook_input, timeout=3)
    assert result.returncode == 0

    jsonl_file = tmp_path / ".graphiti" / "pending_tool_captures.jsonl"
    content = jsonl_file.read_text() if jsonl_file.exists() else ""
    # Security invariant: raw secret value must not appear in stored content
    assert "super_secret_value" not in content, (
        "Secret content was stored without sanitization!"
    )


def test_capture_entry_ignores_non_captured_tools(tmp_path):
    """PostToolUse: Read tool must not create a jsonl entry."""
    (tmp_path / ".graphiti").mkdir(parents=True, exist_ok=True)
    hook_input = json.dumps({
        "tool_name": "Read",
        "tool_input": {"file_path": "/tmp/test.py"},
        "tool_response": {"content": "content"},
        "session_id": "test-uuid",
        "cwd": str(tmp_path),
    })
    result = _run_hook(CAPTURE_ENTRY, hook_input, timeout=3)
    assert result.returncode == 0

    jsonl_file = tmp_path / ".graphiti" / "pending_tool_captures.jsonl"
    if jsonl_file.exists():
        content = jsonl_file.read_text().strip()
        assert content == "", f"Read tool should not create entries: {content!r}"


# ── MEM-03: note command (replaced memory search in Phase 16) ─────────────────

def test_note_command_importable():
    """recall note command module must be importable (replaced memory in Phase 16)."""
    from src.cli.commands.note_cmd import note_command
    assert note_command is not None


def test_note_command_registered():
    """note must be registered in main CLI app (replaced memory in Phase 16)."""
    from src.cli import app
    all_names = [c.name for c in app.registered_commands]
    assert "note" in all_names, f"note not in registered commands: {all_names}"


# ── MEM-04: context injection format ─────────────────────────────────────────

def test_inject_context_empty_prompt_returns_empty():
    """inject_context must return empty context when prompt is empty."""
    hook_input = json.dumps({"prompt": "", "cwd": "/tmp", "session_id": "t"})
    result = _run_hook(INJECT_CONTEXT, hook_input, timeout=8)
    assert result.returncode == 0
    try:
        data = _extract_json_from_stdout(result.stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"No JSON object found in stdout: {result.stdout!r} error: {e}")
    assert data == {"context": ""}, f"Expected empty context, got: {data}"


def test_inject_context_token_budget():
    """inject_context must respect 4000 token budget (len//4 approx)."""
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    try:
        from src.hooks.inject_context import _build_option_c, _approx_tokens
    except ImportError:
        pytest.skip("inject_context not importable")

    large_items = [
        {"snippet": "x" * 400, "created_at": "2026-01-01T00:00:00", "name": f"item_{i}"}
        for i in range(50)
    ]
    result = _build_option_c(
        continuity="Previous session summary here.",
        history_items=large_items,
        token_budget=4000,
    )
    actual_tokens = _approx_tokens(result)
    assert actual_tokens <= 4000, f"Output exceeds 4000 token budget: {actual_tokens} tokens"


# ── MEM-05: install + additive ────────────────────────────────────────────────

def test_install_global_hooks_writes_all_5_types(tmp_path, monkeypatch):
    """install_global_hooks() must write all 5 hook types to settings.json."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    from src.hooks.installer import install_global_hooks

    result = install_global_hooks()
    assert result is True

    settings_path = tmp_path / ".claude" / "settings.json"
    assert settings_path.exists(), f"settings.json not created at {settings_path}"

    data = json.loads(settings_path.read_text())
    required = {"SessionStart", "UserPromptSubmit", "PostToolUse", "PreCompact", "Stop"}
    for hook_type in required:
        assert hook_type in data.get("hooks", {}), f"{hook_type} missing from hooks"


def test_install_preserves_existing_non_graphiti_entries(tmp_path, monkeypatch):
    """install_global_hooks() must NOT remove pre-existing non-graphiti entries."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    pre_existing = {
        "hooks": {
            "Stop": [{
                "matcher": "",
                "hooks": [{"type": "command", "command": "some-other-tool stop"}]
            }]
        }
    }
    settings_path.write_text(json.dumps(pre_existing))

    from src.hooks.installer import install_global_hooks
    install_global_hooks()

    data = json.loads(settings_path.read_text())
    stop_entries = data.get("hooks", {}).get("Stop", [])
    assert len(stop_entries) >= 2, f"Pre-existing entry was removed: {stop_entries}"

    all_commands = [h.get("command", "") for e in stop_entries for h in e.get("hooks", [])]
    assert any("some-other-tool" in cmd for cmd in all_commands), (
        f"Non-graphiti entry was removed! Commands: {all_commands}"
    )


def test_install_global_overwrites_existing_graphiti_entries(tmp_path, monkeypatch):
    """install_global_hooks() must replace old graphiti entries (clean overwrite)."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    old_graphiti = {
        "hooks": {
            "Stop": [{
                "matcher": "",
                "hooks": [{"type": "command", "command": "/old/path/session_stop.py"}]
            }]
        }
    }
    settings_path.write_text(json.dumps(old_graphiti))

    from src.hooks.installer import install_global_hooks
    install_global_hooks()

    data = json.loads(settings_path.read_text())
    stop_entries = data.get("hooks", {}).get("Stop", [])
    all_commands = [h.get("command", "") for e in stop_entries for h in e.get("hooks", [])]

    assert not any("/old/path" in cmd for cmd in all_commands), (
        f"Old graphiti entry was not replaced: {all_commands}"
    )
    assert any("session_stop.py" in cmd for cmd in all_commands), (
        f"New session_stop.py entry not present: {all_commands}"
    )
