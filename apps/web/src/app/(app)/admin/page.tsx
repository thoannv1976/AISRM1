"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { EmptyState, PageHeader, Spinner } from "@/components/ui";
import type { Page } from "@/lib/types";

interface Audit {
  id: string;
  occurred_at: string;
  actor_email?: string | null;
  action: string;
  entity_type?: string | null;
}
interface Feature {
  id: string;
  code: string;
  name: string;
  risk_level: string;
  enabled: boolean;
  requires_citations: boolean;
}

export default function AdminPage() {
  const { can } = useAuth();
  const [audit, setAudit] = useState<Page<Audit> | null>(null);
  const [features, setFeatures] = useState<Feature[]>([]);

  useEffect(() => {
    if (can("audit.read")) api.get<Page<Audit>>("/audit-logs?limit=30").then(setAudit);
    if (can("ai.run")) api.get<Feature[]>("/ai/features").then(setFeatures).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <PageHeader title="Quản trị & Audit" subtitle="Cấu hình AI, nhật ký kiểm toán append-only" />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div>
          <h3 className="mb-2 font-semibold text-slate-800">Tính năng AI</h3>
          {features.length === 0 ? (
            <EmptyState message="Không có dữ liệu tính năng AI." />
          ) : (
            <div className="card divide-y divide-slate-100">
              {features.map((f) => (
                <div key={f.id} className="flex items-center justify-between p-3">
                  <div>
                    <div className="text-sm font-medium text-slate-800">{f.name}</div>
                    <div className="text-xs text-slate-400">
                      {f.code} · rủi ro {f.risk_level}
                      {f.requires_citations && " · yêu cầu trích nguồn"}
                    </div>
                  </div>
                  <span className={`badge ${f.enabled ? "bg-green-100 text-green-700" : "bg-slate-200 text-slate-500"}`}>
                    {f.enabled ? "Bật" : "Tắt"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div>
          <h3 className="mb-2 font-semibold text-slate-800">Nhật ký kiểm toán</h3>
          {!audit ? (
            <Spinner />
          ) : (
            <div className="card max-h-[60vh] overflow-y-auto">
              <table className="w-full">
                <thead className="sticky top-0 border-b bg-slate-50">
                  <tr>
                    <th className="th">Thời gian</th>
                    <th className="th">Hành động</th>
                    <th className="th">Người dùng</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {audit.items.map((a) => (
                    <tr key={a.id}>
                      <td className="td text-xs">{new Date(a.occurred_at).toLocaleString("vi-VN")}</td>
                      <td className="td font-mono text-xs">{a.action}</td>
                      <td className="td text-xs">{a.actor_email || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
