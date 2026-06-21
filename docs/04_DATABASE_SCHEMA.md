# 04 — Database Schema

> Bản đầy đủ: `source/AISRM1_full_specification.txt` (Phần D). Hiện thực: `apps/api/app/models/`.

## Quy ước
- `id UUID` (PK), `created_at/updated_at timestamptz`, `created_by/updated_by`, `version int`, `deleted_at` (soft delete khi cần).
- Tiền: `amount numeric(20,4)` + `currency char(3)`; không dùng float.
- `organization_id` trên mọi bảng nghiệp vụ (multi-tenant ready).
- pgvector cho embeddings; GIN cho tsvector/JSONB; tệp gốc KHÔNG lưu trong DB.

## Nhóm bảng chính
- **Tổ chức & danh tính**: organizations, organization_units, research_groups, users, roles, permissions, role_assignments, delegations, sessions, audit_logs.
- **Nhà nghiên cứu**: researcher_profiles, researcher_identifiers, expertise_taxonomy, researcher_expertise.
- **Tài trợ**: funding_sources, funding_programs, funding_calls, eligibility_rules, form_templates.
- **Proposal**: proposals, proposal_versions, proposal_team_members, work_packages, milestones, deliverables, proposal_budget_lines, submissions.
- **Review**: reviewer_profiles, conflict_declarations, review_assignments, review_templates, reviews, review_scores, councils, council_members, council_meetings, votes, decisions.
- **Project**: projects, project_baselines, project_members, project_tasks, progress_reports, change_requests, risks, closures.
- **Outputs**: research_outputs, output_authors, output_identifiers, publication_venues, verifications.
- **Documents**: documents, document_versions, document_chunks, document_access_grants, embeddings.
- **AI**: ai_providers, ai_features, ai_prompt_templates, ai_jobs, ai_outputs, ai_citations, ai_feedback, ai_usage_ledger.
- **Workflow & báo cáo**: workflow_templates, workflow_instances, workflow_tasks, approvals, notifications, report_definitions, report_runs.

## Trạng thái (state machines)
- Proposal: DRAFT → INTERNAL_REVIEW → SUBMITTED → ADMIN_CHECK → ELIGIBLE/INELIGIBLE → UNDER_REVIEW → COUNCIL → APPROVED/REJECTED/WITHDRAWN
- Project: PENDING_ACTIVATION → ACTIVE → SUSPENDED/CHANGE_PENDING → CLOSING → UNDER_ACCEPTANCE → COMPLETED/TERMINATED
- Output: DRAFT/IMPORTED → CLAIMED → UNDER_VERIFICATION → VERIFIED → PUBLISHED/ARCHIVED
- Document: UPLOADING → QUARANTINED → PROCESSING → AVAILABLE/FAILED → SUPERSEDED → ARCHIVED
- AI job: QUEUED → RUNNING → SUCCEEDED/PARTIAL/FAILED/CANCELLED; output DRAFT → ACCEPTED/REJECTED/STALE
