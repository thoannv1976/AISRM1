"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { EmptyState, PageHeader, Spinner, StatusBadge, formatMoney } from "@/components/ui";
import type { Page, Project } from "@/lib/types";

export default function ProjectsPage() {
  const [data, setData] = useState<Page<Project> | null>(null);

  useEffect(() => {
    api.get<Page<Project>>("/projects?limit=50").then(setData);
  }, []);

  return (
    <div>
      <PageHeader title="Đề tài đang quản lý" subtitle="Vòng đời thực hiện, tiến độ, kinh phí, nghiệm thu" />
      {!data ? (
        <Spinner />
      ) : data.items.length === 0 ? (
        <EmptyState message="Chưa có đề tài. Kích hoạt từ một đề xuất đã được duyệt." />
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {data.items.map((p) => (
            <div key={p.id} className="card p-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-mono text-xs text-slate-400">{p.project_code}</div>
                  <div className="font-medium text-slate-900">{p.title}</div>
                </div>
                <StatusBadge status={p.status} />
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
                <div>
                  <div className="text-xs text-slate-400">Kinh phí</div>
                  <div>{formatMoney(p.approved_budget, p.currency)}</div>
                </div>
                <div>
                  <div className="text-xs text-slate-400">Tiến độ</div>
                  <div className="mt-1 h-2 rounded bg-slate-100">
                    <div
                      className="h-2 rounded bg-green-500"
                      style={{ width: `${Number(p.completion_percent) || 0}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
