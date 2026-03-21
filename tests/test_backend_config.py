"""
Unit tests for BackendConfig parsing and Neo4j URI handling.
Wave 0 stubs — all tests skipped until BackendConfig is implemented in Wave 2/3.
"""
import pytest


def test_ladybug_default_when_no_backend_section():
    """load_config() with no [backend] section returns BackendConfig(backend_type='ladybug', backend_uri=None)."""
    from src.llm.config import load_config
    config = load_config()
    assert config.backend_type == "ladybug"
    assert config.backend_uri is None


def test_neo4j_type_parsed_from_toml(tmp_path):
    """[backend] type = 'neo4j' + uri parses into config correctly."""
    import tomllib
    from src.llm.config import load_config
    toml_content = '[backend]\ntype = "neo4j"\nuri = "bolt://neo4j:changeme@localhost:7687"\n'
    cfg_file = tmp_path / "llm.toml"
    cfg_file.write_text(toml_content)
    config = load_config(config_path=cfg_file)
    assert config.backend_type == "neo4j"
    assert config.backend_uri == "bolt://neo4j:changeme@localhost:7687"


def test_bolt_uri_parsed_correctly():
    """parse_bolt_uri extracts (clean_uri, user, password) from bolt://user:pass@host:port."""
    from src.storage.graph_manager import parse_bolt_uri
    clean_uri, user, password = parse_bolt_uri("bolt://neo4j:changeme@localhost:7687")
    assert clean_uri == "bolt://localhost:7687"
    assert user == "neo4j"
    assert password == "changeme"


def test_neo4j_unreachable_raises_on_init(tmp_path):
    """GraphManager._make_driver() with neo4j type and unreachable URI raises SystemExit."""
    from unittest.mock import patch
    from src.llm.config import LLMConfig
    from src.storage.graph_manager import GraphManager
    from src.models import GraphScope
    neo4j_config = LLMConfig(backend_type="neo4j", backend_uri="bolt://neo4j:bad@127.0.0.1:19999")
    manager = GraphManager()
    with patch("src.llm.config.load_config", return_value=neo4j_config):
        with pytest.raises(SystemExit):
            manager.get_driver(scope=GraphScope.GLOBAL)  # triggers Neo4j reachability check
