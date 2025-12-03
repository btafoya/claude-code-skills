# Memory Theory for AI Agents

## The Continual Learning Problem

LLMs have vast but frozen knowledge. They cannot learn by updating weights after training. Without memory, an agent is like "an intern with amnesia"—brilliant but unable to recall previous conversations or learn from experience.

## The 4 Memory Layers

### 1. Internal Knowledge
- Pre-trained weights baked into the LLM
- Best for general world knowledge
- Frozen at training time
- Cannot be modified

### 2. Context Window
- Slice of information passed to LLM during a call
- Acts as "RAM" for single inference
- The only "reality" the model sees
- Limited by token count

### 3. Short-Term Memory
- RAM of the entire agentic system
- Contains: active context + recent interactions + retrieved long-term memories
- Volatile and fast
- Simulates "learning" during a session

### 4. Long-Term Memory
- External, persistent storage
- Provides personalization and context
- Three subtypes: semantic, episodic, procedural

## Long-Term Memory Types

### Semantic Memory (Facts & Knowledge)

The agent's encyclopedia. Stores individual pieces of knowledge.

**Characteristics:**
- Timeless facts, not tied to specific events
- Can be independent strings or structured attributes
- Provides reliable source of truth

**Examples:**
- `"User is vegetarian"`
- `{"food_restrictions": "vegetarian", "allergies": ["gluten"]}`
- `"User's brother Mark is a software engineer"`

**Use cases:**
- User profiles and preferences
- Project constraints and requirements
- Domain knowledge and relationships

### Episodic Memory (Experiences & History)

The agent's personal diary. Records past interactions with timestamps.

**Characteristics:**
- Always has a timestamp
- Captures "what happened and when"
- Essential for relationship dynamics

**Examples:**
- `"[2025-01-15] User expressed frustration about project deadline"`
- `"[2025-01-10] Helped debug authentication - root cause was JWT expiry"`

**Use cases:**
- Conversation context
- Tracking emotional tone over time
- Answering "what happened last week?"

### Procedural Memory (Skills & How-To)

The agent's muscle memory. Consists of learned workflows and multi-step tasks.

**Characteristics:**
- Often in system prompt as reusable tools
- Defines sequences and decision trees
- Makes behavior reliable and predictable

**Examples:**
```
Procedure: monthly_report
Steps:
1. Query sales DB for last 30 days
2. Summarize top 5 insights
3. Ask user whether to email or display
```

**Use cases:**
- Code review checklists
- Deployment workflows
- Data analysis pipelines

## The Memory Cycle

1. **User Input** → Triggers the system
2. **Retrieval** → Pull from long-term to short-term memory
3. **Context Engineering** → Slice short-term memory for context window
4. **Inference** → LLM generates output using context + internal knowledge
5. **Loop** → Output added to short-term memory
6. **Update** → New facts saved to long-term memory

## The "Lost in the Middle" Problem

Models struggle to use information buried in the center of long prompts. Even with large context windows, keeping everything in context introduces:
- Rising costs per turn
- Noise and overhead
- Reduced accuracy for middle content

**Solution:** Smart retrieval and context engineering rather than dumping everything.

## Context-Augmented Generation (CAG) vs RAG

For vertical AI agents with specific use cases, data often isn't that big. Through:
- Virtual multi-tenancy
- Smart data siloing
- Simple SQL queries

Everything can fit in modern context windows (~65k tokens, well within 1M capacity).

**When CAG beats RAG:**
- Domain-specific applications
- Well-structured data
- Need for speed and reliability

**When RAG is needed:**
- Massive document collections
- Unpredictable query patterns
- Cross-domain knowledge

## References

- Liu et al. (2023). "Lost in the Middle: How Language Models Use Long Contexts"
- Source: https://www.decodingai.com/p/how-does-memory-for-ai-agents-work
