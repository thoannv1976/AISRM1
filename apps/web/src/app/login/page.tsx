"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const DEMO = [
  ["System Admin", "admin@aisrm1.edu.vn", "Admin@12345"],
  ["Research Officer", "officer@aisrm1.edu.vn", "Officer@12345"],
  ["Researcher (PI)", "pi@aisrm1.edu.vn", "Researcher@12345"],
  ["Reviewer", "reviewer@aisrm1.edu.vn", "Reviewer@12345"],
  ["Executive", "exec@aisrm1.edu.vn", "Exec@12345"],
];

export default function LoginPage() {
  const [email, setEmail] = useState("officer@aisrm1.edu.vn");
  const [password, setPassword] = useState("Officer@12345");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const router = useRouter();
  const { refresh } = useAuth();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(email, password);
      await refresh();
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Đăng nhập thất bại");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-brand-50 to-slate-100 p-4">
      <div className="grid w-full max-w-4xl overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-lg md:grid-cols-2">
        <div className="hidden flex-col justify-between bg-brand-700 p-8 text-white md:flex">
          <div>
            <div className="text-2xl font-bold">AISRM1</div>
            <div className="text-brand-100">AI-ResearchHub</div>
          </div>
          <div>
            <p className="text-lg font-medium">
              Hệ thống Quản lý Nghiên cứu Khoa học, Công bố và Đổi mới sáng tạo tích hợp AI
            </p>
            <p className="mt-3 text-sm text-brand-100">
              AI hỗ trợ — con người quyết định. Mọi kết quả AI là gợi ý có nguồn, được phê duyệt.
            </p>
          </div>
          <div className="text-xs text-brand-200">Phòng Quản lý khoa học · v1.0</div>
        </div>

        <div className="p-8">
          <h1 className="text-xl font-semibold text-slate-900">Đăng nhập</h1>
          <p className="mt-1 text-sm text-slate-500">Sử dụng tài khoản nội bộ (local) cho môi trường demo.</p>
          <form onSubmit={submit} className="mt-6 space-y-4">
            <div>
              <label className="label">Email</label>
              <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
            <div>
              <label className="label">Mật khẩu</label>
              <input
                type="password"
                className="input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            {error && <div className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
            <button className="btn-primary w-full" disabled={busy}>
              {busy ? "Đang đăng nhập..." : "Đăng nhập"}
            </button>
          </form>

          <div className="mt-6 border-t border-slate-100 pt-4">
            <div className="mb-2 text-xs font-medium uppercase text-slate-400">Tài khoản demo</div>
            <div className="space-y-1">
              {DEMO.map(([role, e, p]) => (
                <button
                  key={e}
                  onClick={() => {
                    setEmail(e);
                    setPassword(p);
                  }}
                  className="flex w-full justify-between rounded px-2 py-1 text-left text-xs hover:bg-slate-100"
                >
                  <span className="font-medium text-slate-700">{role}</span>
                  <span className="text-slate-400">{e}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
