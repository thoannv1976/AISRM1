# 06 — AI Features Specification

> Bản đầy đủ: `source/AISRM1_full_specification.txt` (Phần F). Hiện thực: `apps/api/app/ai/`.

## Nguyên tắc
Grounded · Human approval · Least privilege · No fabrication · Privacy ·
Explainability · Reproducibility · Evaluated · Cost controlled · Secure by design.

## Tính năng (ưu tiên 1 = MVP)
AI-01 Trích xuất tài liệu · AI-02 Tóm tắt hồ sơ · AI-03 Kiểm tra đầy đủ ·
AI-04 Rà soát nhất quán proposal · AI-05 Phân loại lĩnh vực/SDG · AI-06 Reviewer matching ·
AI-08 Tóm tắt phản biện · AI-09 Draft biên bản hội đồng · AI-11 Trích xuất metadata công bố ·
AI-12 Phát hiện trùng lặp · AI-15 Research profile summarization · AI-18 RAG hỏi đáp nội bộ ·
AI-19 Draft báo cáo · AI-20 Data quality copilot · AI-25 Bilingual translation/editing.

## Kiến trúc RAG
Ingestion: document available → extract → normalize → structural chunk → access-scope hash → embedding → vector index.
Retrieval: user+scope → metadata filters FIRST → hybrid (keyword+vector) → rerank → context pack → LLM with citation schema → output validation → citations → audit/usage.
Critical filters: organization_id, entity, classification, document_status, access_grant, valid_from/to, version_is_current, user/role/unit scope.

## Output schema (JSON, mọi finding có citation_ids)
```json
{"summary":"string","findings":[{"code":"...","severity":"LOW|MEDIUM|HIGH","statement":"...","evidence":["citation-id"],"suggestion":"..."}],"insufficient_evidence":false,"limitations":["..."]}
```

## Bị cấm
Tự phê duyệt/quyết định; tạo số liệu/DOI/xếp hạng không nguồn; truy hồi ngoài scope;
tự gửi email/ký/đăng; tư vấn pháp lý chính thức; sửa hồ sơ gốc (chỉ tạo suggestion/diff).
