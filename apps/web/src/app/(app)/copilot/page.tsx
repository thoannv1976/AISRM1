"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { AIBadge, PageHeader } from "@/components/ui";

interface ChatTurn {
  role: "user" | "ai";
  text: string;
  citations?: { citation_id: string; excerpt?: string | null }[];
  insufficient?: boolean;
}

export default function CopilotPage() {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  async function send() {
    const q = input.trim();
    if (!q) return;
    setInput("");
    setTurns((t) => [...t, { role: "user", text: q }]);
    setBusy(true);
    try {
      const res = await api.post<{
        answer: string;
        citations: { citation_id: string; excerpt?: string | null }[];
        insufficient_evidence: boolean;
      }>("/ai/chat", { message: q });
      setTurns((t) => [
        ...t,
        { role: "ai", text: res.answer, citations: res.citations, insufficient: res.insufficient_evidence },
      ]);
    } catch (e: any) {
      setTurns((t) => [...t, { role: "ai", text: "⚠ " + e.message }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        title="AI Research Copilot"
        subtitle="Hỏi đáp trên kho dữ liệu nội bộ (RAG) — chỉ trong phạm vi quyền, luôn trích nguồn"
      />
      <div className="card flex h-[60vh] flex-col">
        <div className="flex-1 space-y-4 overflow-y-auto p-4">
          {turns.length === 0 && (
            <div className="mt-10 text-center text-sm text-slate-400">
              Hãy đặt câu hỏi về quy định, hồ sơ, tiến độ hoặc sản phẩm.
              <br />
              Câu trả lời sẽ kèm trích dẫn nguồn; nếu thiếu dữ liệu, hệ thống nói rõ.
            </div>
          )}
          {turns.map((t, i) => (
            <div key={i} className={t.role === "user" ? "text-right" : ""}>
              <div
                className={`inline-block max-w-[85%] rounded-2xl px-4 py-2 text-sm ${
                  t.role === "user" ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-800"
                }`}
              >
                {t.role === "ai" && (
                  <div className="mb-1">
                    <AIBadge />
                    {t.insufficient && <span className="ml-2 text-xs text-amber-600">Không đủ dữ liệu</span>}
                  </div>
                )}
                <div className="whitespace-pre-wrap">{t.text}</div>
                {t.citations && t.citations.length > 0 && (
                  <div className="mt-2 space-y-1 border-t border-slate-200 pt-2 text-xs text-slate-500">
                    {t.citations.map((c) => (
                      <div key={c.citation_id}>
                        <span className="font-mono text-brand-600">[{c.citation_id}]</span> {c.excerpt}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          {busy && <div className="text-sm text-slate-400">AI đang truy hồi nguồn...</div>}
        </div>
        <div className="flex gap-2 border-t border-slate-200 p-3">
          <input
            className="input"
            placeholder="Nhập câu hỏi..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
          />
          <button className="btn-primary" onClick={send} disabled={busy}>
            Gửi
          </button>
        </div>
      </div>
    </div>
  );
}
