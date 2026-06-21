"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { EmptyState, PageHeader, Spinner, StatusBadge, formatMoney } from "@/components/ui";
import type { Call, Page, Proposal } from "@/lib/types";

export default function ProposalsPage() {
  const { can } = useAuth();
  const [data, setData] = useState<Page<Proposal> | null>(null);
  const [calls, setCalls] = useState<Call[]>([]);
  const [showNew, setShowNew] = useState(false);
  const [title, setTitle] = useState("");
  const [callId, setCallId] = useState("");
  const [err, setErr] = useState("");

  async function load() {
    setData(await api.get<Page<Proposal>>("/proposals?limit=50"));
  }
  useEffect(() => {
    load();
    api.get<Page<Call>>("/funding-calls?limit=50").then((c) => {
      setCalls(c.items);
      if (c.items[0]) setCallId(c.items[0].id);
    });
  }, []);

  async function create() {
    setErr("");
    try {
      const p = await api.post<Proposal>("/proposals", { call_id: callId, title });
      setShowNew(false);
      setTitle("");
      window.location.href = `/proposals/${p.id}`;
    } catch (e: any) {
      setErr(e.message);
    }
  }

  return (
    <div>
      <PageHeader
        title="Đề xuất nghiên cứu"
        subtitle="Soạn, kiểm tra và nộp thuyết minh đề tài"
        actions={
          can("proposals.create") ? (
            <button className="btn-primary" onClick={() => setShowNew(true)}>
              + Tạo đề xuất
            </button>
          ) : undefined
        }
      />

      {showNew && (
        <div className="card mb-4 p-4">
          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <label className="label">Đợt mời nộp (call)</label>
              <select className="input" value={callId} onChange={(e) => setCallId(e.target.value)}>
                {calls.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.code} — {c.title}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Tên đề tài</label>
              <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} />
            </div>
          </div>
          {err && <div className="mt-2 text-sm text-red-600">{err}</div>}
          <div className="mt-3 flex gap-2">
            <button className="btn-primary" onClick={create} disabled={!title || !callId}>
              Tạo
            </button>
            <button className="btn-ghost" onClick={() => setShowNew(false)}>
              Hủy
            </button>
          </div>
        </div>
      )}

      {!data ? (
        <Spinner />
      ) : data.items.length === 0 ? (
        <EmptyState message="Chưa có đề xuất nào." />
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full">
            <thead className="border-b border-slate-200 bg-slate-50">
              <tr>
                <th className="th">Mã</th>
                <th className="th">Tên đề tài</th>
                <th className="th">Trạng thái</th>
                <th className="th">Ngân sách</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.items.map((p) => (
                <tr key={p.id} className="hover:bg-slate-50">
                  <td className="td font-mono text-xs">{p.proposal_code}</td>
                  <td className="td">
                    <Link href={`/proposals/${p.id}`} className="font-medium text-brand-700 hover:underline">
                      {p.title}
                    </Link>
                  </td>
                  <td className="td">
                    <StatusBadge status={p.status} />
                  </td>
                  <td className="td">{formatMoney(p.budget_total, p.currency)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
