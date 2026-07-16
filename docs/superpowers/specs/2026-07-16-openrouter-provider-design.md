# OpenRouter Provider Design

## Goal

Allow live analyses to use OpenRouter instead of Gemini for both structured generation and embeddings, while retaining Gemini as a configuration option.

## Configuration

- `AI_PROVIDER` selects `gemini` or `openrouter`; default remains `gemini`.
- `OPENROUTER_API_KEY` authenticates OpenRouter requests.
- `OPENROUTER_GENERATION_MODEL` defaults to `openai/gpt-4.1-mini`.
- `OPENROUTER_EMBEDDING_MODEL` defaults to `openai/text-embedding-3-small`.
- Existing `EMBEDDING_DIMENSIONS=384` remains the database vector size and is sent to OpenRouter.

## Architecture

Add three OpenRouter adapters implementing the existing `EmbeddingService`, `EvidenceAnalysisService`, and `SynthesisService` protocols. The provider factory selects one complete adapter set using `AI_PROVIDER`. Pipeline and domain services remain provider-agnostic.

OpenRouter generation uses `POST /api/v1/chat/completions` with strict JSON Schema output. Embeddings use `POST /api/v1/embeddings`, batched with the configured 384 dimensions. Requests use bearer authentication and the existing sanitized `ProviderHTTPError` logging pattern.

## Data Flow and Failure Handling

The pipeline asks the factory for services exactly as it does now. With `AI_PROVIDER=openrouter`, all AI calls use OpenRouter. Provider errors record operation, status, model, and a bounded response body without logging credentials. Rate-limit messages refer to the selected provider.

There is no automatic cross-provider retry in this version: it could create unexpected cost and requires two configured keys. Switching providers is explicit through Compose configuration.

## Scope

Update backend configuration, provider factory, three provider adapters, Compose variables, `.env.example`, and README. No frontend provider selector, database migration, prompt redesign, or unrelated refactor.

## Verification

Per the current user instruction, do not run tests. Verify formatting, container build/startup, active provider configuration, and backend health only.
