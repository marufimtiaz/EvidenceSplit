# EvidenceSplit — Agentic Implementation Guide

> **For agentic workers:** Implement this project one milestone at a time. Do not build later milestones early. After each milestone, run its tests, verify the application still starts, and commit the changes.

## 1. Project Goal

EvidenceSplit is a domain-agnostic scientific RAG application.

A user:

1. enters a scientific claim;
2. uploads one or more research-paper PDFs;
3. submits the analysis;
4. the application searches OpenAlex using only the claim;
5. it uses Unpaywall to locate open-access full text when available;
6. it falls back to the paper abstract when full text is unavailable;
7. it extracts evidence relevant to the claim;
8. it groups papers as **Supporting**, **Contradicting**, or **Qualifying**;
9. it generates a balanced comparison with traceable citations.

Every evidence item must be clearly labeled as one of:

- `UPLOADED_PDF`
- `LIVE_FULL_TEXT`
- `LIVE_ABSTRACT`

The system must not decide whether the scientific claim is universally true. It reports what the retrieved papers say and where they disagree.

---

## 2. Hackathon MVP Scope

### Required features

- Claim input
- Multiple PDF upload
- OpenAlex paper search using only the submitted claim
- Unpaywall lookup for open-access full text
- Abstract fallback
- PDF text extraction
- Metadata-preserving chunking
- Hybrid retrieval using semantic and keyword relevance
- Structured evidence extraction
- Four internal stance labels:
  - `SUPPORTING`
  - `CONTRADICTING`
  - `QUALIFYING`
  - `IRRELEVANT`
- Paper-level stance aggregation
- Balanced synthesis using only extracted evidence
- Inline citations
- Three evidence columns in the UI
- Analysis progress updates through Server-Sent Events
- Clear failure messages and partial-result handling

### Explicit non-goals

Do not add these during the MVP:

- User accounts
- Payment or subscription handling
- Autonomous multi-agent frameworks
- Knowledge graphs
- Fine-tuning
- OCR for scanned PDFs
- Full systematic-review automation
- Journal ranking or scientific-quality scoring
- Citation-network analysis
- Celery or distributed workers
- Permanent storage of uploaded files
- Large-scale RAG evaluation dashboards

---

## 3. Core Product Rules

1. **Use only the claim for live search.** Do not derive search terms from uploaded PDFs.
2. **Prefer full text, but allow abstract fallback.**
3. **Never hide source quality.** The UI must show whether evidence came from uploaded full text, live full text, or an abstract.
4. **Retrieve evidence before synthesis.** The synthesis model must not receive entire documents.
5. **Classify evidence relative to the exact claim.** Stance is not a permanent property of a paper or chunk.
6. **Preserve scientific conditions.** Population, dosage, temperature, material, method, sample size, and other constraints must remain visible when present.
7. **Do not force consensus.** Mixed evidence must remain mixed.
8. **Every factual statement in the final comparison must cite at least one evidence finding.**
9. **If evidence is insufficient, say so.**
10. **The pipeline is deterministic orchestration, not an autonomous agent loop.**

---

## 4. Recommended Technology Stack

### Frontend

- Vite
- React
- TypeScript
- TanStack Query or a small custom API layer
- Native `EventSource` for SSE

### Backend

- Python 3.13
- FastAPI
- Pydantic
- SQLAlchemy 2.x async
- PostgreSQL
- pgvector
- PyMuPDF for PDF extraction
- `httpx` for OpenAlex, Unpaywall, and PDF downloads

### AI services

- Gemini for evidence extraction, stance classification, and synthesis
- A dedicated embedding provider or local sentence-transformer model

Do not combine embedding and generation responsibilities in one interface. They may use different providers later.

---

## 5. High-Level Architecture

```text
Vite/React frontend
        |
        | POST claim + PDFs
        v
FastAPI analysis API
        |
        +--> Uploaded PDF processor
        |
        +--> OpenAlex search client
                  |
                  v
             Unpaywall resolver
                  |
                  v
          Selected full-text downloader
        |
        v
Document normalization and chunking
        |
        v
PostgreSQL + pgvector
        |
        v
Hybrid evidence retrieval
        |
        v
Evidence extraction and stance classification
        |
        v
Paper-level aggregation
        |
        v
Balanced synthesis with citations
        |
        +--> SSE progress events
        |
        v
Three-column comparison UI
```

