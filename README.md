# Claude Code Skills

A collection of skills for [Claude Code](https://claude.com/claude-code) that extend AI agent capabilities with persistent memory, specialized tools, and reusable workflows.

## Available Skills

| Skill | Description | Status |
|-------|-------------|--------|
| [agent-memory-skill](./agent-memory-skill/) | Persistent memory system with semantic, episodic, and procedural memory types | ✅ Ready |

## What are Skills?

Skills are modular components that give Claude Code additional capabilities beyond its built-in tools. They can:

- **Persist data** across sessions (memory, preferences, context)
- **Integrate with external services** via MCP servers
- **Provide specialized workflows** for common tasks
- **Enhance context** with domain-specific knowledge

## Quick Start

Each skill has its own installation instructions. Generally:

1. **Clone this repository**
   ```bash
   git clone https://github.com/btafoya/agent-memory-skills.git
   cd agent-memory-skills
   ```

2. **Choose a skill** and follow its README

3. **Configure Claude Code** (if using MCP server)
   ```json
   {
     "mcpServers": {
       "skill-name": {
         "command": "python",
         "args": ["/path/to/skill/mcp_server.py"]
       }
     }
   }
   ```

## Skill Structure

Each skill follows a consistent structure:

```
skill-name/
├── README.md          # Detailed documentation
├── SKILL.md           # Skill manifest and quick reference
├── scripts/           # Python implementation
│   ├── __init__.py
│   └── mcp_server.py  # MCP server (optional)
└── references/        # Background materials (optional)
```

## Contributing

To add a new skill:

1. Create a new directory with your skill name
2. Include a `README.md` with installation and usage instructions
3. Include a `SKILL.md` with the skill manifest
4. Add your skill to the table above
5. Submit a pull request

## Requirements

- Python 3.10+
- [pipx](https://pypa.github.io/pipx/) (recommended for package installation)
- [Claude Code](https://claude.com/claude-code) (for MCP integration)

## License

MIT
