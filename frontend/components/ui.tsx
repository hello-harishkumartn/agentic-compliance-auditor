import Link from "next/link";
import { ArrowRightIcon } from "@heroicons/react/20/solid";
import { pretty, statusTone } from "@/lib/api";

export function Header({ eyebrow, title, description, action }: {eyebrow: string; title: string; description: string; action?: React.ReactNode}) {
  return <div className="mb-8 flex flex-col justify-between gap-5 md:flex-row md:items-end"><div><p className="eyebrow">{eyebrow}</p><h1 className="mt-2 text-3xl font-semibold tracking-tight md:text-4xl">{title}</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-ink/60">{description}</p></div>{action}</div>
}
export function Pill({ value }: {value: string}) { return <span className={`status ${statusTone(value)}`}>{pretty(value)}</span> }
export function Empty({ children = "No records yet." }: {children?: React.ReactNode}) { return <div className="card p-10 text-center text-sm text-ink/50">{children}</div> }
export function Metric({ label, value, note }: {label: string; value: string | number; note: string}) { return <div className="card p-5"><p className="eyebrow">{label}</p><p className="mt-3 text-3xl font-semibold">{value}</p><p className="mt-2 text-xs text-ink/50">{note}</p></div> }
export function DetailLink({ href, label = "Inspect" }: {href: string; label?: string}) { return <Link href={href} className="inline-flex items-center gap-1 text-sm font-semibold text-moss hover:underline">{label}<ArrowRightIcon className="h-4 w-4" /></Link> }

