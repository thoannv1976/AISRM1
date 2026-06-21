# 09 — Triển khai (Deployment & DevOps)

> Bản đầy đủ: `source/AISRM1_full_specification.txt` (Phần I).

## Local (Docker Compose)
`cp .env.example .env && docker compose up --build` → API :8000, Web :3000, MinIO :9001.

## Production (Google Cloud)
- Cloud Run: web / api / worker (worker chỉ nhận OIDC task).
- Cloud Run Jobs: migration, batch import, re-index, scheduled report.
- Cloud SQL PostgreSQL + pgvector; Cloud Storage; Cloud Tasks; Secret Manager; Identity Platform.
- CI (GitHub Actions): lint/type/test, migration check, OpenAPI diff, docker build+scan, IaC plan.
- CD (Cloud Build): build image gắn commit SHA → Artifact Registry → deploy staging → smoke/UAT → prod.
- Migration expand-and-contract; rollback app qua Cloud Run revision; DB qua backup/PITR.

## Môi trường tách biệt
`aisrm1-dev`, `aisrm1-stg`, `aisrm1-prod` (project riêng, DB/bucket/secret riêng). Least-privilege IAM.

## Không được làm
Deploy thủ công prod; 1 project/DB/bucket cho mọi env; commit secret; cấp Owner rộng cho runtime SA;
chạy db push thẳng prod; lưu file trong DB; log prompt/tài liệu Restricted plaintext; tự push main/deploy.
