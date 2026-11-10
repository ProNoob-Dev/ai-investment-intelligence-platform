"use client";

import { useEffect, useState } from "react";

import { CONFIG } from "@/lib/config";
import { Card, Chip } from "@/components/ui/ui";

export default function SettingsPage() {
  const [apiStatus, setApiStatus] = useState<"checking" | "up" | "down">("checking");
  const [apiDetail, setApiDetail] = useState("");

  useEffect(() => {
    fetch(`${CONFIG.API_BASE_URL}/`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setApiStatus("up");
        setApiDetail(`${data.name ?? "API"} v${data.version ?? "?"}, ${data.status ?? "running"}`);
      })
      .catch((err) => {
        setApiStatus("down");
        setApiDetail(err instanceof Error ? err.message : "Unreachable");
      });
  }, []);

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-medium tracking-tight sm:text-4xl">Settings</h1>
      <p className="mt-3 max-w-2xl text-[17px] leading-relaxed text-muted">
        Where the app gets its data, and which AI provider answers.
      </p>

      <div className="mt-8 space-y-4">
        <Card>
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="font-mono text-xs uppercase tracking-widest text-muted">API</p>
              <p className="mt-2 font-mono text-sm">{CONFIG.API_BASE_URL}</p>
              <p className="mt-1 text-sm text-muted">{apiDetail}</p>
            </div>
            <Chip tone={apiStatus === "up" ? "buy" : apiStatus === "down" ? "sell" : "neutral"}>
              {apiStatus === "checking" ? "Checking…" : apiStatus === "up" ? "Connected" : "Unreachable"}
            </Chip>
          </div>
          <p className="mt-4 text-sm leading-relaxed text-muted">
            Set <span className="font-mono">NEXT_PUBLIC_API_URL</span> to point the
            frontend at a deployed backend.
          </p>
        </Card>

        <Card>
          <p className="font-mono text-xs uppercase tracking-widest text-muted">AI providers</p>
          <ul className="mt-3 space-y-2 text-sm leading-relaxed">
            <li>
              <span className="font-medium">Inception Labs (Mercury)</span>
              <span className="text-muted">, the live provider. Set </span>
              <span className="font-mono">INCEPTION_API_KEY</span>
              <span className="text-muted"> on the backend.</span>
            </li>
            <li>
              <span className="font-medium">Gemini</span>
              <span className="text-muted">, supported as a fallback. Set </span>
              <span className="font-mono">GOOGLE_API_KEY</span>
              <span className="text-muted"> on the backend, or </span>
              <span className="font-mono">LLM_PROVIDER=gemini</span>
              <span className="text-muted"> to make it primary.</span>
            </li>
          </ul>
          <p className="mt-3 text-sm leading-relaxed text-muted">
            With no LLM key the analysis still works: the sentiment engine is
            deterministic and the AI summary simply stays empty.
          </p>
        </Card>

        <Card>
          <p className="font-mono text-xs uppercase tracking-widest text-muted">News data</p>
          <p className="mt-3 text-sm leading-relaxed text-muted">
            Live RSS feeds from Indian business publications refresh every 30
            minutes. NewsAPI and Finnhub are optional. Add their keys on the
            backend to widen coverage. Historical headlines can be imported from
            any Date, Title, Description CSV with{" "}
            <span className="font-mono">python scripts/ingest_csv.py</span>.
          </p>
        </Card>
      </div>
    </div>
  );
}