---

## 6. Correct Pipeline Order

Do not download every paper returned by OpenAlex.

Use this order:

```text
Claim + uploaded PDFs
        |
        +--> Process uploaded PDFs concurrently
        |
        +--> Search OpenAlex using claim
                 |
                 v
          Rank title + abstract metadata
                 |
                 v
          Select top 5–8 candidate papers
                 |
                 v
          Resolve open access through Unpaywall
                 |
                 v
          Download only top 3–5 available full texts
                 |
                 v
          Fall back to abstracts when needed
        |
        v
Chunk selected sources
        |
        v
Hybrid retrieve claim-relevant passages
        |
        v
Extract and classify evidence
        |
        v
Aggregate per paper
        |
        v
Synthesize balanced comparison
```

This order keeps the demo responsive and avoids embedding irrelevant full papers.

---

## 7. Repository Structure

Use feature-focused modules with small files and clear boundaries.

```text
evidencesplit/
├── README.md
├── .env.example
├── docker-compose.yml
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── migrations/
│   ├── src/evidencesplit/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── api/
│   │   │   ├── analyses.py
│   │   │   └── events.py
│   │   ├── analyses/
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── repository.py
│   │   │   ├── service.py
│   │   │   └── pipeline.py
│   │   ├── documents/
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── repository.py
│   │   │   ├── pdf_parser.py
│   │   │   ├── downloader.py
│   │   │   ├── chunker.py
│   │   │   └── normalizer.py
│   │   ├── discovery/
│   │   │   ├── openalex.py
│   │   │   ├── unpaywall.py
│   │   │   ├── schemas.py
│   │   │   └── service.py
│   │   ├── retrieval/
│   │   │   ├── embeddings.py
│   │   │   ├── hybrid.py
│   │   │   ├── reranker.py
│   │   │   └── schemas.py
│   │   ├── evidence/
│   │   │   ├── schemas.py
│   │   │   ├── analyzer.py
│   │   │   ├── aggregator.py
│   │   │   └── prompts.py
│   │   ├── synthesis/
│   │   │   ├── service.py
│   │   │   ├── schemas.py
│   │   │   └── prompts.py
│   │   ├── providers/
│   │   │   ├── protocols.py
│   │   │   ├── gemini.py
│   │   │   └── local_embeddings.py
│   │   └── shared/
│   │       ├── errors.py
│   │       ├── security.py
│   │       └── types.py
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── fixtures/
└── frontend/
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── api/
        │   └── analyses.ts
        ├── components/
        │   ├── ClaimForm.tsx
        │   ├── UploadList.tsx
        │   ├── ProgressPanel.tsx
        │   ├── AssessmentHeader.tsx
        │   ├── EvidenceColumn.tsx
        │   └── EvidenceCard.tsx
        ├── pages/
        │   └── AnalysisPage.tsx
        └── types/
            └── analysis.ts
```

### File-boundary rule

A file should have one clear responsibility. For example:

- `openalex.py` talks to OpenAlex only.
- `unpaywall.py` talks to Unpaywall only.
- `pdf_parser.py` extracts text from PDFs only.
- `analyzer.py` extracts and classifies evidence only.
- `aggregator.py` combines chunk-level findings into a paper-level result only.
- `service.py` files coordinate their feature but do not contain provider-specific HTTP code.

---

## 8. Service Interfaces

Define provider contracts before writing provider implementations.

```python
from typing import Protocol, Sequence


class EmbeddingService(Protocol):
    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        ...

    async def embed_query(self, text: str) -> list[float]:
        ...


class EvidenceAnalysisService(Protocol):
    async def analyze_passages(
        self,
        *,
        claim: str,
        passages: Sequence["RetrievedPassage"],
    ) -> list["EvidenceFinding"]:
        ...


class SynthesisService(Protocol):
    async def synthesize(
        self,
        *,
        claim: str,
        papers: Sequence["PaperAssessment"],
    ) -> "ComparisonReport":
        ...
```

The pipeline depends on these protocols. It must not directly import Gemini-specific classes.

---

## 9. Domain Models

Use enums instead of uncontrolled strings.

