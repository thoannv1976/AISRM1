"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { EmptyState, PageHeader, Spinner, StatusBadge } from "@/components/ui";
import type { Page } from "@/lib/types";

interface Ethics {
  id: string;
  code: string;
  title: string;
  review_type: string;
  risk_level: string;
  status: string;
  classification: string;
  valid_to?: string | null;
}

export default function EthicsPage() {
  const { can } = useAuth();
  const [data, setData] = useState<Page<Ethics> | null>(null);
  const [title, setTitle] = useState("");
  const [msg, setMsg] = useState("");

  async function load() {
    setData(await api.get<Page<Ethics>>("/ethics?limit=50"));
  }
  useEffect(() => {
    load();
  }, []);

  async function act(fn: () => Promise<any>, ok: string) {
    setMsg("");
    try {
      await fn();
      setMsg(ok);
      load();
    } catch (e: any) {
      setMsg("⚠ " + e.message);
    }
  }

  return (
    <div>
      <PageHeader
        title="Đạo đức & Liêm chính nghiên cứu"
        subtitle="Hồ sơ Restricted; AI không tự quyết định. Quy trình thẩm định human-in-the-loop"
      />
      {msg && <div className="mb-3 rounded bg-slate-100 px-3 py-2 text-sm">{msg}</div>}

      {can("ethics.create") && (
        <div className="card mb-4 flex gap-2 p-3">
          <input
            className="input"
            placeholder="Tên hồ sơ đạo đức..."
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <button
            className="btn-primary shrink-0"
            disabled={!title}
            onClick={() =>
              act(async () => {
                await api.post("/ethics", { title, review_type: "FULL", involves_human_subjects: true });
                setTitle("");
              }, "Đã tạo hồ sơ đạo đức")
            }
          >
            + Tạo hồ sơ
          </button>
        </div>
      )}

      {!data ? (
        <Spinner />
      ) : data.items.length === 0 ? (
        <EmptyState message="Chưa có hồ sơ đạo đức." />
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead className="border-b bg-slate-50">
              <tr>
                <th className="th">Mã</th>
                <th className="th">Tên</th>
                <th className="th">Loại</th>
                <th className="th">Trạng thái</th>
                <th className="th">Hiệu lực đến</th>
                <th className="th">Hành động</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.items.map((a) => (
                <tr key={a.id} className="hover:bg-slate-50">
                  <td className="td font-mono text-xs">{a.code}</td>
                  <td className="td">{a.title}</td>
                  <td className="td text-xs">{a.review_type}</td>
                  <td className="td"><StatusBadge status={a.status} /></td>
                  <td className="td text-xs">{a.valid_to || "—"}</td>
                  <td className="td">
                    <div className="flex gap-2 text-xs">
                      {a.status === "DRAFT" && can("ethics.update") && (
                        <button className="text-brand-600 hover:underline"
                                onClick={() => act(() => api.post(`/ethics/${a.id}/submit`), "Đã nộp")}>
                          Nộp
                        </button>
                      )}
                      {a.status === "SUBMITTED" && can("ethics.update") && (
                        <button className="text-brand-600 hover:underline"
                                onClick={() => act(() => api.post(`/ethics/${a.id}/screen?review_type=FULL`), "Đã chuyển thẩm định")}>
                          Phân loại
                        </button>
                      )}
                      {a.status === "UNDER_REVIEW" && can("ethics.decide") && (
                        <>
                          <button className="text-green-700 hover:underline"
                                  onClick={() => act(() => api.post(`/ethics/${a.id}/decision`, { outcome: "APPROVED", valid_months: 12 }), "Đã duyệt")}>
                            Duyệt
                          </button>
                          <button className="text-red-700 hover:underline"
                                  onClick={() => act(() => api.post(`/ethics/${a.id}/decision`, { outcome: "REJECTED" }), "Đã từ chối")}>
                            Từ chối
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
