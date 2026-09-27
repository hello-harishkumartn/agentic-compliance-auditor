export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function getJSON<T>(path: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(`${API}${path}`, { cache: "no-store" });
    if (!response.ok) return fallback;
    return await response.json() as T;
  } catch {
    return fallback;
  }
}

export function pretty(value: string) {
  return value.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
}

export function statusTone(value: string) {
  if (["COMPLIANT", "APPROVED", "SUCCEEDED", "REPORT_READY"].includes(value)) return "bg-emerald-100 text-emerald-800";
  if (["NON_COMPLIANT", "FAILED", "REJECTED"].includes(value)) return "bg-rose-100 text-rose-800";
  if (["PARTIALLY_COMPLIANT", "PENDING", "AWAITING_FINDING_REVIEW", "AWAITING_REQUIREMENT_REVIEW"].includes(value)) return "bg-amber-100 text-amber-900";
  return "bg-slate-100 text-slate-700";
}