```python
from enum import StrEnum


class SourceType(StrEnum):
    UPLOADED_PDF = "UPLOADED_PDF"
    LIVE_FULL_TEXT = "LIVE_FULL_TEXT"
    LIVE_ABSTRACT = "LIVE_ABSTRACT"


class Stance(StrEnum):
    SUPPORTING = "SUPPORTING"
    CONTRADICTING = "CONTRADICTING"
    QUALIFYING = "QUALIFYING"
    IRRELEVANT = "IRRELEVANT"


class AnalysisStatus(StrEnum):
    QUEUED = "QUEUED"
    PROCESSING_UPLOADS = "PROCESSING_UPLOADS"
    SEARCHING = "SEARCHING"
    FETCHING_FULL_TEXT = "FETCHING_FULL_TEXT"
    INDEXING = "INDEXING"
    RETRIEVING = "RETRIEVING"
    ANALYZING_EVIDENCE = "ANALYZING_EVIDENCE"
    SYNTHESIZING = "SYNTHESIZING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"
    FAILED = "FAILED"
```

### Important distinction

A chunk does not have a permanent stance. Stance belongs to an evidence finding created for a specific analysis and claim.

---

## 10. Database Model

### `analyses`

| Field | Purpose |
|---|---|
| `id` | UUID primary key |
| `claim` | Exact user-submitted claim |
| `status` | Current pipeline stage |
| `progress` | Integer from 0 to 100 |
| `warning_message` | Partial-result warning |
| `error_message` | Safe user-facing failure message |
| `created_at` | Creation time |
| `completed_at` | Completion time |

### `documents`

| Field | Purpose |
|---|---|
| `id` | UUID primary key |
| `analysis_id` | Parent analysis |
| `source_type` | Uploaded, live full text, or abstract |
| `title` | Paper title or uploaded filename |
| `authors` | Normalized author list |
| `year` | Publication year |
| `doi` | DOI when available |
| `source_url` | Original source URL |
| `page_count` | PDF page count when available |
| `processing_status` | Document-level status |

### `chunks`

| Field | Purpose |
|---|---|
| `id` | UUID primary key |
| `document_id` | Parent document |
| `content` | Normalized chunk text |
| `page_start` | First source page |
| `page_end` | Last source page |
| `section` | Section name when detected |
| `chunk_index` | Position in document |
| `embedding` | pgvector embedding |
| `search_vector` | PostgreSQL full-text vector |

### `evidence_findings`

| Field | Purpose |
|---|---|
| `id` | UUID primary key |
| `analysis_id` | Analysis that created the finding |
| `document_id` | Source paper |
| `chunk_id` | Source chunk |
| `stance` | Claim-relative stance |
| `evidence_quote` | Exact extracted evidence |
| `explanation` | Why the evidence has this stance |
| `conditions` | Important limitations or context |
| `confidence` | Model-reported confidence from 0 to 1 |

### `paper_assessments`

| Field | Purpose |
|---|---|
| `id` | UUID primary key |
| `analysis_id` | Parent analysis |
| `document_id` | Assessed paper |
| `stance` | Aggregated paper stance |
| `summary` | Paper-level summary |
| `finding_ids` | Referenced evidence findings |

### `comparison_reports`

| Field | Purpose |
|---|---|
| `analysis_id` | One report per analysis |
| `overall_assessment` | Supported, contradicted, mixed, conditional, or insufficient |
| `summary` | Balanced overview |
| `limitations` | Evidence and source limitations |
| `report_json` | Complete structured response |

---

## 11. API Contracts

### Create analysis

```http
POST /api/analyses
Content-Type: multipart/form-data
```

Fields:

- `claim`: required string
- `files`: zero or more PDF files

Response:

```json
{
  "analysis_id": "2dc11c21-d15a-43a8-9b51-5c346a2ea99c",
  "status": "QUEUED"
}
```

Return immediately. Start the analysis as an in-process background task.

### Stream progress

```http
GET /api/analyses/{analysis_id}/events
Accept: text/event-stream
```

Example event:

```text
event: progress
data: {"stage":"SEARCHING","progress":30,"message":"Searching scholarly sources"}
```

Terminal events:

- `completed`
- `completed_with_warnings`
- `failed`

### Read final result

```http
GET /api/analyses/{analysis_id}
```

Response shape:

```json
{
  "id": "...",
  "claim": "Higher annealing temperature always increases crystallite size.",
  "status": "COMPLETED",
  "overall_assessment": "CONDITIONAL",
  "summary": "The retrieved literature generally reports an increase within specific temperature ranges, but does not support an unconditional relationship.",
  "supporting": [],
  "contradicting": [],
  "qualifying": [],
  "limitations": [
    "Two external papers were available only as abstracts."
  ]
}
```

