"""
Agent Memory Scripts Package
Provides memory storage and MCP server functionality.

Supports two storage backends:
- GraphBackend (default): Relationship-aware storage via CogDB (pipx install cogdb)
- JSONBackend: Simple flat-file storage, zero dependencies (fallback)

Usage:
    from scripts import MemoryStore

    # Default Graph backend (recommended)
    store = MemoryStore()

    # JSON backend for zero-dependency fallback
    store = MemoryStore(backend="json")
"""

from .backends import (
    Memory,
    StorageBackend,
    JSONBackend,
    GraphBackend,
    get_backend,
    DEFAULT_MEMORY_DIR,
    SCHEMA_VERSION,
)

from .memory import (
    MemoryStore,
    get_store,
    remember,
    recall,
    MEMORY_DIR,
    MEMORY_FILE,
)

__all__ = [
    # Core
    "Memory",
    "MemoryStore",
    "get_store",
    "remember",
    "recall",
    # Backends
    "StorageBackend",
    "JSONBackend",
    "GraphBackend",
    "get_backend",
    # Constants
    "MEMORY_DIR",
    "MEMORY_FILE",
    "DEFAULT_MEMORY_DIR",
    "SCHEMA_VERSION",
]
