"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { EmptyState, PageHeader, Spinner, StatusBadge } from "@/components/ui";
import type { Page, ResearchOutput } from "@/lib/types";

export default function OutputsPage() {
  const { can } = useAuth();
  const [data, setData] = useState<Page<ResearchOutput> | null>(null);
  const [msg, setMsg] = useState("");

  async function load() {
    setData(await api.get<Page<ResearchOutput>>("/research-outputs?limit=50"));
  }
  useEffect(() => {
    load();
  }, []);

  async function verify(id: string) {
    setMsg("");
    try {
      await api.post(`/research-outputs/${id}/verify`, { step: "OFFICE", decision: "APPROVED" });
      setMsg("Đã xác minh công bố");
      load();
    } catch (e: any) {
      setMsg("⚠ " + e.message);
    }
  }

  return (
    <div>
      <PageHeader title="Công bố & Sản phẩm khoa học" subtitle="Chuẩn hóa metadata, DOI, chống trùng, xác minh" />
      {msg && <div className="mb-3 rounded bg-slate-100 px-3 py-2 text-sm">{msg}</div>}
      {!data ? (
        <Spinner />
      ) : data.items.length === 0 ? (
        <EmptyState message="Chưa có sản phẩm nào." />
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead className="border-b bg-slate-50">
              <tr>
                <th className="th">Tiêu đề</th>
                <th className="th">Loại</th>
                <th className="th">Năm</th>
                <th className="th">DOI</th>
                <th className="th">Xác minh</th>
                <th className="th"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.items.map((o) => (
                <tr key={o.id} className="hover:bg-slate-50">
                  <td className="td max-w-md">{o.title}</td>
                  <td className="td text-xs">{o.output_type}</td>
                  <td className="td">{o.year || "—"}</td>
                  <td className="td font-mono text-xs">{o.doi || "—"}</td>
                  <td className="td"><StatusBadge status={o.verification_status} /></td>
                  <td className="td">
                    {can("outputs.verify") && o.verification_status !== "VERIFIED" && (
                      <button className="text-xs text-brand-600 hover:underline" onClick={() => verify(o.id)}>
                        Xác minh
                      </button>
                    )}
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