Each evidence card must contain:

```json
{
  "document_id": "...",
  "title": "...",
  "authors": ["..."],
  "year": 2024,
  "doi": "...",
  "source_url": "...",
  "source_type": "LIVE_FULL_TEXT",
  "paper_stance": "QUALIFYING",
  "paper_summary": "...",
  "findings": [
    {
      "evidence_quote": "...",
      "explanation": "...",
      "conditions": "...",
      "page_start": 4,
      "page_end": 4
    }
  ]
}
```

---

## 12. Uploaded PDF Processing

### Validation

Reject a file when:

- extension is not `.pdf`;
- MIME type is not PDF;
- file exceeds the configured size limit;
- page count exceeds the configured page limit;
- no meaningful text can be extracted.

Recommended MVP limits:

- Maximum 5 uploaded PDFs
- Maximum 20 MB per file
- Maximum 100 pages per PDF

### Extraction

Use PyMuPDF and preserve page boundaries.

Return normalized page objects:

```python
class ParsedPage(BaseModel):
    page_number: int
    text: str
```

Do not join the entire document into one untraceable string.

### Scanned PDFs

OCR is outside the MVP. Return a clear warning:

> “This PDF appears to contain little or no extractable text. Scanned-document OCR is not supported in this version.”

Continue processing other documents.

---

## 13. OpenAlex and Unpaywall Discovery

### OpenAlex search

Input:

- exact claim only

Output:

- normalized candidate papers containing title, authors, year, DOI, abstract, source URL, and open-access hints

Do not send uploaded-paper text to OpenAlex.

### Candidate selection

1. Search OpenAlex.
2. Remove records without a title.
3. Deduplicate by DOI; if no DOI exists, normalize and compare title.
4. Rank using title and abstract relevance to the claim.
5. Keep the top 5–8 candidates.

### Unpaywall resolution

For candidates with a DOI:

1. request open-access locations;
2. prefer a direct PDF URL;
3. otherwise accept an accessible full-text landing page only when the downloader can resolve a PDF safely;
4. apply download limits and timeouts;
5. fall back to the OpenAlex abstract on any nonfatal failure.

### Source-type assignment

- Successfully downloaded and parsed external PDF: `LIVE_FULL_TEXT`
- External candidate with only an abstract: `LIVE_ABSTRACT`
- User file: `UPLOADED_PDF`

---

## 14. Safe Remote PDF Downloading

The downloader must protect against unsafe URLs.

Required controls:

- Allow only `http` and `https`
- Reject localhost and private-network destinations
- Revalidate every redirect target
- Limit redirects
- Apply connection and read timeouts
- Reject oversized responses
- Confirm PDF content type or valid PDF signature
- Store downloads in a temporary directory
- Delete temporary files after processing

A failure to download one paper must not fail the entire analysis. Use its abstract when possible and add a warning.

---

## 15. Chunking Strategy

Use section-aware and page-aware chunks when possible.

Recommended starting configuration:

- 700–1,000 tokens per chunk
- 100–150 token overlap
- Never merge content from different documents
- Preserve page range
- Preserve section title when available

Each chunk must retain:

```json
{
  "analysis_id": "...",
  "document_id": "...",
  "source_type": "UPLOADED_PDF",
  "title": "...",
  "doi": "...",
  "page_start": 3,
  "page_end": 4,
  "section": "Results",
  "chunk_index": 7,
  "content": "..."
}
```

Abstracts normally become one chunk and have no page number.

---

## 16. Hybrid Retrieval

Use both semantic and lexical retrieval.

### Semantic retrieval

- Embed the exact claim.
- Search chunk embeddings with pgvector.

### Keyword retrieval

- Search PostgreSQL full-text vectors.
- Preserve exact scientific terms, abbreviations, formulas, gene names, material names, and model names.

### Fusion

For the MVP, normalize both result scores and combine them:

```text
combined_score = 0.65 * semantic_score + 0.35 * keyword_score
```

Retrieve a diverse set across documents. Do not allow one long paper to fill all top positions.

Recommended limits:

- Up to 4 chunks per document before classification
- Up to 20 passages total

A reranker is optional. Add it only after the base pipeline works.

