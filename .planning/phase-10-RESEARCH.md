# Phase Research: Local Claude-Mem Alternative

**Researched:** March 8, 2026  
**Domain:** Local memory system for Claude Code with Kuzu DB + Ollama  
**Confidence:** HIGH

## Summary

Building a local-only alternative to claude-mem is feasible using the existing graphiti-knowledge-graph infrastructure. The key findings:

1. **Claude Code Hooks**: Fully accessible via `.claude/settings.json` - same mechanism claude-mem uses
2. **Database**: Kuzu has native FTS5 and vector (HNSW) indexes - no migration needed to SQLite
3. **3-Layer Search**: Can implement with Kuzu using FTS for index + vector for semantic + full records for details
4. **Summarization**: Ollama can replace Anthropic API with structured prompting
5. **Architecture**: Current project already has hooks infrastructure and MCP server - need expansion

**Primary recommendation:** Extend existing graphiti infrastructure rather than rebuilding. The current Stop hook can be expanded to support all 6 lifecycle hooks, and Kuzu's FTS/vector capabilities can power the 3-layer search.

## User Constraints (from Context)

> No CONTEXT.md exists - this is a new research phase for v2 planning

## Standard Stack

### Core Technologies
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Kuzu DB | 0.4.x | Graph + FTS + Vector storage | Native FTS5 and HNSW support |
| Ollama | Latest | Local LLM for summarization | 100% local, no API calls |
| Claude Code | Latest | IDE integration via hooks | Target platform |

### Existing Project Components
| Component | Status | Notes |
|-----------|--------|-------|
| `src/hooks/` | Implemented | Claude Stop hook working |
| `src/storage/graph_manager.py` | Implemented | KuzuDriver with FTS workarounds |
| `src/mcp_server/` | Implemented | Tool exposure via stdio |
| `src/capture/summarizer.py` | Implemented | Async conversation capture |

### New Components Needed
| Library | Purpose | Notes |
|---------|---------|-------|
| Python asyncio queue | Observation queuing | For fire-and-forget hooks |
| Structured output parsing | Ollama response parsing | JSON/schema extraction |

## Architecture Patterns

### Recommended Project Structure
```
src/
  hooks/                    # EXISTING - expand
    manager.py               # Current: Stop hook only
    installer.py             # Current: install/uninstall
    templates/               # Current: shell templates
    session.py               # NEW: SessionStart hook handler
    prompt.py                # NEW: UserPromptSubmit handler  
    tooluse.py               # NEW: PostToolUse handler
    cleanup.py               # NEW: SessionEnd handler
  
  memory/                   # NEW: Core memory system
    store.py                # Observation storage (Kuzu)
    search.py                # 3-layer search engine
    summarizer.py            # Ollama-based compression
    worker.py                # Async background processor
  
  mcp_server/               # EXISTING - expand
    tools.py                 # Add search/timeline/get_observations
    memory_tools.py          # NEW: 3-layer MCP tools
  
  config/
    memory.toml              # NEW: Memory-specific config
```

### Pattern 1: Fire-and-Forget Hooks (from claude-mem)

Claude Code hooks must return quickly (< 100ms). The pattern:

```
Hook (fast) → Queue (buffer) → Worker (process)
```

**Implementation:**
- Hooks read stdin, insert into observation_queue table, return immediately
- Background worker polls queue, processes via Ollama, stores compressed observations
- Current project has `src/queue/` - can extend for memory observations

**Example - PostToolUse hook:**
```python
# Read tool input from stdin (JSON)
# Insert into observation_queue (Kuzu table)
# Return {"continue": True, "suppressOutput": True}
# Worker processes async in background
```

### Pattern 2: 3-Layer Progressive Disclosure (from claude-mem)

**Layer 1 - Search (Index):**
- FTS5 query returns compact index (~50-100 tokens/result)
- Includes: ID, timestamp, title, type
- Kuzu: `CALL QUERY_FTS_INDEX('observations', 'idx', 'query')`

**Layer 2 - Timeline (Context):**
- Chronological context around specific observation
- Shows what happened before/during/after
- Kuzu: Time-ordered query with window functions

**Layer 3 - Details (Full):**
- Complete observation data (~500-1000 tokens)
- Only fetched for filtered IDs
- Kuzu: Direct node lookup by ID

### Pattern 3: Queue-Based Processing

```
┌─────────────────────────────────────────────────────┐
│  Hook receives stdin → enqueues → returns immediately│
└─────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────┐
│  Worker polls queue every 1s → Ollama → stores result│
└─────────────────────────────────────────────────────┘
```

**Benefits:**
- Parallel hook execution safe
- Worker failure doesn't block hooks
- Retry logic centralized

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Full-text search | Custom index | Kuzu FTS5 extension | Native, fast, proven |
| Vector search | Custom embeddings | Kuzu HNSW vector index | Native, disk-based |
| Hook execution | Block until done | Queue + worker | Claude Code requirement |
| Summarization | Claude API | Ollama with prompts | 100% local requirement |
| MCP protocol | Custom stdio | Extend existing mcp_server | Already implemented |

**Key insight:** Kuzu has everything needed - FTS5, HNSW vector index, Cypher queries. No SQLite migration needed.

## Common Pitfalls

### Pitfall 1: Hook Blocking Session
**What goes wrong:** Hook takes too long, Claude Code times out
**Why it happens:** Processing observation in-hook instead of queueing
**How to avoid:** Always queue immediately, never call Ollama in hook
**Warning signs:** Hook timeout errors in Claude Code

