# 01 — Product Requirements (PRD)

> Bản đầy đủ: `source/AISRM1_full_specification.txt` (Phần A).

## Mục tiêu sản phẩm
Một nguồn dữ liệu tin cậy (single source of truth) cho đề tài, nhà nghiên cứu,
công bố, sản phẩm, tài trợ, SHTT và đối tác; số hóa end-to-end; ra quyết định
dựa trên dữ liệu; giảm công việc lặp lại; AI có trách nhiệm (có nguồn, có phê duyệt).

## Personas
Ban Giám hiệu/Hội đồng trường · Lãnh đạo & chuyên viên Phòng QLKH · Khoa/Viện/Bộ môn ·
Nhà nghiên cứu/PI · Thành viên đề tài · Phản biện/Hội đồng · Tài chính · Nhân sự ·
Thư viện · Đơn vị SHTT/chuyển giao · Quản trị hệ thống · Đối tác/cơ quan tài trợ.

## Yêu cầu phi chức năng (tóm tắt)
- **Hiệu năng**: P95 API đọc < 800ms; trang chính < 2.5s; tác vụ AI/tài liệu bất đồng bộ.
- **Bảo mật**: SSO/MFA (prod), RBAC + scope, TLS, secret manager, malware scan, signed URL.
- **Riêng tư**: phân loại Public/Internal/Confidential/Restricted; mục đích & thời hạn lưu rõ.
- **Audit**: ghi tạo/sửa/xóa/xem/tải/phê duyệt/xuất/AI; log không sửa được.
- **Khả dụng**: mục tiêu ≥ 99.5% sau pilot; health check, graceful shutdown.
- **Đa ngôn ngữ**: UI/email/biểu mẫu Việt/Anh; Unicode đầy đủ.

## Nguyên tắc thiết kế
Human-in-the-loop · Single Source of Truth · Configurable workflow ·
Traceability by default · Security/privacy by design · API-first ·
Modular monolith first · Cloud-ready/portable · Evidence-grounded AI · Accessibility & bilingual.
