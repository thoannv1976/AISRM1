"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { EmptyState, PageHeader, Spinner } from "@/components/ui";
import type { Page, Researcher } from "@/lib/types";

export default function ResearchersPage() {
  const [data, setData] = useState<Page<Researcher> | null>(null);
  const [q, setQ] = useState("");

  async function load(query = "") {
    setData(await api.get<Page<Researcher>>(`/researchers?limit=50${query ? `&q=${encodeURIComponent(query)}` : ""}`));
  }
  useEffect(() => {
    load();
  }, []);

  return (
    <div>
      <PageHeader title="Nhà nghiên cứu" subtitle="Hồ sơ năng lực 360°, chuyên môn, định danh" />
      <div className="mb-4 flex gap-2">
        <input
          className="input max-w-xs"
          placeholder="Tìm theo tên..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && load(q)}
        />
        <button className="btn-ghost" onClick={() => load(q)}>Tìm</button>
      </div>
      {!data ? (
        <Spinner />
      ) : data.items.length === 0 ? (
        <EmptyState message="Không tìm thấy nhà nghiên cứu." />
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          {data.items.map((r) => (
            <div key={r.id} className="card p-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-100 font-semibold text-brand-700">
                  {r.full_name.charAt(0)}
                </div>
                <div>
                  <div className="font-medium text-slate-900">{r.full_name}</div>
                  <div className="text-xs text-slate-500">
                    {[r.academic_title, r.degree].filter(Boolean).join(" · ") || "—"}
                  </div>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-1">
                {(r.keywords || []).slice(0, 5).map((k) => (
                  <span key={k} className="badge bg-slate-100 text-slate-600">{k}</span>
                ))}
              </div>
              {r.h_index != null && (
                <div className="mt-2 text-xs text-slate-500">h-index: {r.h_index}</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
