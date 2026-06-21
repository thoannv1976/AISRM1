# 05 — API Specification

> Bản đầy đủ: `source/AISRM1_full_specification.txt` (Phần E). OpenAPI tự sinh: `GET /docs`, `GET /openapi.json`.

## Quy ước
- REST JSON dưới `/api/v1`. Resource = danh từ số nhiều; hành động nghiệp vụ = endpoint riêng (`/submit`, `/approve`, `/assign-reviewers`).
- Bearer token (JWT); permission dependency ở router + domain service (object-level authorization).
- Pagination (`page`/`limit` hoặc cursor); filter/sort allowlist.
- Thời gian ISO 8601 UTC; tiền = string decimal + currency.
- Lỗi theo RFC7807-like: `type, title, status, detail, code, field_errors, trace_id`.

## Nhóm endpoint
`/auth/*`, `/me`, `/organizations`, `/units`, `/users`, `/researchers`,
`/funding-programs`, `/funding-calls`, `/proposals` (+ `/validate`,`/submit`,`/decision`,`/activate-project`),
`/reviewers`, `/review-assignments`, `/reviews`, `/councils`, `/projects` (+ `/progress-reports`,`/change-requests`),
`/research-outputs` (+ `/claim`,`/verify`,`/deduplicate`), `/documents` (+ upload sessions),
`/ai/jobs`, `/ai/outputs`, `/ai/chat`, `/dashboards/*`, `/reports`, `/tasks/inbox`, `/audit-logs`.

## Mã lỗi nghiệp vụ
`AUTH_FORBIDDEN(403)`, `ENTITY_VERSION_CONFLICT(409)`, `INVALID_STATE_TRANSITION(409)`,
`SUBMISSION_INCOMPLETE(422)`, `DEADLINE_PASSED(422)`, `DOCUMENT_QUARANTINED(423)`,
`CONFLICT_OF_INTEREST(422)`, `AI_CITATION_REQUIRED(422)`, `AI_FEATURE_DISABLED(503)`, `RATE_LIMITED(429)`.
