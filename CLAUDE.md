# AISRM1 — Instructions for Claude Code

## Product
AISRM1 (AI-ResearchHub) — an AI-integrated Scientific Research Management System
for a university Research Management Office (Phòng Quản lý khoa học). It manages
the full research lifecycle: funding calls → proposals → review/council →
projects → outputs/publications → IP/transfer → acceptance → KPI/rewards →
analytics & reporting, with a controlled AI Research Copilot.

Full specifications are in `docs/`. Business language is Vietnamese; code and
technical identifiers (tables, fields, endpoints, enums, prompts) are English.

## Architecture
Modular monolith: `apps/web` (Next.js), `apps/api` (FastAPI), `apps/worker`
(background document/AI tasks). PostgreSQL + pgvector, object-storage
abstraction (`StorageService`: local/MinIO/GCS), async task abstraction
(`TaskQueue`: local/redis/Cloud Tasks), provider-agnostic AI
(`LLMProvider`/`EmbeddingProvider`).

## Engineering rules
- Python: FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, pytest, Ruff.
- TypeScript: strict mode, typed API client, Next.js App Router.
- UUID primary keys; snake_case DB; `timestamptz`; `Decimal` for money.
- Domain services own state transitions. Never update status directly.
- All list endpoints paginate; all entity reads enforce object-level scope.
- No original file blobs in DB. No secrets in repo/logs.

## AI rules
- AI is **suggestion-only** and requires human review (human-in-the-loop).
- Use `LLMProvider`/`EmbeddingProvider` interfaces and environment model aliases.
- RAG must filter permissions **before** retrieval and return citations.
- Validate structured output; record model/prompt/input hash/usage/feedback.
- Do not send Restricted content to unapproved providers.
- Never fabricate facts, identifiers, scores, amounts, rankings, or decisions.

## Workflow
One epic at a time. Create feature branch, implement code + migration + tests +
docs, run checks, open PR, summarize, and stop for review. Never push to `main`,
force-push shared branches, delete applied migrations, or deploy production
without explicit human approval.

## Module map (backend)
`identity, organization, researchers, funding, proposals, reviews, projects,
finance_view, outputs, ip_transfer, ethics_integrity, documents, workflow,
analytics, ai, integrations, administration`

## Quick start
```bash
cp .env.example .env
docker compose up --build      # full stack
# API: http://localhost:8000/docs   Web: http://localhost:3000
```
Default demo admin: `admin@aisrm1.edu.vn` / `Admin@12345` (local only).