---

## 17. Evidence Extraction and Stance Classification

Run extraction and classification together using structured output.

### Input

- Exact claim
- Passage text
- Passage metadata

### Output schema

```python
class EvidenceFindingOutput(BaseModel):
    relevant: bool
    stance: Stance
    evidence_quote: str | None
    explanation: str | None
    conditions: str | None
    confidence: float
```

### Classification definitions

#### `SUPPORTING`

The passage provides evidence consistent with the claim as written.

#### `CONTRADICTING`

The passage provides evidence that directly opposes the claim.

#### `QUALIFYING`

The passage supports or contradicts only under specific conditions, weakens absolute wording, reports mixed results, or identifies an important limitation.

#### `IRRELEVANT`

The passage does not provide evidence about the relationship asserted by the claim.

### Model rules

- Quote evidence exactly from the passage.
- Do not quote text not present in the passage.
- Use `QUALIFYING` when the claim contains overly absolute language such as “always,” “never,” or “all,” but the evidence applies only under limited conditions.
- Classification is relative to the exact claim, not the general topic.
- Return `IRRELEVANT` when the passage mentions the topic but does not test or report the claimed relationship.

---

## 18. Paper-Level Aggregation

Do not display isolated chunks as independent papers.

Group findings by document and determine one paper-level assessment.

Suggested decision rules:

1. No relevant findings → exclude the paper.
2. Only supporting findings → `SUPPORTING`.
3. Only contradicting findings → `CONTRADICTING`.
4. Any important conditional limitation → usually `QUALIFYING`.
5. Both supporting and contradicting findings in the same paper → `QUALIFYING`, with both sides explained.
6. Abstract-only evidence must remain labeled as abstract-only.

The aggregator should use deterministic rules first. Use an LLM only to produce a concise paper summary from the already extracted findings.

---

## 19. Final Synthesis

The synthesis model receives:

- Exact claim
- Paper-level assessments
- Extracted evidence findings
- Citation IDs
- Source types

It must not receive raw complete documents.

### Required output

```python
class OverallAssessment(StrEnum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    MIXED = "MIXED"
    CONDITIONAL = "CONDITIONAL"
    INSUFFICIENT = "INSUFFICIENT"


class ComparisonReport(BaseModel):
    overall_assessment: OverallAssessment
    summary: str
    supporting_summary: str | None
    contradicting_summary: str | None
    qualifying_summary: str | None
    limitations: list[str]
    citation_ids: list[str]
```

### Synthesis rules

- Use only supplied evidence findings.
- Preserve disagreement.
- Do not count papers as votes or claim consensus from a small retrieved set.
- Call the UI visualization “Retrieved evidence distribution,” not “Scientific consensus.”
- Mention when evidence is abstract-only.
- Avoid words such as “proves” or “definitively” unless the supplied evidence explicitly justifies them.
- Cite each factual sentence using finding IDs.
- Return `INSUFFICIENT` when too little relevant evidence remains.

---

## 20. Progress and Background Execution

Use an in-process FastAPI background task for the hackathon MVP.

Do not hold the original POST request open while the full pipeline runs.

### Progress stages

| Stage | Suggested progress |
|---|---:|
| Queued | 0 |
| Processing uploads | 10 |
| Searching OpenAlex | 25 |
| Resolving and fetching full text | 40 |
| Chunking and indexing | 55 |
| Retrieving evidence | 70 |
| Classifying evidence | 82 |
| Aggregating papers | 90 |
| Synthesizing report | 96 |
| Completed | 100 |

Progress percentages are user-interface estimates, not exact computation completion.

### Concurrency

Use `asyncio.gather()` for independent network calls.

Do not run CPU-heavy PDF parsing directly on the event loop. Use `asyncio.to_thread()` or a bounded executor.

### Partial failure behavior

- One invalid uploaded PDF: continue with other sources and show a warning.
- OpenAlex unavailable: continue with uploaded PDFs.
- Unpaywall unavailable: use available abstracts.
- External PDF download fails: use abstract where available.
- One LLM batch fails: retry once, then continue with other findings.
- Synthesis fails: return grouped evidence without the synthesized overview.

---

## 21. Frontend Requirements

### Claim form

- Required claim text area
- PDF drag-and-drop input
- Uploaded-file list with remove action
- Submit button
- Validation messages

### Progress view

