"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChartBarIcon, ScaleIcon, ClipboardDocumentCheckIcon, ShieldCheckIcon, CircleStackIcon, MagnifyingGlassIcon, ExclamationTriangleIcon, UserGroupIcon, DocumentChartBarIcon, CpuChipIcon } from "@heroicons/react/24/outline";

const groups = [
  ["Workspace", [["Dashboard", "/", ChartBarIcon], ["Frameworks", "/frameworks", ScaleIcon], ["Requirements", "/requirements", ClipboardDocumentCheckIcon], ["Controls", "/controls", ShieldCheckIcon], ["Evidence", "/evidence", CircleStackIcon]]],
  ["Assurance", [["Audits", "/audits", MagnifyingGlassIcon], ["Findings", "/findings", ExclamationTriangleIcon], ["Review queue", "/reviews", UserGroupIcon], ["Reports", "/reports", DocumentChartBarIcon], ["Agent runs", "/agent-runs", CpuChipIcon]]],
] as const;
const mobileLinks = [["Home", "/", ChartBarIcon], ["Audits", "/audits", MagnifyingGlassIcon], ["Findings", "/findings", ExclamationTriangleIcon], ["Reviews", "/reviews", UserGroupIcon], ["Runs", "/agent-runs", CpuChipIcon]] as const;

export function Sidebar() {
  const pathname = usePathname();
  return <><aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-white/10 bg-ink text-white lg:flex lg:flex-col">
    <div className="border-b border-white/10 px-6 py-7">
      <div className="flex items-center gap-3"><div className="grid h-9 w-9 place-items-center rounded-xl bg-amber font-black text-ink">A</div><div><p className="font-semibold leading-none">Assure AI</p><p className="mt-1 text-xs text-white/50">Compliance operations</p></div></div>
    </div>
    <nav className="flex-1 space-y-7 overflow-y-auto px-3 py-6">{groups.map(([label, links]) => <div key={label}>
      <p className="mb-2 px-3 text-[10px] font-bold uppercase tracking-[.18em] text-white/35">{label}</p>
      <div className="space-y-1">{links.map(([name, href, Icon]) => { const active = href === "/" ? pathname === href : pathname.startsWith(href); return <Link key={href} href={href} className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${active ? "bg-white/10 text-white" : "text-white/60 hover:bg-white/5 hover:text-white"}`}><Icon className={`h-5 w-5 ${active ? "text-amber" : ""}`} />{name}</Link> })}</div>
    </div>)}</nav>
    <div className="m-4 rounded-xl border border-white/10 bg-white/5 p-4"><p className="text-xs font-semibold">Northstar Payments</p><p className="mt-1 text-[11px] text-white/45">Synthetic demo workspace</p></div>
  </aside><nav className="fixed inset-x-3 bottom-3 z-50 flex justify-around rounded-2xl border border-white/10 bg-ink/95 px-2 py-2 text-white shadow-xl backdrop-blur lg:hidden">{mobileLinks.map(([name,href,Icon])=><Link key={href} href={href} className={`flex min-w-14 flex-col items-center gap-1 rounded-xl px-2 py-1.5 text-[9px] ${pathname===href||href!=="/"&&pathname.startsWith(href)?"bg-white/10 text-amber":"text-white/55"}`}><Icon className="h-5 w-5"/>{name}</Link>)}</nav></>
}
