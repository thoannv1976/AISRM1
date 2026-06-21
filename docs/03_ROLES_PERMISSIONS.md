# 03 — Vai trò & Phân quyền (Roles & Permissions)

## Vai trò hệ thống
`SYSTEM_ADMIN`, `RESEARCH_OFFICE_ADMIN`, `RESEARCH_OFFICER`, `EXECUTIVE`, `AUDITOR`

## Vai trò theo đơn vị
`UNIT_HEAD`, `UNIT_RESEARCH_COORDINATOR`, `DEPARTMENT_HEAD`

## Vai trò theo hồ sơ
`PI`, `PROJECT_MEMBER`, `PROPOSAL_EDITOR`, `REVIEWER`, `COUNCIL_CHAIR`,
`COUNCIL_SECRETARY`, `ETHICS_REVIEWER`, `FINANCE_VIEWER`

## Scope (ABAC)
Mỗi quyền được đánh giá theo: `organization_id`, `unit_id`, `call_id`,
`proposal_id`, `project_id`, `document_classification`, và `permission action`.

## Quy tắc
- **Deny by default** — không có endpoint nghiệp vụ nào bỏ qua permission dependency.
- AI/RAG dùng **cùng access scope** với người dùng; không truy hồi chunk ngoài quyền.
- Ủy quyền tạm thời (delegation) có ngày bắt đầu/kết thúc và lý do; không tự ủy quyền quyền cao hơn.
- Audit: đăng nhập, thất bại, đổi vai trò, cấp quyền, tải file, truy cập hồ sơ hạn chế.

## Permission actions (mẫu)
`*.read`, `*.create`, `*.update`, `*.delete`, `*.submit`, `*.approve`,
`*.assign`, `*.verify`, `*.export`, `ai.run`, `admin.config`, `audit.read`

## RACI rút gọn
| Hoạt động | Phòng QLKH | Lãnh đạo QLKH | PI/Khoa | Reviewer/HĐ | BGH/Tài chính |
|---|---|---|---|---|---|
| Cấu hình call | R | A | C | C | I |
| Kiểm tra hồ sơ | R | A | C | - | I |
| Phân công reviewer | R | A | C | C | I |
| Chấm phản biện | - | I | - | R | I |
| Quyết định tài trợ | C | C | C | C | A |
| Báo cáo tiến độ | C | I | R/A | - | I |
| Xác minh công bố | R | A | R | C | I |
| Nghiệm thu | R | C | C | R | A |
| Phê duyệt AI output nhạy cảm | R | A | C | - | I |

R = Responsible · A = Accountable · C = Consulted · I = Informed
