# Production Compose Design

Create a standalone `docker-compose.prod.yml` that builds the existing backend and a production frontend image. Only Nginx publishes a host port; PostgreSQL and FastAPI remain on the private Compose network. Nginx serves the compiled React SPA, falls back to `index.html`, and proxies `/api/` to FastAPI with buffering disabled and a long read timeout for server-sent events.

The production stack uses restart policies, named database storage, service health checks, and `.env` configuration. `DATABASE_URL` and `POSTGRES_PASSWORD` are required at Compose interpolation time so production cannot silently start with development credentials. AI and discovery settings match the development stack. `APP_PORT` defaults to 80.

Add `frontend/Dockerfile.prod` as a Node build plus unprivileged Nginx runtime and `frontend/nginx.conf` for SPA/API routing. Build the frontend with an empty `VITE_API_URL`, causing browser requests to use same-origin `/api` paths. No application behavior, database schema, or provider logic changes. Per user instruction, do not run tests; verify Compose rendering, image builds, container startup, and health only.
