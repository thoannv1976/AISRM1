"use client";
import { ReactNode } from "react";

const STATUS_COLORS: Record<string, string> = {
  DRAFT: "bg-slate-100 text-slate-700",
  INTERNAL_REVIEW: "bg-amber-100 text-amber-800",
  SUBMITTED: "bg-blue-100 text-blue-800",
  UNDER_REVIEW: "bg-indigo-100 text-indigo-800",
  COUNCIL: "bg-purple-100 text-purple-800",
  APPROVED: "bg-green-100 text-green-800",
  REJECTED: "bg-red-100 text-red-800",
  WITHDRAWN: "bg-slate-200 text-slate-600",
  ACTIVE: "bg-green-100 text-green-800",
  PENDING_ACTIVATION: "bg-amber-100 text-amber-800",
  CLOSING: "bg-orange-100 text-orange-800",
  COMPLETED: "bg-teal-100 text-teal-800",
  VERIFIED: "bg-green-100 text-green-800",
  UNVERIFIED: "bg-slate-100 text-slate-600",
  PUBLISHED: "bg-green-100 text-green-800",
  OPEN: "bg-green-100 text-green-800",
  CLOSED: "bg-slate-200 text-slate-600",
};

export function StatusBadge({ status }: { status: string }) {
  const cls = STATUS_COLORS[status] || "bg-slate-100 text-slate-700";
  return <span className={`badge ${cls}`}>{status}</span>;
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-slate-500">
      <div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-brand-600" />
      {label || "Đang tải..."}
    </div>
  );
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-6 flex items-start justify-between gap-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {actions && <div className="flex shrink-0 gap-2">{actions}</div>}
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
      {message}
    </div>
  );
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="card p-4">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-900">{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-400">{hint}</div>}
    </div>
  );
}

export function formatMoney(amount: string | number | null | undefined, currency = "VND") {
  const n = typeof amount === "string" ? parseFloat(amount) : amount || 0;
  return new Intl.NumberFormat("vi-VN").format(n) + " " + currency;
}

export function AIBadge() {
  return (
    <span className="badge bg-violet-100 text-violet-700" title="Kết quả do AI gợi ý, cần người duyệt">
      ✦ AI gợi ý
    </span>
  );
}
