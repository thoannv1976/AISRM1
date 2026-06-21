"""Document upload pipeline + permission-scoped RAG."""
from urllib.parse import urlparse

from tests.conftest import auth

P = "/api/v1"
SAMPLE = (
    "Báo cáo nghiên cứu về ứng dụng trí tuệ nhân tạo trong quản lý khoa học. "
    "Hệ thống AISRM1 hỗ trợ tóm tắt hồ sơ và phát hiện trùng lặp công bố."
).encode("utf-8")


def _upload(client, token, *, title="Tài liệu test", filename="bao_cao.txt"):
    sess = client.post(
        f"{P}/documents/upload-sessions",
        headers=auth(token),
        json={"title": title, "filename": filename, "mime_type": "text/plain",
              "classification": "INTERNAL", "entity_type": "proposal"},
    ).json()
    path = urlparse(sess["upload_url"]).path  # /api/v1/documents/_storage/<token>
    r = client.put(path, headers=auth(token), content=SAMPLE)
    assert r.status_code == 200, r.text
    done = client.post(f"{P}/documents/{sess['document_id']}/complete-upload",
                       headers=auth(token), json={"sha256": r.json()["sha256"]})
    assert done.status_code == 200, done.text
    return sess["document_id"]


def test_upload_extract_and_search(client, officer_token):
    doc_id = _upload(client, officer_token)
    versions = client.get(f"{P}/documents/{doc_id}/versions", headers=auth(officer_token)).json()
    assert versions[0]["scan_status"] == "CLEAN"
    assert versions[0]["extraction_status"] == "DONE"

    res = client.get(f"{P}/documents/search", headers=auth(officer_token),
                     params={"q": "trí tuệ nhân tạo"}).json()
    assert any(h["document_id"] == doc_id for h in res["hits"])


def test_rag_chat_uses_uploaded_docs(client, officer_token):
    _upload(client, officer_token, title="RAG source")
    r = client.post(f"{P}/ai/chat", headers=auth(officer_token),
                    json={"message": "AISRM1 hỗ trợ gì cho quản lý khoa học?"}).json()
    # Now there is indexed content -> answer should carry citations.
    assert r["citations"], "RAG answer must include citations when sources exist"


def test_download_url_signed(client, officer_token):
    doc_id = _upload(client, officer_token)
    r = client.get(f"{P}/documents/{doc_id}/download-url", headers=auth(officer_token)).json()
    assert "sig=" in r["url"] and "exp=" in r["url"]
