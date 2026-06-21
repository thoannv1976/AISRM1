# 10 — Lộ trình & Backlog theo Epic

## Lộ trình 6 giai đoạn
| GĐ | Tên | Kết quả chính |
|---|---|---|
| 0 | Chuẩn hóa yêu cầu | PRD, process maps, roles, forms, report definitions, security classification |
| 1 | Nền tảng lõi | Repo, CI, auth/RBAC, organization, researcher profiles, dictionaries, audit |
| 2 | Call–Proposal–Review | Funding call, proposal, documents, reviewer/COI, scorecard, council, decision |
| 3 | Project–Output–Reporting | Activation, progress, change, deliverable, closure, outputs, dashboards/reports |
| 4 | AI & tích hợp | RAG, extraction, consistency, matching, metadata; HR/Finance/Library connectors |
| 5 | Pilot & hardening | UAT, migration, security/performance, production, IP/Ethics/KPI extensions |

## Backlog theo epic (cho Claude Code)
| Epic | Tên | Phạm vi |
|---|---|---|
| E1 | Project Setup | Monorepo, Docker Compose, FastAPI/Next.js/worker, Postgres+pgvector, MinIO, health, CI |
| E2 | Identity & RBAC | Users, roles, scopes, auth, permission tests, audit, seed admins |
| E3 | Organization & Researchers | Units/history, profiles, identifiers, expertise, search, CV export, import |
| E4 | Funding Programs & Calls | Programs, calls, versioning, form/checklist, eligibility, publish |
| E5 | Proposal Workspace | Proposal versions, team, workplan, milestones, deliverables, budget, documents, submit |
| E6 | Review & Council | Reviewer pool, COI, matching, assignment, review form, council, decision |
| E7 | Project Lifecycle | Activation, baseline, plan, progress, risk, change, deliverable, closure |
| E8 | Outputs & Research Profiles | Publication/output, author order, identifiers, venue, duplicate, verification |
| E9 | Document Platform | Storage abstraction, signed upload, malware hook, extraction, chunks, search, access |
| E10 | AI Foundation & RAG | Provider interfaces, prompt registry, AI jobs, embeddings, RAG citations, usage ledger |
| E11 | AI Research Features | Proposal review, reviewer suggestion, metadata extraction, duplicate detection, report draft |
| E12 | Workflow & Reporting | Generic workflow/tasks/notifications, dashboards, report catalog, snapshot/export |
| E13 | Integrations | HR/finance/library imports/connectors, mappings, sync/reconciliation/webhooks |
| E14 | GCP Production | Terraform, Cloud Build, Cloud Run, Cloud SQL/GCS/Tasks/Secrets, monitoring, backup |

## Definition of Done (mỗi epic)
- User stories & acceptance criteria trace đến issue/PR.
- Migration + seed an toàn; tests (unit/integration/permission) pass.
- OpenAPI/client types cập nhật; không breaking change chưa duyệt.
- Docker build & chạy non-root; vulnerability scan không có critical.
- Audit/logging/metrics/feature flags cần thiết đã có.
- Không secret/PII trong code/log. Docs + demo + release notes đầy đủ.
