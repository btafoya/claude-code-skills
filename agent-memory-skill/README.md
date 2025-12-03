# Agent Memory Skill

A persistent memory system for AI agents, implementing cognitive memory architecture with semantic, episodic, and procedural memory types. Designed for use with [Claude Code](https://claude.com/claude-code).

## Overview

LLMs have vast but frozen knowledge—they cannot learn by updating weights after training. Without memory, an agent is like "an intern with amnesia": brilliant but unable to recall previous conversations or learn from experience.

This skill implements a **4-layer cognitive memory architecture**:

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

## Memory Types

| Type | Purpose | Example |
|------|---------|---------|
| **Semantic** | Facts, preferences, relationships | `"User prefers dark mode"` |
| **Episodic** | Timestamped experiences | `"[2025-01-15] Debugged JWT expiry issue"` |
| **Procedural** | Workflows, multi-step procedures | `"Deploy: 1. Test, 2. Build, 3. Push"` |

## Installation

### Prerequisites

- **Python 3.10+** - Required for the memory system
- **pipx** - Recommended for isolated package installation

```bash
# Install pipx if not already installed
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# Verify installation
pipx --version
```

### Option 1: MCP Server (Recommended)

This exposes memory operations as tools directly in Claude Code.

**Step 1: Install dependencies**

```bash
# Install MCP SDK (required)
pipx install mcp

# Install CogDB for graph backend (recommended)
pipx install cogdb
```

**Step 2: Clone or download the skill**

```bash
git clone https://github.com/btafoya/claude-code-skills.git
cd claude-code-skills/agent-memory-skill
```

**Step 3: Configure Claude Code**

Add to your Claude Code MCP config (`~/.config/claude-code/config.json`):

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

**Available MCP Tools:**
- `memory_add_fact` - Store semantic memories (facts about user/project)
- `memory_add_episode` - Record significant interactions with timestamps
- `memory_add_procedure` - Save reusable workflows with steps
- `memory_search` - Search memories by keyword
- `memory_get_context` - Build context from relevant memories
- `memory_stats` - Get memory statistics
- `memory_list_all` - List all stored memories
- `memory_delete` - Remove a memory by ID

**Step 4: Restart Claude Code**

After updating the config, restart Claude Code to load the MCP server.

**Step 5: Verify installation**

In Claude Code, run:
```
memory_stats
```

You should see output like: `Total: 0 | Semantic: 0 | Episodic: 0 | Procedural: 0 | Backend: graph`

### Option 2: Python Library

For direct Python integration in your own projects:

**Step 1: Install dependencies**

```bash
# Graph backend (recommended)
pipx install cogdb

# Or for zero-dependency fallback, skip cogdb
```

**Step 2: Add to your project**

```bash
# Copy the scripts directory to your project
cp -r agent-memory-skill/scripts your-project/

# Or add to Python path
export PYTHONPATH="${PYTHONPATH}:/path/to/agent-memory-skill"
```

**Step 3: Use in your code**

```python
from scripts.memory import MemoryStore

store = MemoryStore()  # Uses graph backend by default

# Add memories
store.add_fact("User prefers TypeScript over JavaScript")
store.add_episode("Helped debug authentication issue", topic="auth")
store.add_procedure("deploy", ["Run tests", "Build", "Push", "Deploy"])

# Search and retrieve
results = store.search("TypeScript")
context = store.build_context("authentication")  # For prompt injection

# Use JSON backend if CogDB not installed
store_json = MemoryStore(backend="json")
```

### Option 3: CLAUDE.md Injection

Export memories for manual inclusion in your project's `CLAUDE.md`:

```bash
cd /path/to/agent-memory-skill
python -c "from scripts.memory import get_store; print(get_store().export_for_prompt())"
```

## Storage Backends

The skill supports pluggable storage backends:

### Graph Backend (Default)

Relationship-aware storage using [CogDB](https://cogdb.io/) - enables entity relationships, graph traversal, and richer queries.

```bash
pipx install cogdb
```

```python
store = MemoryStore()  # Graph backend is default

# Add memories - entities are auto-extracted and linked
store.add_fact("User's colleague Mark is a data scientist")
store.add_fact("Mark works on the ML pipeline project")

# Graph-specific queries
related = store.find_related("Mark")  # Find all memories mentioning Mark
info = store.get_entity_info("Mark")  # Get entity graph with related entities
```

Storage: `~/.claude_memory/graph/`

### JSON Backend (Fallback)

Zero dependencies, flat-file JSON storage with thread-safe locking.

```python
store = MemoryStore(backend="json")
```

Storage: `~/.claude_memory/memories.json`

## Project Structure

```
agent-memory-skill/
├── README.md              # This file
├── SKILL.md               # Detailed skill documentation
├── requirements.txt       # Dependencies (optional)
├── scripts/
│   ├── __init__.py        # Package exports
│   ├── backends.py        # Storage backends (JSON, Graph)
│   ├── memory.py          # Core MemoryStore implementation
│   └── mcp_server.py      # MCP server for Claude Code
└── references/
    ├── memory-theory.md   # Cognitive science background
    └── storage-patterns.md # Storage architecture options
```

## Use Cases

- **Remember user preferences** across sessions
- **Track project context** and decisions made
- **Store workflows** for common operations (code review, deployment, etc.)
- **Build personalized agents** that learn from conversations
- **Maintain relationship context** with users over time

## Credits

This skill is based on concepts from the article ["How Does Memory for AI Agents Work?"](https://www.decodingai.com/p/how-does-memory-for-ai-agents-work) by Decoding AI, which provides an excellent overview of memory architectures for AI agents.

Additional references:
- Liu et al. (2023). "Lost in the Middle: How Language Models Use Long Contexts"
- [mem0](https://github.com/mem0ai/mem0) - Open-source memory layer for AI applications

## Troubleshooting

### MCP Server Issues

**"MCP not installed" error**
```bash
pipx install mcp
# Ensure pipx bin is in PATH
export PATH="$PATH:$HOME/.local/bin"
```

**"CogDB not installed" error**
```bash
pipx install cogdb
# Or use JSON fallback by modifying mcp_server.py to use backend="json"
```

**MCP server not appearing in Claude Code**
1. Verify the path in config.json is absolute and correct
2. Check that Python can import the mcp module: `python -c "import mcp"`
3. Restart Claude Code completely (not just reload)

### Python Library Issues

**ImportError when importing scripts**
```bash
# Ensure you're in the project directory or add to PYTHONPATH
cd /path/to/agent-memory-skill
python -c "from scripts import MemoryStore; print('OK')"
```

**Permission errors on ~/.claude_memory**
```bash
# Check directory permissions
ls -la ~/.claude_memory/
chmod 755 ~/.claude_memory/
chmod 644 ~/.claude_memory/memories.json 2>/dev/null
```

### Storage Issues

**Memories not persisting**
- Check write permissions to `~/.claude_memory/`
- For graph backend, ensure CogDB is properly installed
- Try JSON backend as fallback: `MemoryStore(backend="json")`

**Corrupted memory file**
```bash
# Backup and reset
mv ~/.claude_memory ~/.claude_memory.bak
# Memories will be recreated on next use
```

## License

MIT
