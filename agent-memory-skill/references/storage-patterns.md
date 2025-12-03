# Storage Patterns for Agent Memory

## Overview

How memories are stored is an architectural decision impacting performance, complexity, and scalability. Three primary methods:

1. Raw Strings
2. Structured Entities (JSON)
3. Knowledge Graphs

## 1. Raw Strings

Store conversations or documents as plain text, indexed for vector search.

**Pros:**
- Simple, fast setup
- Minimal engineering
- Preserves nuance, tone, linguistic cues

**Cons:**
- Imprecise retrieval (query "brother's job" returns all "brother" mentions)
- Hard to update (new facts add to log, creating contradictions)
- No structure (can't distinguish state changes: "Barry was CEO" vs "Claude is CEO")

**Best for:** Quick prototypes, preserving exact phrasing

## 2. Structured Entities (JSON)

Use LLM to transform interactions into structured memories in JSON/SQL.

**Example:**
```json
{
  "user": {
    "name": "Alex",
    "preferences": {
      "diet": "vegetarian",
      "theme": "dark"
    },
    "family": {
      "brother": {
        "name": "Mark",
        "job": "Software Engineer"
      }
    }
  }
}
```

**Pros:**
- Precise, field-level filtering
- Unambiguous retrieval
- Easy updates (overwrite relevant field)
- Ideal for semantic memory (profiles, preferences)

**Cons:**
- Requires upfront schema design
- Can be rigid (data that doesn't fit schema may be lost)

**Best for:** User profiles, preferences, structured facts

## 3. Knowledge Graphs

Store as network of nodes (entities) and edges (relationships).

**Example:**
```
(User) --[HAS_BROTHER]--> (Mark)
(Mark) --[WORKS_AS]--> (Software Engineer)
(Mark) --[CHANGED_JOB date="2025-01"]--> (Doctor)
```

**Pros:**
- Excels at complex relationships
- Superior contextual and temporal awareness
- Auditable retrieval (trace reasoning path)
- Builds trust through explainability

**Cons:**
- Highest complexity and cost
- Converting text to graph triples is difficult
- Graph traversals can be slower than vector lookups
- Often overkill for simple use cases

**Best for:** Complex relationship modeling, temporal tracking, audit requirements

## Choosing a Storage Strategy

| Factor | Strings | Entities | Graph |
|--------|---------|----------|-------|
| Setup complexity | Low | Medium | High |
| Query precision | Low | High | High |
| Update handling | Poor | Good | Excellent |
| Relationship modeling | Poor | Fair | Excellent |
| Temporal awareness | Poor | Fair | Excellent |
| Scalability | Good | Good | Variable |

**Decision guide:**
1. **Start with strings** for prototypes
2. **Move to entities** when you need precise retrieval or updates
3. **Add graphs** when relationships become complex

## Vector Databases

Vector DBs (Pinecone, Weaviate, pgvector) are typically document stores with vector indexes. They fall into "strings" or "entities" categories structurally.

**Recommended stack:**
- **Embeddings:** OpenAI text-embedding-3-small, sentence-transformers
- **Vector store:** pgvector (PostgreSQL), FAISS (local), Pinecone (managed)
- **Hybrid:** Combine vector search with structured filters

## Implementation Example: Upgrading to Embeddings

Replace keyword search with semantic similarity:

```python
from sentence_transformers import SentenceTransformer
import numpy as np

class VectorMemoryStore(MemoryStore):
    def __init__(self):
        super().__init__()
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embeddings = {}
    
    def add_fact(self, fact: str, **metadata):
        memory = super().add_fact(fact, **metadata)
        self.embeddings[memory.id] = self.model.encode(fact)
        return memory
    
    def search(self, query: str, limit: int = 5) -> list:
        query_embedding = self.model.encode(query)
        
        scores = []
        for memory in self.memories:
            if memory.id in self.embeddings:
                similarity = np.dot(query_embedding, self.embeddings[memory.id])
                scores.append((similarity, memory))
        
        scores.sort(reverse=True, key=lambda x: x[0])
        return [m for _, m in scores[:limit]]
```

## mem0 Library

Open-source memory layer with built-in entity extraction and graph storage.

```python
from mem0 import Memory

m = Memory()
m.add("User prefers vegetarian meals", user_id="alex")
m.add("User's brother Mark is a software engineer", user_id="alex")

results = m.search("brother's job", user_id="alex")
```

Features:
- Automatic entity extraction
- Hybrid vector + graph storage
- Built-in user/session isolation
- https://github.com/mem0ai/mem0
