# AISRM1 Worker

Background processor for document/AI tasks. It **shares the `apps/api` package**
(models, services, storage, AI) rather than duplicating code.

- Entry point: `python -m app.worker` (defined in `apps/api/app/worker.py`).
- Image: `infra/docker/worker.Dockerfile` (builds from `apps/api`).
- Drivers:
  - `TASK_DRIVER=local` → the API runs tasks inline; the worker idles.
  - `TASK_DRIVER=redis` → the worker consumes from the shared Redis list.
  - Production: Cloud Tasks → Cloud Run worker (OIDC-authenticated).

Handlers live in `apps/api/app/services/task_handlers.py` (e.g. `document.process`:
scan → extract text → chunk → embed → index for RAG).
