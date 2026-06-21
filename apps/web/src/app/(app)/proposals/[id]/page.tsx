"use client";
import { use, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AIBadge, PageHeader, Spinner, StatusBadge, formatMoney } from "@/components/ui";
import type { AIOutput, Proposal, ValidationIssue } from "@/lib/types";

interface Detail {
  proposal: Proposal;
  team: { id: string; name: string; role: string }[];
  deliverables: { id: string; code: string; title: string; type: string }[];
  budget_lines: { id: string; category: string; amount: string; year: number }[];
  work_packages: { id: string; code: string; title: string }[];
  milestones: { id: string; code: string; title: string; due_date: string }[];
}

export default function ProposalWorkspace({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { can } = useAuth();
  const [d, setD] = useState<Detail | null>(null);
  const [issues, setIssues] = useState<ValidationIssue[] | null>(null);
  const [ai, setAi] = useState<AIOutput | null>(null);
  const [aiBusy, setAiBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [content, setContent] = useState({ objectives: "", methods: "", impact: "" });

  async function load() {
    const detail = await api.get<Detail>(`/proposals/${id}/detail`);
    setD(detail);
    const c = (detail.proposal.content_json || {}) as any;
    setContent({ objectives: c.objectives || "", methods: c.methods || "", impact: c.impact || "" });
  }
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (!d) return <Spinner />;
  const p = d.proposal;
  const editable = ["DRAFT", "INTERNAL_REVIEW"].includes(p.status);

  async function act(fn: () => Promise<any>, ok: string) {
    setMsg("");
    try {
      await fn();
      setMsg(ok);
      await load();
    } catch (e: any) {
      setMsg("⚠ " + (e.message || "Lỗi") + (e.fieldErrors ? ": " + Object.values(e.fieldErrors).join("; ") : ""));
    }
  }

  async function runAI(feature: string) {
    setAiBusy(true);
    setAi(null);
    try {
      const out = await api.post<AIOutput>("/ai/jobs", {
        feature_code: feature,
        entity_type: "proposal",
        entity_id: id,
      });
      setAi(out);
    } catch (e: any) {
      setMsg("⚠ AI: " + e.message);
    } finally {
      setAiBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        title={p.title}
        subtitle={`${p.proposal_code} · Phiên bản ${p.version}`}
        actions={<StatusBadge status={p.status} />}
      />
      {msg && (
        <div className="mb-4 rounded bg-slate-100 px-3 py-2 text-sm text-slate-700">{msg}</div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Main content */}
        <div className="space-y-4 lg:col-span-2">
          <div className="card p-4">
            <h3 className="mb-3 font-semibold text-slate-800">Nội dung thuyết minh</h3>
            {(["objectives", "methods", "impact"] as const).map((k) => (
              <div key={k} className="mb-3">
                <label className="label">
                  {k === "objectives" ? "Mục tiêu" : k === "methods" ? "Phương pháp" : "Tác động"}
                </label>
                <textarea
                  className="input min-h-[70px]"
                  disabled={!editable}
                  value={content[k]}
                  onChange={(e) => setContent({ ...content, [k]: e.target.value })}
                />
              </div>
            ))}
            {editable && (
              <button
                className="btn-primary"
                onClick={() =>
                  act(
                    () => api.patch(`/proposals/${id}`, { content_json: content }),
                    "Đã lưu nội dung"
                  )
                }
              >
                Lưu nội dung
              </button>
            )}
          </div>

          <div className="card p-4">
            <h3 className="mb-3 font-semibold text-slate-800">
              Thành viên ({d.team.length})
              {editable && (
                <button
                  className="ml-2 text-xs text-brand-600 hover:underline"
                  onClick={() => {
                    const name = prompt("Tên thành viên:");
                    if (name)
                      act(
                        () => api.post(`/proposals/${id}/team`, { external_person_name: name, role: "MEMBER" }),
                        "Đã thêm thành viên"
                      );
                  }}
                >
                  + Thêm
                </button>
              )}
            </h3>
            <ul className="text-sm text-slate-700">
              {d.team.map((t) => (
                <li key={t.id} className="flex justify-between border-b border-slate-50 py-1">
                  <span>{t.name || "(nội bộ)"}</span>
                  <span className="text-xs text-slate-400">{t.role}</span>
                </li>
              ))}
              {d.team.length === 0 && <li className="text-slate-400">Chưa có</li>}
            </ul>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="card p-4">
              <h3 className="mb-2 font-semibold text-slate-800">
                Sản phẩm ({d.deliverables.length})
                {editable && (
                  <button
                    className="ml-2 text-xs text-brand-600 hover:underline"
                    onClick={() => {
                      const t = prompt("Tên sản phẩm:");
                      if (t)
                        act(
                          () =>
                            api.post(`/proposals/${id}/deliverables`, {
                              code: "D" + (d.deliverables.length + 1),
                              title: t,
                            }),
                          "Đã thêm sản phẩm"
                        );
                    }}
                  >
                    + Thêm
                  </button>
                )}
              </h3>
              <ul className="text-sm">
                {d.deliverables.map((x) => (
                  <li key={x.id} className="py-0.5">
                    <span className="font-mono text-xs text-slate-400">{x.code}</span> {x.title}
                  </li>
                ))}
                {d.deliverables.length === 0 && <li className="text-slate-400">Chưa có</li>}
              </ul>
            </div>
            <div className="card p-4">
              <h3 className="mb-2 font-semibold text-slate-800">
                Ngân sách: {formatMoney(p.budget_total, p.currency)}
                {editable && (
                  <button
                    className="ml-2 text-xs text-brand-600 hover:underline"
                    onClick={() => {
                      const cat = prompt("Hạng mục:");
                      const amt = cat ? prompt("Số tiền:") : null;
                      if (cat && amt)
                        act(
                          () =>
                            api.post(`/proposals/${id}/budget-lines`, {
                              category: cat,
                              amount: amt,
                              year: 2026,
                            }),
                          "Đã thêm dòng ngân sách"
                        );
                    }}
                  >
                    + Thêm
                  </button>
                )}
              </h3>
              <ul className="text-sm">
                {d.budget_lines.map((b) => (
                  <li key={b.id} className="flex justify-between py-0.5">
                    <span>{b.category}</span>
                    <span>{formatMoney(b.amount, p.currency)}</span>
                  </li>
                ))}
                {d.budget_lines.length === 0 && <li className="text-slate-400">Chưa có</li>}
              </ul>
            </div>
          </div>
        </div>

        {/* Right rail: actions + AI */}
        <div className="space-y-4">
          <div className="card p-4">
            <h3 className="mb-3 font-semibold text-slate-800">Hành động</h3>
            <div className="space-y-2">
              <button
                className="btn-ghost w-full"
                onClick={() =>
                  act(async () => {
                    const v = await api.post<{ ok: boolean; issues: ValidationIssue[] }>(
                      `/proposals/${id}/validate`
                    );
                    setIssues(v.issues);
                  }, "Đã kiểm tra hồ sơ")
                }
              >
                Kiểm tra đầy đủ
              </button>
              {can("proposals.submit") && editable && (
                <button
                  className="btn-primary w-full"
                  onClick={() =>
                    act(() => api.post(`/proposals/${id}/submit`, { submission_note: "Nộp hồ sơ" }), "Đã nộp hồ sơ")
                  }
                >
                  Nộp hồ sơ
                </button>
              )}
              {can("decisions.create") && ["SUBMITTED", "UNDER_REVIEW", "COUNCIL"].includes(p.status) && (
                <button
                  className="btn-primary w-full"
                  onClick={() =>
                    act(
                      () =>
                        api.post(`/proposals/${id}/decision`, {
                          outcome: "APPROVED",
                          decision_no: "QD-" + Date.now(),
                          approved_budget: p.budget_total,
                        }),
                      "Đã ra quyết định: APPROVED"
                    )
                  }
                >
                  Phê duyệt (quyết định)
                </button>
              )}
              {can("projects.create") && p.status === "APPROVED" && (
                <button
                  className="btn-primary w-full"
                  onClick={() => act(() => api.post(`/proposals/${id}/activate-project`), "Đã kích hoạt đề tài")}
                >
                  Kích hoạt đề tài
                </button>
              )}
            </div>
            {issues && (
              <div className="mt-3 space-y-1">
                {issues.length === 0 && <div className="text-sm text-green-700">✓ Hợp lệ</div>}
                {issues.map((i, n) => (
                  <div
                    key={n}
                    className={`rounded px-2 py-1 text-xs ${
                      i.severity === "ERROR" ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-700"
                    }`}
                  >
                    [{i.severity}] {i.message}
                  </div>
                ))}
              </div>
            )}
          </div>

          {can("ai.run") && (
            <div className="card p-4">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="font-semibold text-slate-800">AI Copilot</h3>
                <AIBadge />
              </div>
              <div className="flex flex-wrap gap-2">
                <button className="btn-ghost text-xs" disabled={aiBusy} onClick={() => runAI("PROPOSAL_COMPLETENESS")}>
                  Kiểm tra đầy đủ
                </button>
                <button className="btn-ghost text-xs" disabled={aiBusy} onClick={() => runAI("PROPOSAL_CONSISTENCY_REVIEW")}>
                  Rà soát nhất quán
                </button>
                <button className="btn-ghost text-xs" disabled={aiBusy} onClick={() => runAI("PROPOSAL_SUMMARY")}>
                  Tóm tắt
                </button>
              </div>
              {aiBusy && <div className="mt-3"><Spinner label="AI đang phân tích..." /></div>}
              {ai && (
                <div className="mt-3 rounded-lg border border-violet-100 bg-violet-50/40 p-3 text-sm">
                  {ai.insufficient_evidence && (
                    <div className="mb-2 text-xs font-medium text-amber-700">
                      ⚠ Không đủ dữ liệu — cần kiểm tra.
                    </div>
                  )}
                  {ai.content_json.summary && <p className="text-slate-700">{ai.content_json.summary}</p>}
                  {Array.isArray(ai.content_json.findings) &&
                    ai.content_json.findings.map((f: any, n: number) => (
                      <div key={n} className="mt-2 border-l-2 border-violet-300 pl-2">
                        <div className="text-xs font-semibold text-violet-800">
                          [{f.severity}] {f.code}
                        </div>
                        <div className="text-slate-700">{f.statement}</div>
                        {f.suggestion && <div className="text-xs text-slate-500">→ {f.suggestion}</div>}
                      </div>
                    ))}
                  <div className="mt-3 flex gap-2 border-t border-violet-100 pt-2">
                    <button
                      className="text-xs text-green-700 hover:underline"
                      onClick={() =>
                        api.post(`/ai/outputs/${ai.id}/feedback`, { accept: true, rating: "UP" }).then(() => setMsg("Đã chấp nhận gợi ý AI"))
                      }
                    >
                      ✓ Chấp nhận
                    </button>
                    <button
                      className="text-xs text-red-700 hover:underline"
                      onClick={() =>
                        api.post(`/ai/outputs/${ai.id}/feedback`, { accept: false, rating: "DOWN" }).then(() => setMsg("Đã từ chối gợi ý AI"))
                      }
                    >
                      ✕ Từ chối
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
