"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { EmptyState, PageHeader, Spinner, StatusBadge, formatMoney } from "@/components/ui";
import type { Call, Page } from "@/lib/types";

export default function CallsPage() {
  const { can } = useAuth();
  const [data, setData] = useState<Page<Call> | null>(null);
  const [msg, setMsg] = useState("");

  async function load() {
    setData(await api.get<Page<Call>>("/funding-calls?limit=50"));
  }
  useEffect(() => {
    load();
  }, []);

  async function createDemo() {
    const code = "CALL-" + Date.now().toString().slice(-5);
    try {
      await api.post("/funding-calls", {
        code,
        title: "Đợt mời nộp mới " + code,
        task_level: "INSTITUTIONAL",
        required_documents: ["proposal_form"],
      });
      setMsg("Đã tạo call " + code);
      load();
    } catch (e: any) {
      setMsg("⚠ " + e.message);
    }
  }
  async function publish(id: string) {
    await api.post(`/funding-calls/${id}/publish`);
    load();
  }

  return (
    <div>
      <PageHeader
        title="Chương trình tài trợ & Đợt mời nộp"
        subtitle="Cấu hình call, điều kiện và công bố theo phiên bản"
        actions={can("calls.create") ? <button className="btn-primary" onClick={createDemo}>+ Tạo call</button> : undefined}
      />
      {msg && <div className="mb-3 rounded bg-slate-100 px-3 py-2 text-sm">{msg}</div>}
      {!data ? (
        <Spinner />
      ) : data.items.length === 0 ? (
        <EmptyState message="Chưa có call nào." />
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead className="border-b bg-slate-50">
              <tr>
                <th className="th">Mã</th>
                <th className="th">Tên</th>
                <th className="th">Trạng thái</th>
                <th className="th">Hạn nộp</th>
                <th className="th">Ngân sách</th>
                <th className="th"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.items.map((c) => (
                <tr key={c.id} className="hover:bg-slate-50">
                  <td className="td font-mono text-xs">{c.code}</td>
                  <td className="td">{c.title}</td>
                  <td className="td"><StatusBadge status={c.status} /></td>
                  <td className="td text-xs">{c.close_at ? new Date(c.close_at).toLocaleDateString("vi-VN") : "—"}</td>
                  <td className="td">{c.budget_limit ? formatMoney(c.budget_limit, c.currency) : "—"}</td>
                  <td className="td">
                    {can("calls.update") && c.status !== "PUBLISHED" && (
                      <button className="text-xs text-brand-600 hover:underline" onClick={() => publish(c.id)}>
                        Công bố
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
