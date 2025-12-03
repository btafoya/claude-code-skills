---
name: agent-memory
description: Persistent memory system for AI agents with semantic, episodic, and procedural memory types. Use when users want to (1) remember facts, preferences, or context across sessions, (2) track interaction history and experiences, (3) store reusable workflows or procedures, (4) build personalized agents that learn from conversations, or (5) implement any form of long-term memory for AI applications.
---

# Agent Memory Skill

Implements a 4-layer cognitive memory architecture for AI agents:

```
Internal Knowledge (LLM weights) ← frozen
         ↑
Context Window (per inference) ← this skill helps populate
         ↑
Short-Term Memory (session state)
         ↑
Long-Term Memory (persistent storage)
├── Semantic (facts)
├── Episodic (experiences)
└── Procedural (workflows)
```

## Quick Start

```python
from memory import MemoryStore

store = MemoryStore()

# Add semantic memory (facts)
store.add_fact("User prefers TypeScript over JavaScript")

# Add episodic memory (timestamped experience)
store.add_episode("Helped debug authentication issue", topic="auth")

# Add procedural memory (workflow)
store.add_procedure("deploy", ["Run tests", "Build", "Push", "Deploy"])

# Search and retrieve
results = store.search("TypeScript")
context = store.build_context("authentication")  # For prompt injection
```

## Memory Types

| Type | Purpose | Example |
|------|---------|---------|
| **Semantic** | Facts, preferences, relationships | `"User is a Python developer"` |
| **Episodic** | Timestamped experiences | `"[2025-01-15] Debugged JWT expiry issue"` |
| **Procedural** | Workflows, multi-step procedures | `"Code review: 1. Check types, 2. Review errors..."` |

## Core Operations

### Adding Memories

```python
# Semantic: timeless facts
store.add_fact("Project uses PostgreSQL", project="myapp")

# Episodic: what happened when
store.add_episode("User frustrated with Docker networking", emotion="frustrated")

# Procedural: how to do things
store.add_procedure("code_review", [
    "Check type hints",
    "Review error handling",
    "Verify test coverage"
], trigger="user asks for code review")
```

### Updating Facts

Handle the "brother changed jobs" problem—don't just add new facts, update existing ones:

```python
store.update_fact(
    "User's brother is a software engineer",
    "User's brother is now a doctor"
)
```

### Retrieval

```python
# Search (graph backend enables relationship traversal)
results = store.search("database", category="semantic", limit=5)

# Get specific memory types
facts = store.get_by_category("semantic")
recent = store.get_recent_episodes(limit=10)
procedure = store.get_procedure("deploy")
```

### Context Engineering

Build context for LLM prompts from relevant memories:

```python
context = store.build_context(
    query="API authentication",
    max_facts=10,
    max_episodes=5,
    include_procedures=True
)
# Returns formatted string ready for prompt injection
```

## Integration Patterns

### Pattern 1: CLAUDE.md Injection

Export memories and paste into project's CLAUDE.md:

```bash
python -c "from memory import get_store; print(get_store().export_for_prompt())"
```

### Pattern 2: MCP Server

Run `scripts/mcp_server.py` as an MCP server for direct tool access.

**Setup:**
```bash
# Install dependencies with pipx
pipx install mcp
pipx install cogdb  # For graph backend (default)
```

**Add to Claude Code config (~/.config/claude-code/config.json):**
```json
{
  "mcpServers": {
    "memory": {
      "command": "python",
      "args": ["/path/to/agent-memory-skill/scripts/mcp_server.py"]
    }
  }
}
```

Available tools: `memory_add_fact`, `memory_add_episode`, `memory_add_procedure`, `memory_search`, `memory_get_context`, `memory_stats`

### Pattern 3: Session Hooks

```python
# At session start: load relevant context
context = store.build_context(user_query)

# During session: record significant interactions  
store.add_episode("Helped with X", outcome="success")

# At session end: extract and save new facts
store.add_fact("User prefers functional patterns")
```

## Storage

By default, memories persist to `~/.claude_memory/graph/` using CogDB for relationship-aware storage.

For zero-dependency fallback, use `MemoryStore(backend="json")` which stores to `~/.claude_memory/memories.json`.

For enhanced production use, consider adding vector similarity using embeddings (OpenAI, sentence-transformers) alongside the graph storage.

## References

- See `references/memory-theory.md` for cognitive science background
- See `references/storage-patterns.md` for advanced storage options (entities, knowledge graphs)
