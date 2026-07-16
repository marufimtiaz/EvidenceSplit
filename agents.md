# AGENTS.md

## Project

EvidenceSplit is a scientific RAG application that compares evidence from uploaded papers and live scholarly sources. It groups findings as supporting, contradicting, qualifying, or irrelevant, then generates a balanced comparison with citations.

Read `EvidenceSplit_Agentic_Implementation_Guide.md` before making changes. It is the primary source of truth.

## Core Constraints

* Backend: FastAPI
* Frontend: Vite and React
* Database: PostgreSQL with pgvector
* Search OpenAlex using only the submitted claim.
* Use Unpaywall for open-access full text and fall back to abstracts.
* Label sources as `UPLOADED_PDF`, `LIVE_FULL_TEXT`, or `LIVE_ABSTRACT`.
* Use deterministic orchestration, not autonomous agent loops.
* Rank external papers before downloading full texts.
* Keep embedding and LLM services separate.
* Store stance per analysis, not directly on document chunks.
* Aggregate chunk findings into one paper-level stance.
* Generate conclusions only from extracted evidence.
* Use SSE for progress updates; do not add Celery for the MVP.

## Development Rules

* Keep modules small, typed, and focused.
* Use async I/O for APIs, downloads, and database operations.
* Validate file type, size, page count, redirects, and download timeouts.
* Preserve partial results when an external source fails.
* Never invent quotations, metadata, page numbers, or citations.
* Clearly distinguish abstract evidence from full-text evidence.
* Avoid unnecessary dependencies and unrelated refactoring.

## Workflow

1. Identify the current milestone in the implementation guide.
2. Inspect existing code and tests.
3. Implement one reviewable task at a time.
4. Add or update tests.
5. Run formatting, linting, type checking, and tests.
6. Update documentation when contracts change.
7. Commit only coherent, passing changes.

## Validation

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

```bash
pnpm install
pnpm run lint
pnpm run build
```

## Definition of Done

A change is complete when it is tested, documented, passes validation, preserves source provenance, and cannot generate unsupported scientific conclusions.
