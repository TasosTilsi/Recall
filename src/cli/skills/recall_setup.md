---
name: recall-setup
description: >
  Interactive setup walkthrough for the recall knowledge graph.
  Guides the user through configuring ~/.recall/config.toml and verifying the installation.
trigger: /recall-setup
---

# /recall-setup — recall Configuration Walkthrough

You are guiding the user through setting up recall, a local engineering knowledge graph.
Walk through each step conversationally. Do not rush — confirm each step before moving on.

## Step 1: Check for existing config

Run this in your Bash tool:
```bash
cat ~/.recall/config.toml 2>/dev/null || echo "NO_CONFIG"
```

- If config exists and user wants to keep it → skip to Step 4 (health check)
- If config exists and user wants to reconfigure → proceed with Step 2
- If no config → proceed with Step 2

## Step 2: Choose LLM provider

Ask the user: "Which LLM provider would you like to use?"

Options:
1. **claude** (recommended) — uses the `claude` CLI subprocess, no API key needed
2. **ollama** — local models via Ollama, no API key needed; ask which model (suggest `gemma2:9b`)
3. **openai** — OpenAI or compatible API; ask for base URL and API key

For embeddings, always use **ollama** with `nomic-embed-text` (local, no cost). Confirm Ollama is running.

## Step 3: Write config.toml

Based on the user's choices, write `~/.recall/config.toml` using the Write tool:

For **claude** provider:
```toml
[llm]
provider = "claude"
model = "claude-haiku-4-5-20251001"
url = ""
api_key = ""

[embeddings]
provider = "ollama"
model = "nomic-embed-text"
url = "http://localhost:11434"
api_key = ""

[db]
path = ".recall/recall.db"
```

For **ollama** provider (replace model with user's choice):
```toml
[llm]
provider = "ollama"
model = "gemma2:9b"
url = "http://localhost:11434"
api_key = ""

[embeddings]
provider = "ollama"
model = "nomic-embed-text"
url = "http://localhost:11434"
api_key = ""

[db]
path = ".recall/recall.db"
```

For **openai** provider (fill in user's url and api_key):
```toml
[llm]
provider = "openai"
model = "gpt-4o-mini"
url = "https://api.openai.com/v1"
api_key = "sk-..."

[embeddings]
provider = "ollama"
model = "nomic-embed-text"
url = "http://localhost:11434"
api_key = ""

[db]
path = ".recall/recall.db"
```

## Step 4: Verify with recall health

Run:
```bash
recall health
```

- If health passes → proceed to Step 5.
- If health fails → show the error output, diagnose (common issues: Ollama not running, claude CLI not found), and offer to fix before continuing.

## Step 5: Optionally index the current repo

Ask the user: "Would you like to index the current repository's git history now? This runs `recall init` and may take a few minutes for large repos."

- If **yes** → run:
  ```bash
  recall init 2>&1
  ```
  Report the result: commits indexed, any errors. Then confirm: "Indexing complete. recall will now inject relevant context at the start of each Claude session."

- If **no** → confirm: "recall is configured and healthy. Run /recall-index any time to index a repository."

## Important

- Do NOT show raw TOML to the user unless they ask
- Do NOT invent API keys — ask the user to paste them
- If the user has an existing config.toml, show them its current values before asking if they want to change anything
