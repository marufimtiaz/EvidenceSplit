# Production Compose Design

Create a standalone `docker-compose.prod.yml` that builds the existing backend and a production frontend image. No service binds a host port; Coolify's proxy reaches Caddy on internal port 80 while PostgreSQL and FastAPI remain private. Caddy serves the compiled React SPA, falls back to `index.html`, and proxies `/api/` to FastAPI with immediate response flushing for server-sent events.

The production stack uses restart policies, named database storage, service health checks, and `.env` configuration. `DATABASE_URL` and `POSTGRES_PASSWORD` are required at Compose interpolation time so production cannot silently start with development credentials. AI and discovery settings match the development stack.

Add `frontend/Dockerfile.prod` as a Node build plus Caddy runtime and `frontend/Caddyfile` for SPA/API routing. Build the frontend with an empty `VITE_API_URL`, causing browser requests to use same-origin `/api` paths. No application behavior, database schema, or provider logic changes. Per user instruction, do not run tests; verify Compose rendering, image builds, container startup, and health only.