- Current stage
- Progress bar
- Human-readable status message
- Warnings without stopping the entire job

### Results view

Display:

1. Exact submitted claim
2. Overall assessment badge
3. Balanced summary
4. Retrieved-paper count
5. Retrieved evidence distribution
6. Three evidence columns:
   - Supporting
   - Contradicting
   - Qualifying
7. Limitations

### Evidence card

Each card shows:

- Paper title
- Authors and year
- Source badge
- Paper-level stance
- Short paper assessment
- Expandable evidence quotes
- Page number for PDF evidence
- DOI or source link

Never visually imply that abstract evidence has the same depth as full-text evidence.

---

## 22. Configuration

Use environment variables and validate them at startup.

```dotenv
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/evidencesplit
GEMINI_API_KEY=
OPENALEX_API_KEY=
UNPAYWALL_EMAIL=
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
MAX_UPLOAD_FILES=5
MAX_UPLOAD_SIZE_MB=20
MAX_PDF_PAGES=100
OPENALEX_RESULT_LIMIT=8
MAX_LIVE_FULL_TEXT_PAPERS=5
MAX_PASSAGES_PER_DOCUMENT=4
MAX_TOTAL_PASSAGES=20
REMOTE_DOWNLOAD_TIMEOUT_SECONDS=20
MAX_REMOTE_PDF_SIZE_MB=25
```

Never commit real credentials.

---

## 23. Error Model

Define application errors centrally.

```python
class EvidenceSplitError(Exception):
    code: str
    user_message: str
    retryable: bool
```

Recommended error codes:

- `INVALID_CLAIM`
- `INVALID_PDF`
- `PDF_TOO_LARGE`
- `PDF_TEXT_UNAVAILABLE`
- `DISCOVERY_UNAVAILABLE`
- `FULL_TEXT_DOWNLOAD_FAILED`
- `EMBEDDING_FAILED`
- `EVIDENCE_ANALYSIS_FAILED`
- `SYNTHESIS_FAILED`
- `ANALYSIS_NOT_FOUND`

Logs may contain technical details. API responses must contain safe user-facing messages.

---

## 24. Testing Strategy

The hackathon can skip formal RAG-quality evaluation, but implementation tests are still required.

### Unit tests

Test:

- PDF validation
- Source-type assignment
- DOI and title deduplication
- Chunk metadata preservation
- Hybrid-score fusion
- Maximum chunks per document
- Stance aggregation rules
- Citation formatting
- SSRF URL rejection
- Partial-failure decisions

### Integration tests

Use mocked external APIs to test:

- OpenAlex search normalization
- Unpaywall full-text resolution
- Abstract fallback
- Analysis creation and SSE progression
- Complete pipeline with one uploaded PDF and two live candidates

### Smoke test

Before each demo build:

1. Start PostgreSQL.
2. Start FastAPI.
3. Start Vite.
4. Submit one claim and one text-based PDF.
5. Confirm live papers are returned.
6. Confirm all evidence cards have source labels.
7. Confirm citations open or identify the source.
8. Confirm a failed external PDF falls back to an abstract.

---

## 25. Implementation Milestones

Implement in this exact order.

### Milestone 1 — Project foundation

Deliverable:

- Backend and frontend start successfully
- PostgreSQL connection works
- Health endpoint works
- Environment validation works

Do not implement RAG yet.

### Milestone 2 — Analysis job API and SSE

Deliverable:

- `POST /api/analyses` returns an analysis ID
- Background task updates status
- Frontend receives progress through SSE
- A fake pipeline reaches `COMPLETED`

### Milestone 3 — Uploaded PDF ingestion

Deliverable:

- Multiple PDFs accepted and validated
- Text extracted by page
- Documents and chunks persisted
- Invalid PDFs produce warnings without crashing the analysis

### Milestone 4 — Live paper discovery

Deliverable:

- OpenAlex results normalized and deduplicated
- Unpaywall resolves full text
- Selected external PDFs download safely
- Abstract fallback works
- Source types are correct

### Milestone 5 — Embeddings and hybrid retrieval

Deliverable:

- Chunks receive embeddings and search vectors
- Exact claim retrieves relevant passages
- Per-document and total limits are enforced

### Milestone 6 — Evidence analysis

Deliverable:

- Gemini returns schema-valid evidence findings
- Irrelevant passages are discarded
- Exact quote, explanation, conditions, and stance are stored

