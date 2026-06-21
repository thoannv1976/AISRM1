"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { EmptyState, PageHeader, Spinner, StatusBadge } from "@/components/ui";
import type { Page } from "@/lib/types";

interface Doc {
  id: string;
  title: string;
  document_type: string;
  classification: string;
  status: string;
}

export default function DocumentsPage() {
  const [data, setData] = useState<Page<Doc> | null>(null);
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<{ document_id: string; title: string; snippet?: string | null }[] | null>(null);

  async function load() {
    setData(await api.get<Page<Doc>>("/documents?limit=50"));
  }
  useEffect(() => {
    load();
  }, []);

  async function search() {
    if (q.length < 2) return;
    const r = await api.get<{ hits: any[] }>(`/documents/search?q=${encodeURIComponent(q)}`);
    setHits(r.hits);
  }

  return (
    <div>
      <PageHeader title="Kho tài liệu" subtitle="Lưu trữ có phân loại, version, trích xuất & tìm kiếm toàn văn" />
      <div className="mb-4 flex gap-2">
        <input
          className="input max-w-md"
          placeholder="Tìm trong nội dung tài liệu..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && search()}
        />
        <button className="btn-ghost" onClick={search}>Tìm toàn văn</button>
      </div>

      {hits && (
        <div className="card mb-4 p-4">
          <h3 className="mb-2 text-sm font-semibold">Kết quả tìm kiếm ({hits.length})</h3>
          {hits.length === 0 && <div className="text-sm text-slate-400">Không có kết quả.</div>}
          {hits.map((h) => (
            <div key={h.document_id} className="border-b border-slate-50 py-2 text-sm">
              <div className="font-medium text-slate-800">{h.title}</div>
              {h.snippet && <div className="text-xs text-slate-500">...{h.snippet}...</div>}
            </div>
          ))}
        </div>
      )}

      {!data ? (
        <Spinner />
      ) : data.items.length === 0 ? (
        <EmptyState message="Chưa có tài liệu nào trong kho." />
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead className="border-b bg-slate-50">
              <tr>
                <th className="th">Tiêu đề</th>
                <th className="th">Loại</th>
                <th className="th">Phân loại</th>
                <th className="th">Trạng thái</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.items.map((d) => (
                <tr key={d.id} className="hover:bg-slate-50">
                  <td className="td">{d.title}</td>
                  <td className="td text-xs">{d.document_type}</td>
                  <td className="td"><span className="badge bg-slate-100 text-slate-600">{d.classification}</span></td>
                  <td className="td"><StatusBadge status={d.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
