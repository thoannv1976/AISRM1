"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PageHeader, Spinner, Stat } from "@/components/ui";
import type { AIConfig, AIFeature, AIUsage } from "@/lib/types";

export default function AIConfigPage() {
  const [cfg, setCfg] = useState<AIConfig | null>(null);
  const [usage, setUsage] = useState<AIUsage | null>(null);
  const [features, setFeatures] = useState<AIFeature[]>([]);
  const [msg, setMsg] = useState("");
  const [test, setTest] = useState<{ ok: boolean; message: string } | null>(null);
  const [busy, setBusy] = useState(false);

  // form state
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("");
  const [mode, setMode] = useState("AUTO");
  const [budget, setBudget] = useState<number>(100);
  const [clearKey, setClearKey] = useState(false);

  async function load() {
    const c = await api.get<AIConfig>("/ai/config");
    setCfg(c);
    setModel(c.llm_model);
    setMode(c.mode);
    setBudget(c.monthly_budget);
    api.get<AIUsage>("/ai/usage").then(setUsage).catch(() => {});
    api.get<AIFeature[]>("/ai/features").then(setFeatures).catch(() => {});
  }
  useEffect(() => {
    load();
  }, []);

  async function save() {
    setBusy(true);
    setMsg("");
    setTest(null);
    try {
      const body: Record<string, unknown> = { mode, llm_model: model, monthly_budget: budget };
      if (clearKey) body.clear_key = true;
      else if (apiKey.trim()) body.api_key = apiKey.trim();
      const updated = await api.put<AIConfig>("/ai/config", body);
      setCfg(updated);
      setApiKey("");
      setClearKey(false);
      setMsg("✓ Đã lưu cấu hình AI.");
    } catch (e: any) {
      setMsg("⚠ " + e.message);
    } finally {
      setBusy(false);
    }
  }

  async function runTest() {
    setBusy(true);
    setTest(null);
    try {
      const r = await api.post<{ ok: boolean; message: string }>("/ai/config/test");
      setTest(r);
      load();
    } catch (e: any) {
      setTest({ ok: false, message: e.message });
    } finally {
      setBusy(false);
    }
  }

  async function toggle(f: AIFeature) {
    const updated = await api.patch<AIFeature>(`/ai/features/${f.id}/toggle`, { enabled: !f.enabled });
    setFeatures((fs) => fs.map((x) => (x.id === f.id ? updated : x)));
  }

  if (!cfg) return <Spinner />;

  return (
    <div>
      <PageHeader
        title="Cấu hình AI"
        subtitle="Nạp & quản lý API key, model và chế độ cho AI Copilot — chỉ dành cho quản trị"
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Current config + form */}
        <div className="space-y-4 lg:col-span-2">
          <div className="card p-5">
            <h3 className="mb-4 flex items-center gap-2 font-semibold text-slate-800">
              🔑 Cấu hình AI Copilot
            </h3>
            <dl className="grid grid-cols-3 gap-y-2 text-sm">
              <dt className="text-slate-500">Bộ AI hiện dùng</dt>
              <dd className="col-span-2 font-semibold text-green-700">{cfg.effective_label}</dd>
              <dt className="text-slate-500">Model</dt>
              <dd className="col-span-2 font-mono">{cfg.effective_model}</dd>
              <dt className="text-slate-500">API key</dt>
              <dd className="col-span-2">
                {cfg.api_key_masked ? (
                  <span className="font-mono">
                    {cfg.api_key_masked}{" "}
                    <span className="text-slate-400">(nguồn: {cfg.api_key_source})</span>
                  </span>
                ) : (
                  <span className="text-slate-400">Chưa cấu hình (nguồn: {cfg.api_key_source})</span>
                )}
              </dd>
            </dl>

            <div className="mt-5 space-y-4 border-t border-slate-100 pt-4">
              <div>
                <label className="label">Nạp/đổi Claude API key</label>
                <input
                  className="input font-mono"
                  placeholder="sk-ant-... (để trống = giữ key hiện tại)"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  disabled={clearKey}
                  autoComplete="off"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label">Model</label>
                  <select className="input" value={model} onChange={(e) => setModel(e.target.value)}>
                    {(cfg.available_models.includes(model)
                      ? cfg.available_models
                      : [model, ...cfg.available_models]
                    ).map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="label">Chế độ</label>
                  <select className="input" value={mode} onChange={(e) => setMode(e.target.value)}>
                    <option value="AUTO">Tự động (có key → Claude)</option>
                    <option value="CLAUDE">Luôn dùng Claude (chấm thật)</option>
                    <option value="MOCK">Mock (offline, không gọi API)</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="label">Hạn mức chi phí/tháng (USD)</label>
                <input
                  type="number"
                  className="input max-w-[200px]"
                  value={budget}
                  onChange={(e) => setBudget(parseFloat(e.target.value) || 0)}
                />
              </div>
              <label className="flex items-center gap-2 text-sm text-slate-600">
                <input
                  type="checkbox"
                  checked={clearKey}
                  onChange={(e) => setClearKey(e.target.checked)}
                />
                Xóa API key đang lưu
              </label>

              {msg && <div className="rounded bg-slate-100 px-3 py-2 text-sm">{msg}</div>}

              <div className="flex gap-2">
                <button className="btn-primary" onClick={save} disabled={busy}>
                  Lưu cấu hình AI
                </button>
                <button className="btn-ghost" onClick={runTest} disabled={busy}>
                  ⚡ Kiểm tra kết nối
                </button>
              </div>

              {test && (
                <div
                  className={`rounded px-3 py-2 text-sm ${
                    test.ok ? "bg-green-50 text-green-700" : "bg-amber-50 text-amber-700"
                  }`}
                >
                  {test.ok ? "✓ " : "⚠ "}
                  {test.message}
                </div>
              )}
              <p className="text-xs text-slate-400">
                API key được mã hoá khi lưu trong CSDL; hệ thống không bao giờ trả lại key gốc. AI là
                gợi ý, cần người duyệt (human-in-the-loop).
              </p>
            </div>
          </div>

          {/* Features kill-switch */}
          <div className="card p-5">
            <h3 className="mb-3 font-semibold text-slate-800">Tính năng AI (bật/tắt)</h3>
            <div className="divide-y divide-slate-100">
              {features.map((f) => (
                <div key={f.id} className="flex items-center justify-between py-2">
                  <div>
                    <div className="text-sm font-medium text-slate-800">{f.name}</div>
                    <div className="text-xs text-slate-400">
                      {f.code} · rủi ro {f.risk_level}
                      {f.requires_citations && " · yêu cầu trích nguồn"}
                    </div>
                  </div>
                  <button
                    onClick={() => toggle(f)}
                    className={`relative h-6 w-11 rounded-full transition ${
                      f.enabled ? "bg-green-500" : "bg-slate-300"
                    }`}
                    title={f.enabled ? "Đang bật" : "Đang tắt"}
                  >
                    <span
                      className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition ${
                        f.enabled ? "left-[22px]" : "left-0.5"
                      }`}
                    />
                  </button>
                </div>
              ))}
              {features.length === 0 && <div className="text-sm text-slate-400">Không có tính năng.</div>}
            </div>
          </div>
        </div>

        {/* Usage */}
        <div className="space-y-4">
          <div className="card p-5">
            <h3 className="mb-3 font-semibold text-slate-800">Sử dụng AI</h3>
            {!usage ? (
              <Spinner />
            ) : (
              <div className="space-y-3">
                <Stat label="Số lần gọi" value={usage.calls} hint={`${usage.jobs} job`} />
                <Stat label="Tổng token" value={usage.total_tokens.toLocaleString("vi-VN")} />
                <Stat
                  label="Ước tính chi phí"
                  value={`$${usage.estimated_cost.toFixed(4)}`}
                  hint={`Hạn mức tháng: $${usage.monthly_budget}`}
                />
                <div className="h-2 rounded bg-slate-100">
                  <div
                    className="h-2 rounded bg-brand-500"
                    style={{
                      width: `${Math.min(
                        100,
                        usage.monthly_budget
                          ? (usage.estimated_cost / usage.monthly_budget) * 100
                          : 0
                      )}%`,
                    }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