### Milestone 7 — Paper aggregation

Deliverable:

- Findings are grouped by document
- One paper-level stance is produced
- Mixed within-paper evidence becomes qualifying

### Milestone 8 — Synthesis and citations

Deliverable:

- Balanced structured report generated from findings only
- Every factual sentence contains citation IDs
- Insufficient evidence is handled

### Milestone 9 — Final results UI

Deliverable:

- Overall assessment
- Summary
- Three evidence columns
- Source badges
- Expandable quotations
- DOI/source links
- Limitations and warnings

### Milestone 10 — Demo hardening

Deliverable:

- Three prepared demo claims
- Cached or fixture-based fallback demo mode
- Graceful handling of API failures
- File and download limits
- Temporary-file cleanup
- Final smoke test passes

---

## 26. Agentic Coding Rules

Every coding agent must follow these rules.

### Before changing code

1. Read this document completely.
2. Read the relevant existing files.
3. Identify the current milestone.
4. State which files will change.
5. Do not alter unrelated modules.

### During implementation

1. Work on one milestone or one small task only.
2. Write or update tests first when practical.
3. Use typed Pydantic models at external and AI boundaries.
4. Use protocols for swappable providers.
5. Keep provider-specific code outside orchestration services.
6. Preserve provenance metadata at every transformation.
7. Never store stance on a chunk record.
8. Never pass full documents to the synthesis model.
9. Never add an agent framework unless the specification changes.
10. Avoid dependencies not required by the active milestone.

### Before declaring completion

1. Run the relevant unit tests.
2. Run affected integration tests.
3. Run type checking and linting.
4. Verify the backend starts.
5. Verify migrations apply cleanly when database models changed.
6. Review the diff for unrelated edits.
7. Report:
   - files changed;
   - tests run;
   - known limitations;
   - next milestone dependency.

### Commit style

Use small conventional commits:

```text
feat: add OpenAlex paper discovery
feat: add PDF chunk persistence
fix: fall back to abstract after PDF timeout
test: cover paper stance aggregation
refactor: separate embeddings from generation provider
```

---

## 27. Prompt for a Coding Agent

Use this prompt when starting implementation in an AI coding environment:

```text
You are implementing EvidenceSplit using the specification in
EvidenceSplit_Agentic_Implementation_Guide.md.

Read the entire specification and inspect the repository before editing.
Work only on the milestone I name. Do not implement future milestones or
introduce autonomous agent frameworks.

For the selected milestone:
1. summarize the relevant existing architecture;
2. list the exact files you will create or modify;
3. write or update focused tests;
4. implement the smallest complete solution;
5. run tests, linting, and type checks;
6. report verification results and remaining limitations.

Preserve source provenance, use structured outputs, keep provider-specific
code behind protocols, and never store stance as a permanent chunk property.
Do not claim completion without showing verification output.

Current milestone: Milestone 1 — Project foundation
```

---

## 28. Demo Scenario

Use a claim with room for disagreement or qualification, for example:

> “Higher annealing temperature always increases crystallite size.”

Prepare:

- One uploaded paper that supports an increase within a specific range
- One uploaded or live paper that reports no clear effect
- One paper that reports a conditional or non-monotonic relationship

The demo should visibly show:

- Uploaded and live sources together
- Full-text and abstract source badges
- Supporting, contradicting, and qualifying columns
- Conditions that challenge the word “always”
- Inline citations that lead back to the evidence

The key product message is:

> EvidenceSplit does not produce one overconfident answer. It retrieves and organizes the evidence so users can see where research agrees, disagrees, or depends on specific conditions.

---

## 29. Definition of Done for the Hackathon

The MVP is complete when:

- A user can submit any scientific claim.
- A user can upload multiple text-based PDFs.
- The application searches OpenAlex using only the claim.
- It attempts to obtain open-access full text through Unpaywall.
- It falls back to abstracts without failing the analysis.
- Uploaded and live sources are processed together.
- Relevant passages are retrieved through hybrid search.
- Evidence is classified into supporting, contradicting, qualifying, or irrelevant.
- Papers are grouped into one of the three visible evidence columns.
- The final comparison preserves disagreement and conditions.
- Every displayed finding has a traceable citation.
- The UI shows progress and partial failures clearly.
- The application completes at least three prepared demo claims reliably.
