"use client";

import { useRef, useState } from "react";
import { ArrowUpTrayIcon } from "@heroicons/react/20/solid";
import { API } from "@/lib/api";

export function UploadButton({ resource }: { resource: "framework" | "evidence" }) {
  const input = useRef<HTMLInputElement>(null);
  const [state, setState] = useState("Upload text file");
  async function upload(file?: File) {
    if (!file) return;
    setState("Uploading…");
    const content = await file.text();
    const endpoint = resource === "framework" ? "/api/frameworks" : "/api/evidence";
    const body = resource === "framework"
      ? { name: file.name.replace(/\.[^.]+$/, ""), version: "uploaded", source_type: "user_supplied", description: "Uploaded framework", content }
      : { name: file.name, kind: "evidence", content };
    const response = await fetch(`${API}${endpoint}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!response.ok) { setState("Upload failed"); return; }
    window.location.reload();
  }
  return <><input ref={input} className="hidden" type="file" accept=".txt,.md,text/plain,text/markdown" onChange={e => upload(e.target.files?.[0])}/><button onClick={() => input.current?.click()} className="inline-flex items-center gap-2 rounded-xl bg-ink px-4 py-2.5 text-sm font-semibold text-white"><ArrowUpTrayIcon className="h-4 w-4"/>{state}</button></>;
}
