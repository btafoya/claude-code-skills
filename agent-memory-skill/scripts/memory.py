#!/usr/bin/env python3
"""
Agent Memory System
Persistent memory with semantic, episodic, and procedural memory types.

Supports pluggable storage backends:
- Graph (default): Relationship-aware storage via CogDB (pipx install cogdb)
- JSON: Simple flat-file storage, zero dependencies (fallback)

Usage:
    # Default Graph backend (recommended)
    store = MemoryStore()

    # JSON backend for zero-dependency fallback
    store = MemoryStore(backend="json")
"""

import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal, Union

from .backends import (
    Memory,
    StorageBackend,
    JSONBackend,
    GraphBackend,
    get_backend,
    DEFAULT_MEMORY_DIR,
)

# Re-export Memory for backward compatibility
__all__ = ["Memory", "MemoryStore", "get_store", "remember", "recall"]

logger = logging.getLogger(__name__)

MEMORY_DIR = DEFAULT_MEMORY_DIR
MEMORY_FILE = MEMORY_DIR / "memories.json"


class MemoryStore:
    """
    Long-term memory with three types:
    - Semantic: Facts & knowledge
    - Episodic: Timestamped experiences
    - Procedural: Workflows & skills

    Args:
        memory_dir: Directory for storage (default: ~/.claude_memory)
        backend: Storage backend - "graph" (default) or "json"

    The graph backend enables relationship queries:
        store = MemoryStore()  # Uses graph by default
        related = store.find_related("Python")  # Find memories connected to Python
    """

    def __init__(
        self,
        memory_dir: Path = MEMORY_DIR,
        backend: Union[str, StorageBackend] = "graph"
    ):
        self.memory_dir = memory_dir

        # Initialize backend
        if isinstance(backend, str):
            self._backend = get_backend(backend, memory_dir=memory_dir)
        else:
            self._backend = backend

        self._is_graph = isinstance(self._backend, GraphBackend)

    @property
    def memories(self) -> list[Memory]:
        """Get all memories from backend."""
        return self._backend.get_all()

    def get_memories(self, offset: int = 0, limit: Optional[int] = None) -> list[Memory]:
        """
        Get memories with optional pagination.

        Args:
            offset: Number of memories to skip (default: 0)
            limit: Maximum number of memories to return (default: None = all)

        Returns:
            List of Memory objects, paginated if offset/limit specified.

        Example:
            # Get first 10 memories
            store.get_memories(limit=10)

            # Get next 10 memories
            store.get_memories(offset=10, limit=10)
        """
        return self._backend.get_all(offset=offset, limit=limit)

    def _generate_id(self, content: str) -> str:
        timestamp = datetime.now().isoformat()
        return hashlib.sha256(f"{content}{timestamp}".encode()).hexdigest()[:12]

    # === SEMANTIC MEMORY (Facts) ===

    def add_fact(self, fact: str, **metadata) -> Memory:
        """Add a fact. Example: store.add_fact("User prefers dark mode")"""
        now = datetime.now().isoformat()
        memory = Memory(
            id=self._generate_id(fact),
            content=fact,
            category="semantic",
            created_at=now,
            updated_at=now,
            metadata=metadata
        )
        self._backend.add(memory)
        return memory

    def update_fact(self, old_content: str, new_content: str) -> Optional[Memory]:
        """Update an existing fact (handles contradictions)."""
        for memory in self.memories:
            if memory.category == "semantic" and memory.content == old_content:
                memory.content = new_content
                memory.updated_at = datetime.now().isoformat()
                self._backend.save(self.memories)
                return memory
        return None

    # === EPISODIC MEMORY (Experiences) ===

    def add_episode(self, summary: str, **metadata) -> Memory:
        """Add a timestamped experience."""
        now = datetime.now().isoformat()
        memory = Memory(
            id=self._generate_id(summary),
            content=summary,
            category="episodic",
            created_at=now,
            updated_at=now,
            metadata={"timestamp": now, **metadata}
        )
        self._backend.add(memory)
        return memory

    # === PROCEDURAL MEMORY (Workflows) ===

    def add_procedure(self, name: str, steps: list[str], **metadata) -> Memory:
        """Add a workflow. Example: store.add_procedure("deploy", ["test", "build", "push"])"""
        now = datetime.now().isoformat()
        content = f"Procedure: {name}\nSteps:\n" + "\n".join(
            f"{i+1}. {step}" for i, step in enumerate(steps)
        )
        memory = Memory(
            id=self._generate_id(name),
            content=content,
            category="procedural",
            created_at=now,
            updated_at=now,
            metadata={"procedure_name": name, "steps": steps, **metadata}
        )
        self._backend.add(memory)
        return memory

    # === RETRIEVAL ===

    def search(
        self,
        query: str,
        category: Optional[Literal["semantic", "episodic", "procedural"]] = None,
        limit: int = 5
    ) -> list[Memory]:
        """Keyword search through memories."""
        return self._backend.search(query, category=category, limit=limit)

    def get_by_category(self, category: str) -> list[Memory]:
        return self._backend.get_by_category(category)

    def get_recent_episodes(self, limit: int = 10) -> list[Memory]:
        episodes = self.get_by_category("episodic")
        return sorted(episodes, key=lambda m: m.created_at, reverse=True)[:limit]

    def get_procedure(self, name: str) -> Optional[Memory]:
        for memory in self.memories:
            if memory.category == "procedural" and memory.metadata.get("procedure_name") == name:
                return memory
        return None

    # === GRAPH-SPECIFIC METHODS ===

    def find_related(self, query: str, depth: int = 2) -> list[Memory]:
        """
        Find memories related through entity relationships.
        Only available with graph backend; falls back to search() for JSON.

        Args:
            query: Entity or keyword to find relationships for
            depth: How many relationship hops to traverse (1-3)

        Returns:
            List of related memories
        """
        if self._is_graph:
            return self._backend.find_related(query, depth=depth)
        return self.search(query)

    def get_entity_info(self, entity: str) -> dict:
        """
        Get all information about an entity from the knowledge graph.
        Only available with graph backend.

        Args:
            entity: Name of the entity (e.g., "Python", "Mark")

        Returns:
            Dict with 'memories' and 'related_entities' keys
        """
        if self._is_graph:
            return self._backend.get_entity_graph(entity)
        # Fallback for JSON backend
        memories = self.search(entity, limit=20)
        return {"memories": memories, "related_entities": []}

    # === CONTEXT ENGINEERING ===

    def build_context(
        self,
        query: str = "",
        max_facts: int = 10,
        max_episodes: int = 5,
        include_procedures: bool = True,
        use_relationships: bool = True
    ) -> str:
        """
        Build context string for LLM prompt injection.

        Args:
            query: Optional query to focus context on
            max_facts: Maximum semantic memories to include
            max_episodes: Maximum episodic memories to include
            include_procedures: Whether to include procedural memories
            use_relationships: Use graph relationships if available (graph backend only)
        """
        sections = []

        # Semantic memories
        if query and use_relationships and self._is_graph:
            # Use relationship-aware search for graph backend
            facts = self.find_related(query, depth=1)
            facts = [m for m in facts if m.category == "semantic"][:max_facts]
        elif query:
            facts = self.search(query, category="semantic", limit=max_facts)
        else:
            facts = self.get_by_category("semantic")[:max_facts]

        if facts:
            fact_text = "\n".join(f"- {m.content}" for m in facts)
            sections.append(f"## Known Facts\n{fact_text}")

        # Episodic memories
        episodes = self.get_recent_episodes(max_episodes)
        if episodes:
            episode_text = "\n".join(
                f"- [{m.created_at[:10]}] {m.content}" for m in episodes
            )
            sections.append(f"## Recent History\n{episode_text}")

        # Procedural memories
        if include_procedures:
            if query:
                procedures = self.search(query, category="procedural", limit=3)
            else:
                procedures = self.get_by_category("procedural")[:3]
            if procedures:
                proc_text = "\n\n".join(m.content for m in procedures)
                sections.append(f"## Available Procedures\n{proc_text}")

        return "\n\n".join(sections) if sections else ""

    # === UTILITY ===

    def delete(self, memory_id: str) -> bool:
        return self._backend.delete(memory_id)

    def clear_all(self):
        self._backend.save([])

    def export_for_prompt(self) -> str:
        """Export all memories for system prompt."""
        return self.build_context("", max_facts=50, max_episodes=20)

    def stats(self) -> dict:
        stats = {
            "total": len(self.memories),
            "semantic": len(self.get_by_category("semantic")),
            "episodic": len(self.get_by_category("episodic")),
            "procedural": len(self.get_by_category("procedural")),
            "backend": "graph" if self._is_graph else "json",
        }
        return stats