### Pitfall 2: Context Injection Not Working
**What goes wrong:** SessionStart hook runs but no context appears
**Why it happens:** Output not valid JSON, wrong stdout vs stderr
**How to avoid:** Output JSON to stdout, use `hookSpecificOutput.additionalContext`
**Warning signs:** No errors but no context injection

### Pitfall 3: Token Bloat
**What goes wrong:** Too much context injected, session exceeds limits
**Why it happens:** Fetching full observations instead of using progressive disclosure
**How to avoid:** Implement 3-layer pattern strictly - index first, details only when needed
**Warning signs:** Compaction triggering frequently

### Pitfall 4: Worker Not Starting
**What goes wrong:** Observations queue but never processed
**Why it happens:** Worker not auto-started or crashed
**How to avoid:** Hook triggers worker start, Bun/process manager handles restart
**Warning signs:** Empty observation_queue but no processed records

## Code Examples

### Claude Code Hook Configuration (SessionStart)
```json
{
  "hooks": {
    "SessionStart": [{
      "matcher": "startup|resume|compact",
      "hooks": [{
        "type": "command",
        "command": "graphiti memory context-hook",
        "timeout": 60
      }]
    }]
  }
}
```

### Claude Code Hook Configuration (PostToolUse)
```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "graphiti memory save-hook",
        "timeout": 5
      }]
    }]
  }
}
```

### Kuzu FTS5 Index Creation
```cypher
-- Install FTS extension
INSTALL FTS;

-- Create FTS index on observations
CALL CREATE_FTS_INDEX(
  'observations',
  'obs_fts_idx',
  ['title', 'narrative', 'facts', 'concepts'],
  stemmer := 'porter'
);

-- Query FTS index
CALL QUERY_FTS_INDEX('observations', 'obs_fts_idx', 'authentication bug', 10);
```

### Kuzu Vector Index Creation
```cypher
-- Install vector extension
INSTALL vector;

-- Create vector index on embeddings
CALL CREATE_VECTOR_INDEX(
  'observations',
  'obs_vec_idx',
  'embedding',
  'hnsw',
  128
);

-- Query with similarity
CALL QUERY_VECTOR_INDEX(
  'observations',
  'obs_vec_idx',
  $query_embedding,
  10
);
```

### Ollama Summarization Prompt
```
You are an expert code analyst. Create a structured summary of the following Claude Code observation.

Format your response as:
<summary>
  <request>What the user asked for</request>
  <investigated>What was examined/checked</investigated>
  <learned>Key discoveries about the codebase</learned>
  <completed>Work that was completed</completed>
  <next_steps>Remaining tasks or suggestions</next_steps>
  <files_read>List of files examined</files_read>
  <files_modified>List of files changed</files_modified>
  <concepts>Key concepts or patterns identified</concepts>
</summary>

Observation:
{tool_input}
{tool_output}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| External vector DB (Chroma) | Kuzu native HNSW | 2025 | Single DB for graph + vectors |
| SQLite FTS5 | Kuzu FTS5 | 2025 | Single DB for all storage |
| Claude API summarization | Ollama local | Now | 100% local, no API costs |
| Single hook (Stop) | 6 lifecycle hooks | Phase 2 | Full memory lifecycle |

**Deprecated/outdated:**
- ChromaDB: Now unnecessary with Kuzu vector index
- Anthropic API: Replaced with Ollama for local-only
- Single observation type: Expand to decision/bugfix/feature/refactor/discovery

## Open Questions

1. **Hook matcher behavior**: Does SessionStart with `startup|resume|compact` cover all session start scenarios?
   - What we know: claude-mem uses this pattern successfully
   - Recommendation: Test with Claude Code 1.x and 2.x

2. **Worker process management**: How to keep worker running across sessions?
   - What we know: claude-mem uses Bun, we could use Python asyncio or systemd
   - Recommendation: Start worker on first hook call, keep alive with heartbeat

3. **Observation deduplication**: How to avoid storing duplicate observations?
   - What we know: Need session_id + tool_name + hash of input
   - Recommendation: Add deduplication check in queue processor

4. **Context size limits**: How much context to inject at session start?
   - What we know: claude-mem uses ~50 recent observations + 10 session summaries
   - Recommendation: Start with this, adjust based on token usage

## Sources

### Primary (HIGH confidence)
- Kuzu FTS Documentation - https://docs.kuzudb.com/extensions/full-text-search
- Kuzu Vector Documentation - https://docs.kuzudb.com/extensions/vector
- Claude Code Hooks Official - https://docs.claude.com/claude-code/hooks

### Secondary (MEDIUM confidence)
- claude-mem Hooks Architecture - https://docs.claude-mem.ai/hooks-architecture
- claude-mem Database Architecture - https://docs.claude-mem.ai/architecture/database
- claude-mem Search Architecture - https://docs.claude-mem.ai/architecture/search-architecture

### Tertiary (LOW confidence)
- Ollama Python Examples - https://github.com/ollama/ollama-python/tree/main/examples
- Claude Code Hooks Guide - https://aiorg.dev/blog/claude-code-hooks (2026 edition)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Kuzu provides all needed features natively
- Architecture: HIGH - Patterns well-documented in claude-mem
- Pitfalls: MEDIUM - Based on claude-mem issues, need to verify with implementation

**Research date:** March 8, 2026
**Valid until:** June 2026 (6 months - stable technology)
