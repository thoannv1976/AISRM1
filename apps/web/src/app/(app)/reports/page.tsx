"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { EmptyState, PageHeader, Spinner } from "@/components/ui";

interface ReportDef {
  code: string;
  name: string;
  category?: string | null;
  supported: boolean;
}
interface RunResult {
  id: string;
  report_code: string;
  snapshot: { title: string; columns: string[]; rows: any[][]; summary: Record<string, any> };
  snapshot_hash: string;
  generated_at: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export default function ReportsPage() {
  const [defs, setDefs] = useState<ReportDef[] | null>(null);
  const [run, setRun] = useState<RunResult | null>(null);
  const [busy, setBusy] = useState("");

  useEffect(() => {
    api.get<ReportDef[]>("/reports").then(setDefs);
  }, []);

  async function runReport(code: string) {
    setBusy(code);
    setRun(null);
    try {
      setRun(await api.post<RunResult>(`/reports/${code}/runs`));
    } finally {
      setBusy("");
    }
  }

  function exportUrl(fmt: string) {
    // Open signed/authorized export. Token is sent via query is not supported; use fetch+blob.
    return `${API_BASE}/api/v1/reports/runs/${run!.id}/export?format=${fmt}`;
  }

  async function download(fmt: string) {
    if (!run) return;
    const token = localStorage.getItem("aisrm1_token");
    const res = await fetch(exportUrl(fmt), { headers: { Authorization: `Bearer ${token}` } });
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${run.report_code}.${fmt}`;
    a.click();
  }

  return (
    <div>
      <PageHeader
        title="Báo cáo (R01–R28)"
        subtitle="Chạy báo cáo tạo snapshot bất biến; xuất Excel/CSV/Word có truy vết"
      />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-1">
          {!defs ? (
            <Spinner />
          ) : (
            <div className="card divide-y divide-slate-100">
              {defs.map((d) => (
                <div key={d.code} className="flex items-center justify-between p-3">
                  <div>
                    <div className="text-sm font-medium text-slate-800">
                      <span className="font-mono text-xs text-slate-400">{d.code}</span> {d.name}
                    </div>
                    <div className="text-xs text-slate-400">{d.category}</div>
                  </div>
                  <button
                    className="btn-ghost text-xs"
                    disabled={!d.supported || busy === d.code}
                    onClick={() => runReport(d.code)}
                    title={d.supported ? "" : "Chưa hỗ trợ sinh dữ liệu"}
                  >
                    {busy === d.code ? "..." : "Chạy"}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="lg:col-span-2">
          {!run ? (
            <EmptyState message="Chọn một báo cáo và bấm Chạy để xem kết quả." />
          ) : (
            <div className="card p-4">
              <div className="mb-3 flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-slate-800">{run.snapshot.title}</h3>
                  <div className="text-xs text-slate-400">
                    Snapshot {run.snapshot_hash?.slice(0, 20)}… ·{" "}
                    {new Date(run.generated_at).toLocaleString("vi-VN")}
                  </div>
                </div>
                <div className="flex gap-2">
                  <button className="btn-ghost text-xs" onClick={() => download("xlsx")}>
                    ⬇ Excel
                  </button>
                  <button className="btn-ghost text-xs" onClick={() => download("csv")}>
                    ⬇ CSV
                  </button>
                  <button className="btn-ghost text-xs" onClick={() => download("docx")}>
                    ⬇ Word
                  </button>
                </div>
              </div>
              {run.snapshot.summary && Object.keys(run.snapshot.summary).length > 0 && (
                <div className="mb-3 flex flex-wrap gap-3 text-sm">
                  {Object.entries(run.snapshot.summary).map(([k, v]) => (
                    <span key={k} className="rounded bg-slate-100 px-2 py-1">
                      {k}: <b>{String(v)}</b>
                    </span>
                  ))}
                </div>
              )}
              <div className="max-h-[60vh] overflow-auto">
                <table className="w-full">
                  <thead className="sticky top-0 bg-slate-50">
                    <tr>
                      {run.snapshot.columns.map((c) => (
                        <th key={c} className="th">
                          {c}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {run.snapshot.rows.map((row, i) => (
                      <tr key={i}>
                        {row.map((cell, j) => (
                          <td key={j} className="td">
                            {cell === null ? "—" : String(cell)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
                {run.snapshot.rows.length === 0 && (
                  <div className="p-4 text-center text-sm text-slate-400">Không có dữ liệu.</div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