# Convenience functions
_store: Optional[MemoryStore] = None
_store_backend: str = "graph"


def get_store(backend: str = "graph") -> MemoryStore:
    """
    Get or create the global MemoryStore instance.

    Args:
        backend: "graph" (default) or "json"
    """
    global _store, _store_backend
    if _store is None or _store_backend != backend:
        _store = MemoryStore(backend=backend)
        _store_backend = backend
    return _store


def remember(content: str, category: Literal["semantic", "episodic"] = "semantic", **metadata) -> Memory:
    """
    Add a memory to the store.

    Args:
        content: The memory content to store
        category: Either "semantic" (facts) or "episodic" (experiences)
        **metadata: Additional metadata to attach to the memory

    Returns:
        The created Memory object

    Raises:
        ValueError: If category is "procedural" (use add_procedure() instead)
    """
    store = get_store()
    if category == "semantic":
        return store.add_fact(content, **metadata)
    elif category == "episodic":
        return store.add_episode(content, **metadata)
    raise ValueError("Use add_procedure() for procedural memories")


def recall(query: str, category: Optional[str] = None, limit: int = 5) -> list[Memory]:
    return get_store().search(query, category=category, limit=limit)


if __name__ == "__main__":
    import sys

    # Check for --json flag to use fallback
    use_json = "--json" in sys.argv

    if use_json:
        print("Using JSON backend (fallback)")
        store = MemoryStore(backend="json")
    else:
        print("Using GRAPH backend (default)")
        try:
            store = MemoryStore(backend="graph")
        except ImportError as e:
            print(f"CogDB not installed: {e}")
            print("Falling back to JSON backend...")
            store = MemoryStore(backend="json")

    print("\nAdding memories...")
    store.add_fact("User prefers Python")
    store.add_fact("User uses pytest for testing")
    store.add_fact("User's colleague Mark is a data scientist")
    store.add_episode("Helped debug authentication flow")
    store.add_procedure("review", ["Check types", "Review errors", "Verify tests"])

    print(f"\nStats: {store.stats()}")
    print(f"\nSearch 'Python': {[m.content for m in store.search('Python')]}")

    if not use_json:
        print(f"\nFind related to 'Mark': {[m.content for m in store.find_related('Mark')]}")
        print(f"\nEntity info for 'Python': {store.get_entity_info('Python')}")

    print(f"\nContext:\n{store.build_context('testing')}")
