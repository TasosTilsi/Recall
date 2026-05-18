"""SQLite schema DDL for recall knowledge graph database."""

SCHEMA_VERSION = "3.0"

# --- Core tables ---

DDL_COMMITS = """
CREATE TABLE IF NOT EXISTS commits (
    sha         TEXT PRIMARY KEY,
    message     TEXT NOT NULL,
    author      TEXT NOT NULL,
    date        TEXT NOT NULL,
    files_changed TEXT NOT NULL DEFAULT '[]',
    external_context TEXT NOT NULL DEFAULT ''
)
"""

DDL_ENTITIES = """
CREATE TABLE IF NOT EXISTS entities (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL CHECK(type IN ('decision','bug_fix','pattern','file','concept','tech_debt','workflow','business_rule')),
    name        TEXT NOT NULL,
    content     TEXT NOT NULL DEFAULT '',
    commit_sha  TEXT REFERENCES commits(sha),
    tags        TEXT NOT NULL DEFAULT '[]',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
)
"""

DDL_BACKLINKS = """
CREATE TABLE IF NOT EXISTS backlinks (
    from_id      TEXT NOT NULL REFERENCES entities(id),
    to_id        TEXT NOT NULL REFERENCES entities(id),
    relationship TEXT NOT NULL,
    context      TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (from_id, to_id, relationship)
)
"""

DDL_METADATA = """
CREATE TABLE IF NOT EXISTS metadata (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
"""

# --- FTS5 virtual table ---

DDL_ENTITIES_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts
USING fts5(
    name,
    content,
    content=entities,
    content_rowid=rowid,
    tokenize='porter unicode61'
)
"""

# FTS triggers to keep entities_fts in sync with entities
DDL_FTS_INSERT_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS entities_ai AFTER INSERT ON entities BEGIN
    INSERT INTO entities_fts(rowid, name, content) VALUES (new.rowid, new.name, new.content);
END
"""

DDL_FTS_DELETE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS entities_ad AFTER DELETE ON entities BEGIN
    INSERT INTO entities_fts(entities_fts, rowid, name, content) VALUES('delete', old.rowid, old.name, old.content);
END
"""

DDL_FTS_UPDATE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS entities_au AFTER UPDATE ON entities BEGIN
    INSERT INTO entities_fts(entities_fts, rowid, name, content) VALUES('delete', old.rowid, old.name, old.content);
    INSERT INTO entities_fts(rowid, name, content) VALUES (new.rowid, new.name, new.content);
END
"""

# --- Backlinks auto-inverse trigger ---
# When A->B is inserted, automatically insert B->A with "inverse:" prefix on relationship label
DDL_BACKLINKS_INVERSE_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS backlinks_auto_inverse
AFTER INSERT ON backlinks
WHEN NOT EXISTS (
    SELECT 1 FROM backlinks WHERE from_id = NEW.to_id AND to_id = NEW.from_id AND relationship = 'inverse:' || NEW.relationship
)
BEGIN
    INSERT OR IGNORE INTO backlinks (from_id, to_id, relationship, context)
    VALUES (NEW.to_id, NEW.from_id, 'inverse:' || NEW.relationship, NEW.context);
END
"""

# --- Optional embeddings table ---

DDL_EMBEDDINGS = """
CREATE TABLE IF NOT EXISTS embeddings (
    entity_id  TEXT PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE,
    vector     BLOB NOT NULL
)
"""

DDL_SUMMARIES = """
CREATE TABLE IF NOT EXISTS summaries (
    id          TEXT PRIMARY KEY,
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    commit_sha  TEXT REFERENCES commits(sha),
    parent_id   TEXT REFERENCES summaries(id),
    scope       TEXT NOT NULL DEFAULT 'project'
)
"""

# Ordered list for init_db to execute
CORE_DDL = [
    DDL_COMMITS,
    DDL_ENTITIES,
    DDL_BACKLINKS,
    DDL_METADATA,
    DDL_ENTITIES_FTS,
    DDL_FTS_INSERT_TRIGGER,
    DDL_FTS_DELETE_TRIGGER,
    DDL_FTS_UPDATE_TRIGGER,
    DDL_BACKLINKS_INVERSE_TRIGGER,
    DDL_SUMMARIES,
]
