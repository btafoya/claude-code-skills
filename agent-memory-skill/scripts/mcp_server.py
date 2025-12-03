#!/usr/bin/env python3
"""
MCP Server for Agent Memory
Exposes memory operations as tools for Claude Code.

Setup:
1. Install dependencies with pipx:
   pipx install mcp
   pipx install cogdb  # For graph backend (default)

2. Add to Claude Code MCP config (~/.config/claude-code/config.json):
   {
     "mcpServers": {
       "memory": {
         "command": "python",
         "args": ["/path/to/agent-memory-skill/scripts/mcp_server.py"]
       }
     }
   }
"""

import sys
import asyncio
from pathlib import Path
from functools import partial

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


async def run_sync(func, *args, **kwargs):
    """Run a synchronous function in a thread pool to avoid blocking."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(func, *args, **kwargs))

# Import from package when installed, or from local file when run directly
try:
    from .memory import MemoryStore
except ImportError:
    # Running as script directly - add parent to path
    sys.path.insert(0, str(Path(__file__).parent))
    from memory import MemoryStore


def create_server():
    server = Server("agent-memory")
    store = MemoryStore()
    
    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="memory_add_fact",
                description="Add a semantic memory (fact about user or project)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "fact": {"type": "string", "description": "The fact to remember"},
                        "tags": {"type": "string", "description": "Optional comma-separated tags"}
                    },
                    "required": ["fact"]
                }
            ),
            Tool(
                name="memory_add_episode",
                description="Add an episodic memory (record of significant interaction)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string", "description": "Summary of what happened"},
                        "topic": {"type": "string", "description": "Topic/category"}
                    },
                    "required": ["summary"]
                }
            ),
            Tool(
                name="memory_add_procedure",
                description="Add a procedural memory (workflow with steps)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Procedure name"},
                        "steps": {"type": "array", "items": {"type": "string"}, "description": "Steps"},
                        "trigger": {"type": "string", "description": "When to use"}
                    },
                    "required": ["name", "steps"]
                }
            ),
            Tool(
                name="memory_search",
                description="Search memories by keyword",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "category": {"type": "string", "enum": ["semantic", "episodic", "procedural"]},
                        "limit": {"type": "integer", "description": "Max results"}
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="memory_get_context",
                description="Build context from relevant memories for a topic",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "Topic to build context for"}
                    },
                    "required": ["topic"]
                }
            ),
            Tool(
                name="memory_stats",
                description="Get memory statistics",
                inputSchema={"type": "object", "properties": {}}
            ),
            Tool(
                name="memory_list_all",
                description="List all memories",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "enum": ["semantic", "episodic", "procedural"]}
                    }
                }
            ),
            Tool(
                name="memory_delete",
                description="Delete a memory by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "memory_id": {"type": "string", "description": "Memory ID to delete"}
                    },
                    "required": ["memory_id"]
                }
            )
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        # Use run_sync for I/O operations to prevent blocking the event loop
        if name == "memory_add_fact":
            meta = {"tags": arguments["tags"].split(",")} if arguments.get("tags") else {}
            mem = await run_sync(store.add_fact, arguments["fact"], **meta)
            return [TextContent(type="text", text=f"✓ Saved fact (ID: {mem.id})")]

        elif name == "memory_add_episode":
            meta = {"topic": arguments["topic"]} if arguments.get("topic") else {}
            mem = await run_sync(store.add_episode, arguments["summary"], **meta)
            return [TextContent(type="text", text=f"✓ Saved episode (ID: {mem.id})")]

        elif name == "memory_add_procedure":
            meta = {"trigger": arguments["trigger"]} if arguments.get("trigger") else {}
            mem = await run_sync(store.add_procedure, arguments["name"], arguments["steps"], **meta)
            return [TextContent(type="text", text=f"✓ Saved procedure '{arguments['name']}'")]

        elif name == "memory_search":
            results = await run_sync(
                store.search,
                arguments["query"],
                category=arguments.get("category"),
                limit=arguments.get("limit", 5)
            )
            if not results:
                return [TextContent(type="text", text="No memories found")]
            output = f"Found {len(results)} memories:\n\n"
            for mem in results:
                output += f"[{mem.category}] {mem.content}\n  ID: {mem.id}\n\n"
            return [TextContent(type="text", text=output)]

        elif name == "memory_get_context":
            context = await run_sync(store.build_context, arguments["topic"])
            return [TextContent(type="text", text=context or "No relevant memories")]

        elif name == "memory_stats":
            stats = await run_sync(store.stats)
            return [TextContent(type="text", text=f"Total: {stats['total']} | Semantic: {stats['semantic']} | Episodic: {stats['episodic']} | Procedural: {stats['procedural']} | Backend: {stats['backend']}")]

        elif name == "memory_list_all":
            if arguments.get("category"):
                memories = await run_sync(store.get_by_category, arguments["category"])
            else:
                memories = await run_sync(lambda: store.memories)
            if not memories:
                return [TextContent(type="text", text="No memories")]
            output = f"{len(memories)} memories:\n\n"
            for mem in memories:
                output += f"[{mem.category}] {mem.content[:80]}...\n  ID: {mem.id}\n\n"
            return [TextContent(type="text", text=output)]

        elif name == "memory_delete":
            success = await run_sync(store.delete, arguments["memory_id"])
            return [TextContent(type="text", text=f"✓ Deleted" if success else "✗ Not found")]

        return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    return server


async def main():
    if not MCP_AVAILABLE:
        print("MCP not installed. Run: pipx install mcp", file=sys.stderr)
        sys.exit(1)
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
