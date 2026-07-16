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
3. Relevant passages are retrieved and classified with Gemini.
4. The results page presents the evidence, citations, and limitations.

## Tech stack

- **Frontend:** React, TypeScript, Vite
- **Backend:** FastAPI, Python
- **Database:** PostgreSQL with pgvector
- **AI:** Gemini generation and embedding models
- **Deployment:** Docker Compose

## Quick start

Copy the environment template:

```bash
cp .env.example .env
```

Add your Gemini API key to `.env`:

```dotenv
GEMINI_API_KEY=your-key-here
```

Build and start the complete application:

```bash
docker compose up --build
```

Open the frontend at <http://localhost:5173>. The API is available at <http://localhost:8000>.

### Deterministic demo mode

For a presentation that does not depend on Gemini quota, set this in `.env`:

```dotenv
DEMO_MODE=true
```

Then restart with `docker compose up --build`. The frontend will offer three prepared claims and clearly label the results as fixture evidence. Set `DEMO_MODE=false` to restore normal PDF analysis.

Useful commands:

```bash
# Follow service logs
docker compose logs -f

# Stop the application
docker compose down

# Stop the application and delete local database data
docker compose down -v
```

## Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `GEMINI_API_KEY` | Gemini API authentication | Required |
| `DEMO_MODE` | Use three deterministic prepared analyses | `false` |
| `GEMINI_GENERATION_MODEL` | Evidence extraction and synthesis model | `gemini-2.5-flash` |
| `EMBEDDING_MODEL` | Document embedding model | `gemini-embedding-001` |
| `EMBEDDING_DIMENSIONS` | Embedding vector size | `384` |
| `VITE_API_URL` | API URL used by the frontend | `http://localhost:8000` |

See [.env.example](.env.example) for the complete configuration.

## API overview

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/analyses` | Create an analysis with a claim and PDFs |
| `GET` | `/api/analyses/{id}/events` | Stream analysis progress |
| `GET` | `/api/analyses/{id}` | Retrieve the completed report |
| `GET` | `/health` | Check API health |

## Current scope

- The current build analyzes uploaded, text-based PDFs; live OpenAlex/Unpaywall discovery is not enabled yet.
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
