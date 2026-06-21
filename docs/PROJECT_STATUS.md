# Trạng thái build AISRM1

Cập nhật theo roadmap (epic E1–E14).

## Bổ sung phiên 2 (Reports + Council/Review + Ethics + KPI/Reward)
- ✅ **M16 Báo cáo R01–R28**: chạy báo cáo → snapshot bất biến (hash) → xuất **Excel/CSV/Word**; UI `/reports`.
- ✅ **M6 Hội đồng (nâng cao)**: review assignment inbox, council members/meetings, **bỏ phiếu + quorum + finalize → tạo quyết nghị**.
- ✅ **M11 Đạo đức & liêm chính**: hồ sơ Restricted, state machine DRAFT→SUBMITTED→SCREENING→UNDER_REVIEW→APPROVED/EXEMPT/REJECTED; UI `/ethics`.
- ✅ **M12 KPI & khen thưởng**: KPI run tái lập (rule hash, contributions theo tác giả), reward workflow DRAFT→…→APPROVED→PAID; UI `/kpi`.
- Tests: 34 pass · 19 route frontend.

---


## ✅ Đã hoàn thành & kiểm thử
| Epic | Hạng mục | Trạng thái |
|---|---|---|
| E1 | Monorepo, Docker Compose, Postgres+pgvector, health, CI, docs | ✅ |
| E2 | Identity & RBAC (system/unit/profile roles, scope), JWT auth, audit | ✅ |
| E3 | Organization units, researcher profiles, identifiers, expertise, CV | ✅ |
| E4 | Funding programs & calls, eligibility rules, publish theo version | ✅ |
| E5 | Proposal workspace, team/workplan/deliverables/budget, validate, submit (snapshot) | ✅ |
| E6 | Reviewer pool, COI, AI matching, assignment, scorecard, council, decision | ✅ |
| E7 | Project lifecycle: activation, baseline, tasks, progress, change, risk, finance, closure | ✅ |
| E8 | Outputs/publications, authors, identifiers (DOI), venue, duplicate, verification | ✅ |
| E9 | Document platform: storage abstraction, signed URL, scan hook, extraction, chunks, search | ✅ |
| E10 | AI foundation: LLM/Embedding providers, prompt contract, jobs, RAG citations, usage ledger | ✅ |
| E11 | AI features: completeness, consistency, summary, classification, duplicate, profile summary | ✅ |
| E12 | Workflow tasks/notifications/comments, dashboards, report definitions | ✅ |
| AI Admin | Quản trị AI: nạp/đổi API key (mã hoá DB), chọn model/chế độ, test kết nối, usage (token/chi phí), kill-switch tính năng | ✅ |
| — | Frontend Next.js (13 màn hình chính, role-based nav, AI panel, Cấu hình AI) | ✅ |

**Kiểm thử:** 19 pytest (auth, RBAC, proposal flow, AI human-in-the-loop, documents/RAG) — pass.
Verified qua HTTP thật + TestClient. Frontend build (15 routes) pass.

## 🔶 Khung đã có, cần mở rộng cho production
- **Finance (M8)**: mới ở mức snapshot/transaction quản trị; chưa đồng bộ ERP 2 chiều.
- **IP/Transfer (M10), Ethics (M11), KPI/Reward (M12)**: enums + chỗ mở rộng; chưa có workflow đầy đủ.
- **Integrations (M17)**: ORCID/Crossref/HR/Library connectors — interface sẵn sàng, chưa nối thật.
- **External portal (M18)**: chưa làm (ngoài MVP).
- **Reports (M16)**: report_definitions + dashboards có; render Word/PDF/Excel + snapshot freeze chưa.
- **Storage MinIO/GCS**: driver local hoàn chỉnh; MinIO/GCS có chỗ cắm signed URL thật.
- **AI provider/key**: admin nạp & quản lý API key qua UI (mã hoá Fernet trong DB), chọn model + chế độ AUTO/CLAUDE/MOCK, test kết nối, theo dõi token/chi phí. Vertex là chỗ cắm.
- **Alembic**: 1 migration khởi tạo; production dùng expand-and-contract cho thay đổi sau.

## ⬜ Chưa làm (E13–E14, giai đoạn sau)
- Terraform/GCP IaC, Cloud Build/Run/SQL/Tasks/Secrets wiring, monitoring/backup runbooks.
- SSO/MFA (Identity Platform/OIDC) — code có chỗ cắm `AUTH_PROVIDER=oidc`.
- E2E browser tests, performance/security hardening, pilot data migration.

## Nguyên tắc đã tuân thủ
- Human-in-the-loop (AI luôn DRAFT/suggestion, người duyệt).
- RBAC + entity scope enforce ở backend **và** AI retrieval (RAG lọc quyền trước).
- Không lưu file gốc trong DB; audit append-only; không commit secret.
- Abstractions (Storage/TaskQueue/LLM/Embedding) để đổi nhà cung cấp không sửa nghiệp vụ.
