"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { AIBadge, EmptyState, PageHeader, Spinner } from "@/components/ui";
import type { Page, Proposal, Suggestion } from "@/lib/types";

interface Reviewer {
  id: string;
  full_name: string;
  affiliation?: string | null;
  expertise: string[];
  current_load: number;
  is_external: boolean;
}

interface Council {
  id: string;
  code: string;
  name: string;
  council_type: string;
  status: string;
}

export default function ReviewsPage() {
  const [reviewers, setReviewers] = useState<Reviewer[]>([]);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [pid, setPid] = useState("");
  const [sugg, setSugg] = useState<Suggestion[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [councils, setCouncils] = useState<Council[]>([]);
  const [cmsg, setCmsg] = useState("");

  async function loadCouncils() {
    setCouncils((await api.get<Page<Council>>("/councils?limit=50")).items);
  }

  useEffect(() => {
    api.get<Page<Reviewer>>("/reviewers?limit=50").then((r) => setReviewers(r.items));
    api.get<Page<Proposal>>("/proposals?limit=50").then((p) => {
      setProposals(p.items);
      if (p.items[0]) setPid(p.items[0].id);
    });
    loadCouncils();
  }, []);

  async function suggest() {
    if (!pid) return;
    setBusy(true);
    setSugg(null);
    try {
      setSugg(await api.post<Suggestion[]>(`/proposals/${pid}/reviewer-suggestions`));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader title="Phản biện & Hội đồng" subtitle="Reviewer pool, xung đột lợi ích, gợi ý chuyên gia" />

      <div className="card mb-6 p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="font-semibold text-slate-800">Gợi ý reviewer (AI)</h3>
          <AIBadge />
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <div className="flex-1">
            <label className="label">Chọn đề xuất</label>
            <select className="input" value={pid} onChange={(e) => setPid(e.target.value)}>
              {proposals.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.proposal_code} — {p.title}
                </option>
              ))}
            </select>
          </div>
          <button className="btn-primary" onClick={suggest} disabled={busy || !pid}>
            Gợi ý chuyên gia
          </button>
        </div>
        <p className="mt-2 text-xs text-slate-400">
          AI chỉ xếp hạng sau khi loại COI cứng; cán bộ tự quyết định mời.
        </p>
        {busy && <div className="mt-3"><Spinner /></div>}
        {sugg && (
          <div className="mt-4 space-y-2">
            {sugg.map((s) => (
              <div
                key={s.reviewer_id}
                className={`flex items-start justify-between rounded-lg border p-3 ${
                  s.excluded ? "border-red-100 bg-red-50/40" : "border-slate-200"
                }`}
              >
                <div>
                  <div className="font-medium text-slate-800">
                    {s.full_name}
                    {s.excluded && <span className="ml-2 text-xs text-red-600">(Loại: {s.exclusion_reason})</span>}
                  </div>
                  <div className="text-xs text-slate-500">{s.reasons.join(" · ")}</div>
                </div>
                <div className="text-sm font-semibold text-brand-700">{s.score.toFixed(1)}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <h3 className="mb-2 font-semibold text-slate-800">Reviewer pool ({reviewers.length})</h3>
      {reviewers.length === 0 ? (
        <EmptyState message="Chưa có reviewer." />
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          {reviewers.map((r) => (
            <div key={r.id} className="card p-4">
              <div className="font-medium text-slate-800">{r.full_name}</div>
              <div className="text-xs text-slate-500">{r.affiliation || (r.is_external ? "Ngoài trường" : "Nội bộ")}</div>
              <div className="mt-2 flex flex-wrap gap-1">
                {r.expertise.map((e) => (
                  <span key={e} className="badge bg-slate-100 text-slate-600">{e}</span>
                ))}
              </div>
              <div className="mt-2 text-xs text-slate-400">Tải hiện tại: {r.current_load}</div>
            </div>
          ))}
        </div>
      )}

      {/* Council & quyết nghị */}
      <div className="mt-8">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="font-semibold text-slate-800">Hội đồng khoa học</h3>
          <button
            className="btn-ghost text-xs"
            onClick={async () => {
              const name = prompt("Tên hội đồng:");
              if (!name) return;
              await api.post("/councils", {
                code: "HD-" + Date.now().toString().slice(-5),
                name,
                council_type: "SELECTION",
              });
              loadCouncils();
            }}
          >
            + Tạo hội đồng
          </button>
        </div>
        {cmsg && <div className="mb-2 rounded bg-slate-100 px-3 py-2 text-sm">{cmsg}</div>}
        {councils.length === 0 ? (
          <EmptyState message="Chưa có hội đồng." />
        ) : (
          <div className="card divide-y divide-slate-100">
            {councils.map((c) => (
              <div key={c.id} className="flex items-center justify-between p-3">
                <div>
                  <div className="text-sm font-medium text-slate-800">{c.name}</div>
                  <div className="text-xs text-slate-400">
                    {c.code} · {c.council_type} · {c.status}
                  </div>
                </div>
                <button
                  className="btn-ghost text-xs"
                  onClick={async () => {
                    // create a meeting then finalize (demo of quorum/decision flow)
                    const r = await api.post<{ meeting_id: string }>(`/councils/${c.id}/meetings`, {
                      title: "Phiên họp " + new Date().toLocaleDateString("vi-VN"),
                      quorum_required: 0,
                    });
                    try {
                      const f = await api.post<{ quorum_voters: number }>(
                        `/council-meetings/${r.meeting_id}/finalize`
                      );
                      setCmsg(`Đã tạo & chốt phiên họp (quorum: ${f.quorum_voters}).`);
                    } catch (e: any) {
                      setCmsg("⚠ " + e.message);
                    }
                  }}
                >
                  Tạo & chốt phiên họp
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
