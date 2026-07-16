# EvidenceSplit

> See where scientific evidence supports, contradicts, or qualifies a claim.

EvidenceSplit analyzes research PDFs against a scientific claim and produces a balanced, cited evidence report. It surfaces supporting, contradicting, and qualifying findings without pretending to determine universal truth.

## What it does

- Accepts a scientific claim and multiple PDF uploads
- Splits and embeds paper content for hybrid semantic and keyword retrieval
- Extracts evidence with source-backed quotations
- Groups findings as supporting, contradicting, or qualifying
- Produces a cited summary with limitations and an overall assessment
- Streams analysis progress to the frontend

## How it works

1. Enter a claim and upload up to five research PDFs.
2. EvidenceSplit parses and indexes the documents.
3. Relevant passages are retrieved and classified with Gemini or OpenRouter.
4. The results page presents the evidence, citations, and limitations.

## Tech stack

- **Frontend:** React, TypeScript, Vite
- **Backend:** FastAPI, Python
- **Database:** PostgreSQL with pgvector
- **AI:** Gemini or OpenRouter generation and embedding models
- **Deployment:** Docker Compose

## Quick start

Copy the environment template:

```bash
cp .env.example .env
```

Choose an AI provider and add its API key to `.env`:

```dotenv
AI_PROVIDER=gemini
GEMINI_API_KEY=your-key-here
```

To use OpenRouter for both generation and embeddings instead:

```dotenv
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=your-openrouter-key-here
```

Create an OpenRouter key at <https://openrouter.ai/settings/keys>.

Build and start the complete application:

```bash
docker compose up --build
```

Open the frontend at <http://localhost:5173>. The API is available at <http://localhost:8000>.

### Deterministic demo mode

The frontend includes a **Demo mode** switch. Demo submissions use prepared fixture evidence and do not depend on Gemini quota. To make the switch enabled initially, set this in `.env`:

```dotenv
DEMO_MODE=true
```

Then restart with `docker compose up --build`. You can switch back to live PDF analysis directly from the frontend at any time.

Useful commands:

```bash
# Follow backend pipeline and provider errors
docker compose logs -f backend

# Stop the application
docker compose down

# Stop the application and delete local database data
docker compose down -v
```

## Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `AI_PROVIDER` | AI adapter set: `gemini` or `openrouter` | `gemini` |
| `GEMINI_API_KEY` | Gemini API authentication | Required |
| `OPENROUTER_API_KEY` | OpenRouter API authentication | Required when selected |
| `OPENROUTER_GENERATION_MODEL` | OpenRouter evidence and synthesis model | `openai/gpt-4.1-mini` |
| `OPENROUTER_EMBEDDING_MODEL` | OpenRouter embedding model | `openai/text-embedding-3-small` |
| `SQL_ECHO` | Include verbose SQL statements in backend logs | `false` |
| `DEMO_MODE` | Initial state of the frontend Demo mode switch | `false` |
| `GEMINI_GENERATION_MODEL` | Evidence extraction and synthesis model | `gemini-3.5-flash` |
| `EMBEDDING_MODEL` | Document embedding model | `gemini-embedding-001` |
| `EMBEDDING_DIMENSIONS` | Embedding vector size | `384` |
| `VITE_API_URL` | API URL used by the frontend | `http://localhost:8000` |
| `OPENALEX_API_KEY` | OpenAlex API authentication for live discovery | Required for live mode |
| `UNPAYWALL_EMAIL` | Contact email required by the Unpaywall API | Required for OA lookup |

See [.env.example](.env.example) for the complete configuration.

## API overview

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/analyses` | Create an analysis with a claim and PDFs |
| `GET` | `/api/analyses/{id}/events` | Stream analysis progress |
| `GET` | `/api/analyses/{id}` | Retrieve the completed report |
| `GET` | `/health` | Check API health |

## Current scope

- Live mode searches OpenAlex and uses Unpaywall for open-access PDFs, with abstract fallback when full text is unavailable.
- Upload limits are five PDFs, 20 MB per file, and 100 pages per document.
- Scanned PDFs require OCR before upload.
- Results depend on the supplied papers and should support—not replace—expert scientific judgment.

## Project structure

```text
backend/            FastAPI application and analysis pipeline
frontend/           React user interface
docker-compose.yml  Local full-stack environment
docs/               Project guide and milestone documentation
```

For the full implementation roadmap, see [docs/agent-guide.md](docs/agent-guide.md).
