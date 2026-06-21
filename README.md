# AISRM1 — AI-ResearchHub

**Hệ thống Quản lý Nghiên cứu Khoa học, Công bố và Đổi mới sáng tạo tích hợp AI**
_AI-integrated Scientific Research Management System for a university Research Management Office._

> Nguyên tắc cốt lõi: **AI hỗ trợ — con người quyết định** (human-in-the-loop).
> Mọi kết quả AI là *gợi ý/bản nháp* có nguồn, có mức tin cậy, được người có thẩm quyền phê duyệt.

---

## 1. Tính năng chính

| Phân hệ | Mô tả |
|---|---|
| **Identity & RBAC** | Đăng nhập (local/JWT, sẵn sàng SSO/OIDC), vai trò hệ thống/đơn vị/hồ sơ, scope theo đơn vị & thực thể, audit log |
| **Tổ chức & Người dùng** | Cây đơn vị có lịch sử, nhóm nghiên cứu, tài khoản |
| **Hồ sơ nhà nghiên cứu** | CV 360°, ORCID/Scopus/WoS, expertise taxonomy, mạng lưới, xuất CV |
| **Tài trợ & Đợt mời nộp** | Program, call, form builder, eligibility rules, publish theo version |
| **Đề xuất nghiên cứu** | Workspace cộng tác, team, workplan/milestones/deliverables, ngân sách, validate & submit (snapshot bất biến) |
| **Phản biện & Hội đồng** | Reviewer pool, COI, AI matching, scorecard, hội đồng, biểu quyết, quyết định |
| **Quản lý đề tài** | Activation, baseline, tasks, progress report, change request, risk, deliverable, nghiệm thu |
| **Sản phẩm & Công bố** | Output/publication, author order, DOI/identifiers, venue registry, duplicate detection, verification |
| **Kho tài liệu** | Upload (signed URL), version, classification, scan hook, OCR/extraction, full-text + semantic search |
| **AI Research Copilot** | Tóm tắt, kiểm tra đầy đủ/nhất quán, reviewer matching, trích xuất metadata, RAG có citations |
| **Workflow & Thông báo** | Generic workflow/tasks/approvals, inbox, notifications |
| **Dashboard & Báo cáo** | Executive / research office / unit / researcher dashboards, report catalog, export snapshot |

## 2. Kiến trúc

```
Người dùng / SSO ──HTTPS──► Next.js (web) ──REST/OpenAPI──► FastAPI (api)
                                                              ├─ PostgreSQL + pgvector
                                                              ├─ Object Storage (MinIO/GCS)
                                                              ├─ Task Queue (Redis/Cloud Tasks) ─► Worker
                                                              └─ LLM/Embedding Provider (mock/Anthropic/Vertex)
```

- **Modular monolith** — `apps/api` chia module rõ ràng, dễ tách service sau.
- **Storage 3 lớp**: file gốc (object storage) · metadata nghiệp vụ (Postgres) · dữ liệu AI (Postgres + pgvector).
- **Abstractions**: `StorageService`, `TaskQueue`, `LLMProvider`, `EmbeddingProvider` → đổi nhà cung cấp không sửa nghiệp vụ.

## 3. Công nghệ

| Lớp | Công nghệ |
|---|---|
| Frontend | Next.js 15 (App Router), React, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python, Pydantic v2, SQLAlchemy 2, Alembic |
| Database | PostgreSQL 16 + pgvector |
| Storage | MinIO (local) / Google Cloud Storage (prod) |
| Async | Redis worker (local) / Cloud Tasks + Cloud Run worker (prod) |
| AI | LLMProvider / EmbeddingProvider (mock · Anthropic · Vertex AI) |
| Hạ tầng | Docker Compose (local) · Cloud Run / Cloud SQL / GCS (prod) |

## 4. Chạy nhanh (local)

### Cách A — Docker Compose (khuyến nghị)
```bash
cp .env.example .env
docker compose up --build
# API docs:  http://localhost:8000/docs
# Web:       http://localhost:3000
```

### Cách B — chạy trực tiếp (đã có Postgres+pgvector)
```bash
# Backend
cd apps/api
pip install -e ".[dev]"
export DATABASE_URL="postgresql+psycopg://aisrm1:aisrm1@127.0.0.1:5432/aisrm1"
python -m app.cli migrate
python -m app.cli seed --demo
uvicorn app.main:app --reload

# Frontend (terminal khác)
cd apps/web
npm install
npm run dev
```

**Tài khoản demo (chỉ dùng local):**
| Vai trò | Email | Mật khẩu |
|---|---|---|
| System Admin | `admin@aisrm1.edu.vn` | `Admin@12345` |
| Research Officer | `officer@aisrm1.edu.vn` | `Officer@12345` |
| Researcher (PI) | `pi@aisrm1.edu.vn` | `Researcher@12345` |
| Reviewer | `reviewer@aisrm1.edu.vn` | `Reviewer@12345` |
| Executive | `exec@aisrm1.edu.vn` | `Exec@12345` |

## 5. Cấu trúc repository

```
apps/
  api/      # FastAPI backend (modular monolith)
  web/      # Next.js frontend
  worker/   # background document/AI tasks
packages/shared/   # shared enums/types
infra/docker/      # Dockerfiles
docs/              # đặc tả (PRD, schema, API, AI, screens, reports, roadmap)
scripts/           # init_db, helpers
.github/workflows/ # CI
```

## 6. Tài liệu
Xem thư mục [`docs/`](docs/): `01_PRD.md`, `02_MVP_SCOPE.md`, `03_ROLES_PERMISSIONS.md`,
`04_DATABASE_SCHEMA.md`, `05_API_SPEC.md`, `06_AI_FEATURES_SPEC.md`,
`07_UI_SCREEN_LIST.md`, `08_REPORT_LIST.md`, `09_DEPLOYMENT_GUIDE.md`,
`10_ROADMAP_EPICS.md`. Bản đặc tả gốc đầy đủ ở `docs/source/`.

## 7. Bảo mật & tuân thủ
- RBAC + scope theo đơn vị/thực thể enforce ở backend **và** AI retrieval.
- Không lưu file gốc trong DB; không commit secret/PII; audit append-only.
- AI: suggestion-only, có citations, không gửi dữ liệu Restricted tới provider chưa duyệt.

## 8. Giấy phép
Nội bộ / phục vụ triển khai cho Phòng Quản lý khoa học. Xem `docs/` để biết phạm vi.
