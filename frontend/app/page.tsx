import { Header, Metric, Pill, DetailLink } from "@/components/ui";
import { Workflow } from "@/components/workflow";
import { getJSON, pretty } from "@/lib/api";

type Dashboard = { metrics: Record<string, number>; assessments: Record<string, number>; audits: Array<{id:string;name:string;status:string;scope:string;progress:number}> };
const fallback: Dashboard = { metrics: {active_audits:0,controls_tested:0,pending_reviews:0,high_risk_gaps:0}, assessments: {}, audits: [] };
export default async function DashboardPage() {
  const data = await getJSON<Dashboard>("/api/dashboard", fallback);
  const total = Object.values(data.assessments).reduce((a,b)=>a+b,0) || 1;
  const colors: Record<string,string> = {COMPLIANT:"bg-emerald-600",PARTIALLY_COMPLIANT:"bg-amber-500",NON_COMPLIANT:"bg-rose-600",INSUFFICIENT_EVIDENCE:"bg-slate-400",REQUIRES_HUMAN_REVIEW:"bg-violet-500"};
  return <><Header eyebrow="Operational overview" title="Compliance command center" description="Trace every AI-assisted assessment from source requirement to cited evidence and human decision." />
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4"><Metric label="Active audits" value={data.metrics.active_audits} note="Currently in workflow"/><Metric label="Controls tested" value={data.metrics.controls_tested} note="Across active scope"/><Metric label="Review queue" value={data.metrics.pending_reviews} note="Human decisions required"/><Metric label="High-risk gaps" value={data.metrics.high_risk_gaps} note="Non-compliant findings"/></div>
    <div className="mt-7"><p className="eyebrow mb-3">Live workflow</p><div className="overflow-x-auto"><Workflow active={7}/></div></div>
    <div className="mt-7 grid gap-5 xl:grid-cols-[1.5fr_1fr]">
      <section className="card overflow-hidden"><div className="border-b border-ink/10 p-5"><p className="font-semibold">Recent audits</p><p className="text-xs text-ink/50">Human-gated assurance work</p></div>{data.audits.map(a=><div key={a.id} className="grid gap-3 border-b border-ink/10 p-5 last:border-0 md:grid-cols-[1fr_auto_auto] md:items-center"><div><p className="font-medium">{a.name}</p><p className="mt-1 text-xs text-ink/50">{a.scope}</p></div><Pill value={a.status}/><DetailLink href={`/audits/${a.id}`} /></div>)}{!data.audits.length&&<p className="p-8 text-sm text-ink/50">Start the backend to load the seeded audit.</p>}</section>
      <section className="card p-5"><p className="font-semibold">Assessment mix</p><div className="mt-5 flex h-3 overflow-hidden rounded-full bg-ink/5">{Object.entries(data.assessments).map(([k,v])=><div key={k} title={k} className={colors[k]} style={{width:`${v/total*100}%`}} />)}</div><div className="mt-5 space-y-3">{Object.entries(data.assessments).map(([k,v])=><div key={k} className="flex items-center justify-between text-xs"><span className="flex items-center gap-2"><i className={`h-2.5 w-2.5 rounded-full ${colors[k]}`}/>{pretty(k)}</span><strong>{v}</strong></div>)}</div></section>
    </div></>;
}
