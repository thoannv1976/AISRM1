"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { EmptyState, PageHeader, Spinner, StatusBadge, formatMoney } from "@/components/ui";

interface KPIRun {
  id: string;
  period: string;
  status: string;
  total_points: string | number;
  rule_hash?: string | null;
}
interface Contribution {
  researcher: string;
  points: number;
  outputs: number;
}
interface Reward {
  id: string;
  code: string;
  title: string;
  points: string | number;
  amount: string | number;
  currency: string;
  status: string;
}

const NEXT: Record<string, string> = {
  DRAFT: "SUBMITTED",
  SUBMITTED: "UNIT_CONFIRMED",
  UNIT_CONFIRMED: "OFFICE_REVIEWED",
  OFFICE_REVIEWED: "APPROVED",
  APPROVED: "PAID",
};

export default function KPIPage() {
  const { can } = useAuth();
  const [runs, setRuns] = useState<KPIRun[]>([]);
  const [contribs, setContribs] = useState<Contribution[] | null>(null);
  const [rewards, setRewards] = useState<Reward[]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  async function load() {
    setRuns((await api.get<{ items: KPIRun[] }>("/kpi-runs?limit=20")).items);
    setRewards((await api.get<{ items: Reward[] }>("/reward-applications?limit=50")).items);
  }
  useEffect(() => {
    load();
  }, []);

  async function runKPI() {
    setBusy(true);
    setMsg("");
    try {
      const r = await api.post<KPIRun>("/kpi-runs", { period: String(new Date().getFullYear()) });
      setMsg(`Đã chạy KPI · tổng điểm ${r.total_points}`);
      await load();
      viewRun(r.id);
    } catch (e: any) {
      setMsg("⚠ " + e.message);
    } finally {
      setBusy(false);
    }
  }

  async function viewRun(id: string) {
    const d = await api.get<{ contributions: Contribution[] }>(`/kpi-runs/${id}`);
    setContribs(d.contributions);
  }

  async function transition(r: Reward) {
    const target = NEXT[r.status];
    if (!target) return;
    try {
      await api.post(`/reward-applications/${r.id}/transition`, { target_status: target });
      load();
    } catch (e: any) {
      setMsg("⚠ " + e.message);
    }
  }

  return (
    <div>
      <PageHeader
        title="KPI & Khen thưởng nghiên cứu"
        subtitle="Tính KPI tái lập từ công bố đã xác minh; quy trình khen thưởng có phê duyệt"
        actions={
          can("kpi.run") ? (
            <button className="btn-primary" onClick={runKPI} disabled={busy}>
              {busy ? "Đang tính..." : "Chạy KPI kỳ này"}
            </button>
          ) : undefined
        }
      />
      {msg && <div className="mb-3 rounded bg-slate-100 px-3 py-2 text-sm">{msg}</div>}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div>
          <h3 className="mb-2 font-semibold text-slate-800">Lần chạy KPI</h3>
          {runs.length === 0 ? (
            <EmptyState message="Chưa có lần chạy KPI nào." />
          ) : (
            <div className="card divide-y divide-slate-100">
              {runs.map((r) => (
                <button
                  key={r.id}
                  onClick={() => viewRun(r.id)}
                  className="flex w-full items-center justify-between p-3 text-left hover:bg-slate-50"
                >
                  <div>
                    <div className="text-sm font-medium">Kỳ {r.period}</div>
                    <div className="text-xs text-slate-400">
                      {r.rule_hash?.slice(0, 18)}… · <StatusBadge status={r.status} />
                    </div>
                  </div>
                  <div className="text-sm font-semibold text-brand-700">{String(r.total_points)} đ</div>
                </button>
              ))}
            </div>
          )}

          {contribs && (
            <div className="card mt-4 p-4">
              <h4 className="mb-2 text-sm font-semibold">Đóng góp theo nhà nghiên cứu</h4>
              <table className="w-full">
                <thead>
                  <tr>
                    <th className="th">Nhà nghiên cứu</th>
                    <th className="th">Điểm</th>
                    <th className="th">Công bố</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {contribs.map((c, i) => (
                    <tr key={i}>
                      <td className="td">{c.researcher}</td>
                      <td className="td font-medium">{c.points}</td>
                      <td className="td">{c.outputs}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {contribs.length === 0 && (
                <div className="text-sm text-slate-400">Chưa có công bố verified để tính KPI.</div>
              )}
            </div>
          )}
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between">
            <h3 className="font-semibold text-slate-800">Đề nghị khen thưởng</h3>
            {can("rewards.create") && (
              <button
                className="btn-ghost text-xs"
                onClick={async () => {
                  const t = prompt("Tên đề nghị khen thưởng:");
                  if (t) {
                    await api.post("/reward-applications", { title: t, amount: "5000000" });
                    load();
                  }
                }}
              >
                + Tạo
              </button>
            )}
          </div>
          {rewards.length === 0 ? (
            <EmptyState message="Chưa có đề nghị khen thưởng." />
          ) : (
            <div className="card divide-y divide-slate-100">
              {rewards.map((r) => (
                <div key={r.id} className="flex items-center justify-between p-3">
                  <div>
                    <div className="text-sm font-medium">{r.title}</div>
                    <div className="text-xs text-slate-400">
                      {r.code} · {formatMoney(r.amount, r.currency)}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={r.status} />
                    {NEXT[r.status] && (can("rewards.update") || can("rewards.approve")) && (
                      <button className="text-xs text-brand-600 hover:underline" onClick={() => transition(r)}>
                        → {NEXT[r.status]}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
