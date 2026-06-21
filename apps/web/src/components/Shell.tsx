"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { Spinner } from "./ui";

interface NavItem {
  href: string;
  label: string;
  perm?: string;
  icon: string;
}

const NAV: NavItem[] = [
  { href: "/dashboard", label: "Tổng quan", icon: "▣" },
  { href: "/calls", label: "Đợt mời nộp", perm: "calls.read", icon: "📣" },
  { href: "/proposals", label: "Đề xuất", perm: "proposals.read", icon: "📝" },
  { href: "/reviews", label: "Phản biện & Hội đồng", perm: "reviews.read", icon: "⚖" },
  { href: "/projects", label: "Đề tài", perm: "projects.read", icon: "📂" },
  { href: "/outputs", label: "Công bố & Sản phẩm", perm: "outputs.read", icon: "📚" },
  { href: "/researchers", label: "Nhà nghiên cứu", perm: "researchers.read", icon: "👤" },
  { href: "/ethics", label: "Đạo đức & Liêm chính", perm: "ethics.read", icon: "🧭" },
  { href: "/kpi", label: "KPI & Khen thưởng", perm: "kpi.read", icon: "🏆" },
  { href: "/documents", label: "Kho tài liệu", perm: "documents.read", icon: "🗄" },
  { href: "/reports", label: "Báo cáo", perm: "reports.read", icon: "📊" },
  { href: "/copilot", label: "AI Copilot", perm: "ai.run", icon: "✦" },
  { href: "/ai-config", label: "Cấu hình AI", perm: "admin.config", icon: "🔑" },
  { href: "/admin", label: "Quản trị & Audit", perm: "audit.read", icon: "⚙" },
];

export function Shell({ children }: { children: ReactNode }) {
  const { me, loading, can, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !me) router.push("/login");
  }, [loading, me, router]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner label="Đang tải phiên làm việc..." />
      </div>
    );
  }
  if (!me) return null;

  const items = NAV.filter((n) => !n.perm || can(n.perm));

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-64 shrink-0 flex-col border-r border-slate-200 bg-white">
        <div className="flex items-center gap-2 border-b border-slate-100 px-5 py-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 font-bold text-white">
            AI
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-900">AISRM1</div>
            <div className="text-xs text-slate-500">AI-ResearchHub</div>
          </div>
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {items.map((n) => {
            const active = pathname === n.href || pathname.startsWith(n.href + "/");
            return (
              <Link
                key={n.href}
                href={n.href}
                className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm ${
                  active
                    ? "bg-brand-50 font-medium text-brand-700"
                    : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                <span className="w-5 text-center">{n.icon}</span>
                {n.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-slate-100 p-3 text-xs text-slate-400">
          AI hỗ trợ — con người quyết định
        </div>
      </aside>

      <div className="flex flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-3">
          <div className="text-sm text-slate-500">Phòng Quản lý khoa học</div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <div className="text-sm font-medium text-slate-800">{me.user.display_name}</div>
              <div className="text-xs text-slate-500">
                {me.system_roles.join(", ") || me.user.email}
              </div>
            </div>
            <button onClick={logout} className="btn-ghost text-xs">
              Đăng xuất
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
