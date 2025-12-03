#!/usr/bin/env python3
"""
Storage Backends for Agent Memory

Provides pluggable storage implementations:
- GraphBackend: Graph database with relationships via CogDB (default, recommended)
- JSONBackend: Simple flat-file JSON storage (fallback, zero dependencies)

Usage:
    from backends import JSONBackend, GraphBackend

    # Graph storage with relationships (default, requires: pipx install cogdb)
    backend = GraphBackend()

    # Simple JSON storage (fallback, zero dependencies)
    backend = JSONBackend()
"""

import json
import fcntl
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Literal, Protocol, runtime_checkable
from dataclasses import dataclass, asdict, field
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

# Default storage locations
DEFAULT_MEMORY_DIR = Path.home() / ".claude_memory"

# Schema version for storage format compatibility
SCHEMA_VERSION = "1.0"


@dataclass
class Memory:
    """Single memory unit - shared across all backends."""
    id: str
    content: str
    category: Literal["semantic", "episodic", "procedural"]
    created_at: str
    updated_at: str
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Memory":
        return cls(**data)


@runtime_checkable
class StorageBackend(Protocol):
    """Protocol for memory storage backends."""

    def save(self, memories: list[Memory]) -> None:
        """Persist all memories to storage."""
        ...

    def load(self) -> list[Memory]:
        """Load all memories from storage."""
        ...

    def add(self, memory: Memory) -> None:
        """Add a single memory."""
        ...

    def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID. Returns True if found and deleted."""
        ...

    def search(self, query: str, category: Optional[str] = None, limit: int = 5) -> list[Memory]:
        """Search memories by keyword."""
        ...

    def get_by_category(self, category: str) -> list[Memory]:
        """Get all memories of a specific category."""
        ...

    def get_all(self, offset: int = 0, limit: Optional[int] = None) -> list[Memory]:
        """Get all memories with optional pagination."""
        ...


class JSONBackend:
    """
    Simple JSON file storage backend.

    Features:
    - Zero dependencies
    - Thread-safe with file locking
    - Human-readable storage format
    - Schema versioning for backward compatibility

    Storage: ~/.claude_memory/memories.json

    Storage Format (v1.0):
        {
            "schema_version": "1.0",
            "memories": [...]
        }
    """

    def __init__(self, memory_dir: Path = DEFAULT_MEMORY_DIR):
        self.memory_dir = memory_dir
        self.memory_file = memory_dir / "memories.json"
        self._ensure_storage()
        self._memories: list[Memory] = []
        self._load_cache()

    def _ensure_storage(self):
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        if not self.memory_file.exists():
            # Initialize with versioned schema
            initial_data = {"schema_version": SCHEMA_VERSION, "memories": []}
            self.memory_file.write_text(json.dumps(initial_data, indent=2))

    def _load_cache(self):
        """Load memories into internal cache."""
        self._memories = self.load()

    def load(self) -> list[Memory]:
        """Load all memories from JSON file with shared lock."""
        try:
            with open(self.memory_file, 'r') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    data = json.load(f)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            # Handle versioned format (v1.0+)
            if isinstance(data, dict) and "schema_version" in data:
                version = data.get("schema_version", "1.0")
                memories_data = data.get("memories", [])
                logger.debug(f"Loading memories with schema version {version}")
                return [Memory.from_dict(m) for m in memories_data]

            # Handle legacy format (plain list) - auto-migrate
            if isinstance(data, list):
                logger.info("Migrating legacy memory format to v1.0")
                memories = [Memory.from_dict(m) for m in data]
                self._memories = memories
                self.save(memories)  # Save in new format
                return memories

            logger.warning(f"Unknown memory file format")
            return []

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse memories file: {e}")
            return []
        except FileNotFoundError:
            return []
        except OSError as e:
            logger.warning(f"Failed to load memories: {e}")
            return []

    def save(self, memories: list[Memory]) -> None:
        """Save all memories to JSON file with exclusive lock."""
        self._memories = memories
        data = {
            "schema_version": SCHEMA_VERSION,
            "memories": [m.to_dict() for m in memories]
        }
        with open(self.memory_file, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(data, f, indent=2)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def add(self, memory: Memory) -> None:
        """Add a memory and persist."""
        self._memories.append(memory)
        self.save(self._memories)

    def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        for i, memory in enumerate(self._memories):
            if memory.id == memory_id:
                del self._memories[i]
                self.save(self._memories)
                return True
        return False

    def search(self, query: str, category: Optional[str] = None, limit: int = 5) -> list[Memory]:
        """Keyword search through memories."""
        query_lower = query.lower()
        results = []
        for memory in self._memories:
            if category and memory.category != category:
                continue
            if query_lower in memory.content.lower():
                results.append(memory)
        return results[:limit]

    def get_by_category(self, category: str) -> list[Memory]:
        """Get all memories of a specific category."""
        return [m for m in self._memories if m.category == category]

    def get_all(self, offset: int = 0, limit: Optional[int] = None) -> list[Memory]:
        """
        Get all memories with optional pagination.

        Args:
            offset: Number of memories to skip (default: 0)
            limit: Maximum number of memories to return (default: None = all)

        Returns:
            List of Memory objects, paginated if offset/limit specified.
        """
        memories = self._memories[offset:]
        if limit is not None:
            memories = memories[:limit]
        return memories.copy()


class GraphBackend:
    """
    Graph database storage backend using CogDB.

    Features:
    - Relationship modeling between entities
    - Graph traversal queries
    - Entity extraction from memories
    - Flat-file persistence (no server required)

    Requires: pip install cogdb
    Storage: ~/.claude_memory/graph/

    Graph Structure:
    - Memories stored as nodes with properties
    - Entities extracted and linked: (Memory)-[MENTIONS]->(Entity)
    - Categories as relationships: (Memory)-[IS_A]->(Category)
    - Temporal edges for episodic: (Memory)-[OCCURRED_ON]->(Date)
    """

    def __init__(self, memory_dir: Path = DEFAULT_MEMORY_DIR):
        self.memory_dir = memory_dir
        self.graph_dir = memory_dir / "graph"
        self._graph = None
        self._memories_cache: dict[str, Memory] = {}
        self._init_graph()

    def _init_graph(self):
        """Initialize CogDB graph."""
        try:
            from cog.torque import Graph
            from cog import config

            # Configure CogDB storage location
            self.graph_dir.mkdir(parents=True, exist_ok=True)
            config.COG_HOME = str(self.graph_dir)
            config.COG_PATH_PREFIX = str(self.graph_dir)

            self._graph = Graph("agent_memory")
            self._load_cache()
            logger.info(f"GraphBackend initialized at {self.graph_dir}")
        except ImportError:
            raise ImportError(
                "CogDB not installed. Install with: pipx install cogdb\n"
                "Or use JSONBackend for zero-dependency storage."
            )

    def _load_cache(self):
        """Load memory objects from graph into cache."""
        if not self._graph:
            return

        # Query all memory nodes
        try:
            results = self._graph.v().has("type", "memory").all()
            for node in results:
                if isinstance(node, dict) and "id" in node:
                    memory = Memory(
                        id=node.get("id", ""),
                        content=node.get("content", ""),
                        category=node.get("category", "semantic"),
                        created_at=node.get("created_at", ""),
                        updated_at=node.get("updated_at", ""),
                        metadata=json.loads(node.get("metadata", "{}"))
                    )
                    self._memories_cache[memory.id] = memory
        except (KeyError, TypeError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to load memories from graph: {e}")

    def _generate_id(self, content: str) -> str:
        """Generate unique ID for a memory."""
        timestamp = datetime.now().isoformat()
        return hashlib.sha256(f"{content}{timestamp}".encode()).hexdigest()[:12]

    def _extract_entities(self, content: str) -> list[str]:
        """
        Extract entities from content for graph linking.

        This is a basic regex-based implementation suitable for simple use cases.
        It extracts:
        - Quoted strings (e.g., "Python" from 'User prefers "Python"')
        - Capitalized words likely to be proper nouns (e.g., Mark, PostgreSQL)

        For production use with complex entity recognition, consider:
        - spaCy NER: `pip install spacy` with a trained model
        - Hugging Face transformers for named entity recognition
        - Custom domain-specific entity patterns

        Returns:
            List of unique entity strings extracted from content.
        """
        import re

        entities = []

        # Find quoted strings
        quoted = re.findall(r'"([^"]+)"', content)
        entities.extend(quoted)

        # Find capitalized words (potential proper nouns)
        words = content.split()
        for word in words:
            clean = word.strip('.,!?:;()[]{}')
            if clean and clean[0].isupper() and len(clean) > 1:
                # Skip common sentence starters
                if clean.lower() not in ['the', 'a', 'an', 'this', 'that', 'user', 'i']:
                    entities.append(clean)

        return list(set(entities))

    def add(self, memory: Memory) -> None:
        """Add a memory to the graph with entity relationships."""
        if not self._graph:
            return

        # Store memory as a node with properties
        memory_node = f"memory:{memory.id}"

        # Add memory properties as triples
        self._graph.put(memory_node, "type", "memory")
        self._graph.put(memory_node, "id", memory.id)
        self._graph.put(memory_node, "content", memory.content)
        self._graph.put(memory_node, "category", memory.category)
        self._graph.put(memory_node, "created_at", memory.created_at)
        self._graph.put(memory_node, "updated_at", memory.updated_at)
        self._graph.put(memory_node, "metadata", json.dumps(memory.metadata))

        # Link to category node
        self._graph.put(memory_node, "IS_A", f"category:{memory.category}")

        # Extract and link entities
        entities = self._extract_entities(memory.content)
        for entity in entities:
            entity_node = f"entity:{entity.lower()}"
            self._graph.put(entity_node, "type", "entity")
            self._graph.put(entity_node, "name", entity)
            self._graph.put(memory_node, "MENTIONS", entity_node)

        # For episodic memories, add temporal link
        if memory.category == "episodic":
            date = memory.created_at[:10]  # YYYY-MM-DD
            self._graph.put(memory_node, "OCCURRED_ON", f"date:{date}")

        # For procedural memories, extract steps
        if memory.category == "procedural" and "steps" in memory.metadata:
            for i, step in enumerate(memory.metadata["steps"]):
                step_node = f"step:{memory.id}:{i}"
                self._graph.put(step_node, "type", "step")
                self._graph.put(step_node, "content", step)
                self._graph.put(step_node, "order", str(i))
                self._graph.put(memory_node, "HAS_STEP", step_node)

        # Update cache
        self._memories_cache[memory.id] = memory

    def save(self, memories: list[Memory]) -> None:
        """Save all memories (rebuilds graph)."""
        # Clear and rebuild
        self._memories_cache.clear()
        # Note: CogDB doesn't have a clear() method, so we add/update
        for memory in memories:
            self.add(memory)

    def load(self) -> list[Memory]:
        """Load all memories from graph."""
        return list(self._memories_cache.values())

    def delete(self, memory_id: str) -> bool:
        """Delete a memory from the graph."""
        if memory_id not in self._memories_cache:
            return False

        if self._graph:
            memory_node = f"memory:{memory_id}"
            # Drop all edges from this memory
            # Note: CogDB's drop removes specific triples
            try:
                # Get all predicates for this memory and drop them
                # This is a simplified approach
                self._graph.drop(memory_node, "type", "memory")
                self._graph.drop(memory_node, "IS_A", f"category:{self._memories_cache[memory_id].category}")
            except (KeyError, AttributeError, RuntimeError) as e:
                logger.warning(f"Error dropping memory edges: {e}")

        del self._memories_cache[memory_id]
        return True

    def search(self, query: str, category: Optional[str] = None, limit: int = 5) -> list[Memory]:
        """
        Search memories using graph traversal.

        Enhanced search: also finds memories mentioning entities that match the query.
        """
        results = []
        query_lower = query.lower()

        # Direct content search
        for memory in self._memories_cache.values():
            if category and memory.category != category:
                continue
            if query_lower in memory.content.lower():
                results.append(memory)

        # Entity-based search via graph
        if self._graph and len(results) < limit:
            try:
                # Find entities matching query
                entity_node = f"entity:{query_lower}"
                # Find memories mentioning this entity
                mentioning = self._graph.v(entity_node).inc("MENTIONS").all()
                for node in mentioning:
                    if isinstance(node, str) and node.startswith("memory:"):
                        mem_id = node.replace("memory:", "")
                        if mem_id in self._memories_cache:
                            memory = self._memories_cache[mem_id]
                            if memory not in results:
                                if not category or memory.category == category:
                                    results.append(memory)
            except (KeyError, AttributeError, TypeError) as e:
                logger.debug(f"Graph search fallback: {e}")

        return results[:limit]

    def get_by_category(self, category: str) -> list[Memory]:
        """Get all memories of a specific category via graph traversal."""
        return [m for m in self._memories_cache.values() if m.category == category]

    def get_all(self, offset: int = 0, limit: Optional[int] = None) -> list[Memory]:
        """
        Get all memories with optional pagination.

        Args:
            offset: Number of memories to skip (default: 0)
            limit: Maximum number of memories to return (default: None = all)

        Returns:
            List of Memory objects, paginated if offset/limit specified.
        """
        memories = list(self._memories_cache.values())[offset:]
        if limit is not None:
            memories = memories[:limit]
        return memories

    # === Graph-specific methods ===

    def find_related(self, query: str, depth: int = 2) -> list[Memory]:
        """
        Find memories related to a query through entity relationships.

        This is the key advantage of graph storage - relationship traversal.
        """
        if not self._graph:
            return self.search(query)

        related_ids = set()
        query_lower = query.lower()

        try:
            # Start from entity matching query
            entity_node = f"entity:{query_lower}"

            # Find all memories mentioning this entity
            direct = self._graph.v(entity_node).inc("MENTIONS").all()
            for node in direct:
                if isinstance(node, str) and node.startswith("memory:"):
                    related_ids.add(node.replace("memory:", ""))

            # If depth > 1, find entities mentioned by those memories,
            # then find other memories mentioning those entities
            if depth > 1:
                for mem_id in list(related_ids):
                    mem_node = f"memory:{mem_id}"
                    # Get entities this memory mentions
                    entities = self._graph.v(mem_node).out("MENTIONS").all()
                    for ent in entities:
                        if isinstance(ent, str) and ent.startswith("entity:"):
                            # Find other memories mentioning this entity
                            others = self._graph.v(ent).inc("MENTIONS").all()
                            for other in others:
                                if isinstance(other, str) and other.startswith("memory:"):
                                    related_ids.add(other.replace("memory:", ""))
        except (KeyError, AttributeError, TypeError) as e:
            logger.debug(f"Relationship traversal error: {e}")

        # Return memories for found IDs
        return [self._memories_cache[mid] for mid in related_ids if mid in self._memories_cache]

    def get_entity_graph(self, entity: str) -> dict:
        """
        Get all information about an entity from the graph.

        Returns a dict with:
        - memories: list of memories mentioning this entity
        - related_entities: other entities co-mentioned with this one
        """
        if not self._graph:
            return {"memories": [], "related_entities": []}

        result = {"memories": [], "related_entities": set()}
        entity_node = f"entity:{entity.lower()}"

        try:
            # Get memories mentioning this entity
            mentioning = self._graph.v(entity_node).inc("MENTIONS").all()
            for node in mentioning:
                if isinstance(node, str) and node.startswith("memory:"):
                    mem_id = node.replace("memory:", "")
                    if mem_id in self._memories_cache:
                        result["memories"].append(self._memories_cache[mem_id])

                        # Get other entities in these memories
                        mem_node = f"memory:{mem_id}"
                        entities = self._graph.v(mem_node).out("MENTIONS").all()
                        for ent in entities:
                            if isinstance(ent, str) and ent.startswith("entity:"):
                                ent_name = ent.replace("entity:", "")
                                if ent_name != entity.lower():
                                    result["related_entities"].add(ent_name)
        except (KeyError, AttributeError, TypeError) as e:
            logger.debug(f"Entity graph error: {e}")

        result["related_entities"] = list(result["related_entities"])
        return result


def get_backend(backend_type: str = "json", **kwargs) -> StorageBackend:
    """
    Factory function to get a storage backend.

    Args:
        backend_type: "json" or "graph"
        **kwargs: Passed to backend constructor

    Returns:
        StorageBackend instance
    """
    if backend_type == "json":
        return JSONBackend(**kwargs)
    elif backend_type == "graph":
        return GraphBackend(**kwargs)
    else:
        raise ValueError(f"Unknown backend type: {backend_type}. Use 'json' or 'graph'.")
