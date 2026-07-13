# Interview Prep Platform

An adaptive mock-interview engine. A student picks a **track** (e.g. Civil
Services / UPSC, Technical, Behavioral), goes through a session of
questions, gets each answer evaluated against a rubric, and receives
probing follow-up questions on weak answers — the way a real interviewer
drills into a vague response, rather than a static quiz.

This repo is **Phase 1**: the data model and CRUD API, with no AI agents
wired in yet. That's intentional — get the foundation solid and tested
before adding generation/evaluation/follow-up logic on top of it.

## Architecture (target, full build)

```
Student answer
      │
      ▼
┌─────────────────┐     ┌──────────────────┐     ┌────────────────────┐
│ Question Agent   │ →   │ Evaluation Agent  │ →   │ Follow-up Agent     │
│ (RAG-grounded,   │     │ (rubric-scored    │     │ (probes weak        │
│  LangGraph)      │     │  JSON output)     │     │  answers)           │
└─────────────────┘     └──────────────────┘     └────────────────────┘
                                  │
                                  ▼
                         Session summary agent
                       (strengths / weak areas)
```

Retrieval is backed by **Postgres + pgvector** rather than a separate
vector DB — keeps infra simple and is a deliberate choice over
Pinecone/Chroma for a system this size.

## Current state (Phase 1)

- Django + DRF project with token auth
- Models: `Track`, `Question`, `ReferenceSnippet` (pgvector-ready),
  `Session`, `Turn`
- Full CRUD API for all of the above, scoped so a user can only see their
  own sessions/turns
- Django admin wired up for managing tracks/questions without a frontend
- Works against sqlite for quick local iteration, or Postgres+pgvector via
  Docker Compose

## Quickstart (local, sqlite — fastest way to poke around)

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Visit `http://localhost:8000/admin/` to add a Track and some Questions,
or `http://localhost:8000/api/tracks/` to see the API.

## Quickstart (Docker, Postgres + pgvector — needed once RAG is added)

```bash
cp .env.example .env
docker compose up --build
```

This brings up Postgres (with the pgvector extension preloaded via the
`pgvector/pgvector:pg16` image), Redis, and the Django app, and runs
migrations automatically.

## API overview

| Endpoint | Notes |
|---|---|
| `POST /api/auth/token/` | Get an auth token (username/password) |
| `GET/POST /api/tracks/` | List/create tracks (read is public) |
| `GET/POST /api/questions/?track=<slug>` | Question bank, filterable by track |
| `GET/POST /api/sessions/` | A student's own mock-interview sessions |
| `GET/POST /api/turns/?session=<id>` | Q&A turns within a session |

## Roadmap

- **Phase 2** — ingestion pipeline: chunk + embed reference material into
  `ReferenceSnippet.embedding`, async via Celery
- **Phase 3** — evaluation agent: rubric-scored JSON output on submitted
  answers
- **Phase 4** — follow-up agent: generates probing follow-ups on weak
  turns
- **Phase 5** — LangGraph orchestration tying question generation →
  evaluation → follow-up → session summary into one state machine
- **Phase 6** — Next.js frontend
- **Phase 7+** — eval harness, rate limiting, polish

## Design notes

- UUID primary keys throughout, since session/turn IDs may end up
  client-visible (e.g. in URLs) and shouldn't be guessable/sequential.
- `Turn.question` is nullable and `question_text` is stored as a
  snapshot, because not every question a student sees will come from the
  seed bank — agent-generated questions still need a durable record.
- `ReferenceSnippet.embedding` falls back to a plain `JSONField` if
  `pgvector` isn't installed, so the schema doesn't hard-fail before
  Phase 2 wires up real embeddings — but Postgres is required for the
  vector index itself to do anything useful.
