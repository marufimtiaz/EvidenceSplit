# EvidenceSplit

## Run everything with Docker Compose

Create the environment file and add your Gemini API key:

```bash
cp .env.example .env
```

```dotenv
GEMINI_API_KEY=your-key-here
```

Start PostgreSQL, apply migrations, and launch the backend and frontend:

```bash
docker compose up --build
```

Open <http://localhost:5173>. The API is available at <http://localhost:8000>.

Stop the application with:

```bash
docker compose down
```

To also delete the local database volume:

```bash
docker compose down -v
```
