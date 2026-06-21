"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { PageHeader, Spinner, Stat, formatMoney } from "@/components/ui";

interface Dash {
  metrics: Record<string, number>;
  proposals_by_status: Record<string, number>;
  projects_by_status: Record<string, number>;
  outputs_by_type: Record<string, number>;
  outputs_by_year: Record<string, number>;
}

function Breakdown({ title, data }: { title: string; data: Record<string, number> }) {
  const entries = Object.entries(data || {}).sort((a, b) => b[1] - a[1]);
  const max = Math.max(1, ...entries.map((e) => e[1]));
  return (
    <div className="card p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-700">{title}</h3>
      {entries.length === 0 && <div className="text-sm text-slate-400">Chưa có dữ liệu</div>}
      <div className="space-y-2">
        {entries.map(([k, v]) => (
          <div key={k}>
            <div className="flex justify-between text-xs text-slate-600">
              <span>{k}</span>
              <span className="font-medium">{v}</span>
            </div>
            <div className="mt-0.5 h-2 rounded bg-slate-100">
              <div className="h-2 rounded bg-brand-500" style={{ width: `${(v / max) * 100}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { me } = useAuth();
  const [data, setData] = useState<Dash | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api
      .get<Dash>("/dashboards/executive")
      .then(setData)
      .catch((e) => setErr(e.message));
  }, []);

  if (err) return <div className="rounded bg-red-50 p-4 text-sm text-red-700">{err}</div>;
  if (!data) return <Spinner />;
  const m = data.metrics;

  return (
    <div>
      <PageHeader
        title={`Xin chào, ${me?.user.display_name}`}
        subtitle="Tổng quan hoạt động khoa học & công nghệ toàn trường"
      />
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat label="Nhà nghiên cứu" value={m.researchers} />
        <Stat label="Đề xuất" value={m.proposals} />
        <Stat label="Đề tài đang thực hiện" value={m.projects_active} hint={`Tổng: ${m.projects_total}`} />
        <Stat label="Công bố" value={m.outputs} hint={`Đã xác minh: ${m.outputs_verified}`} />
      </div>
      <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
        <Stat label="Tổng kinh phí phê duyệt" value={formatMoney(m.total_budget)} />
        <Stat label="Đã giải ngân (quản trị)" value={formatMoney(m.disbursed)} hint="ERP là nguồn chuẩn" />
      </div>
      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
        <Breakdown title="Đề xuất theo trạng thái" data={data.proposals_by_status} />
        <Breakdown title="Đề tài theo trạng thái" data={data.projects_by_status} />
        <Breakdown title="Công bố theo loại" data={data.outputs_by_type} />
        <Breakdown title="Công bố theo năm" data={data.outputs_by_year} />
      </div>
    </div>
  );
}
