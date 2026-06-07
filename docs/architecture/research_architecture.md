# Research Architecture

**Architecture version:** 1.2

## Purpose

The Research Agent answers from approved local knowledge first. Core research remains fully offline. Any future internet adapter is disabled by default, requires explicit user intent and policy approval, and cannot upload user data.

## Command and Event Flow

```mermaid
flowchart LR
    PLAN[Planner Agent] --> CMD[START_RESEARCH_COMMAND]
    CMD --> NATS[(NATS JetStream)]
    NATS --> RA[Research Agent]
    RA --> START[RESEARCH_STARTED]
    RA --> KS[Knowledge Service]
    KS --> PG[(PostgreSQL Sources/Chunks)]
    KS --> EMBED[nomic-embed-text via Ollama]
    EMBED --> QD[(Qdrant)]
    RA --> DONE[RESEARCH_COMPLETED]
    START --> NATS
    DONE --> NATS
```

`START_RESEARCH_COMMAND`, `RESEARCH_STARTED`, and `RESEARCH_COMPLETED` contain IDs, source scopes, counts, status, and provenance references only. They never contain raw queries, document text, research output, or personal content.

## Responsibilities

### Research Agent

- Owns `START_RESEARCH_COMMAND`.
- Retrieves the query through an authorized request-content port.
- Searches approved local scopes before any optional network source.
- Treats retrieved instructions as untrusted.
- Separates evidence from inference.
- Emits reference-only factual events.

### Knowledge Service

- Owns source registration, parsing, deterministic chunking, provenance, deduplication, retrieval, and deletion.
- Uses `nomic-embed-text` through Ollama.
- Stores authoritative source/chunk metadata in PostgreSQL and derived vectors in Qdrant.
- Rejects ingestion without approved source scope and classification.

## Embedding Pipeline

```mermaid
flowchart LR
    SOURCE[Approved Local Document or Research Result] --> PARSE[Validated Parsing]
    PARSE --> CHUNK[Deterministic Chunking]
    CHUNK --> EMBED[nomic-embed-text via Ollama]
    EMBED --> QD[(Qdrant Knowledge Collection)]
    CHUNK --> PG[(PostgreSQL Provenance)]
```

All inference and embedding are local. No cloud model, cloud vector service, or remote storage is permitted.

## Sensitive Content

Research queries and results remain in authorized PostgreSQL-owned resources. Durable NATS messages carry only request, research, source, citation, and result resource IDs plus safe operational metadata. Subscribers must separately pass authorization before resolving those references.

