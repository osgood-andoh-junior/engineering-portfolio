"use client";
import { useEffect, useState, type ReactNode } from "react";
export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch("/api/cloud" + path, { cache: "no-store", ...init });
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(typeof error?.detail === "string" ? error.detail : "Request could not be completed.");
  }
  return response.json();
}

export function useData<T>(path: string, revision = 0) {
  const [result, setResult] = useState<{
    path: string; data?: T; error?: string; receivedAt?: number;
  }>();
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function refresh() {
      try {
        const data = await request<T>(path, { signal: controller.signal });
        if (!controller.signal.aborted) setResult({ path, data, receivedAt: Date.now() });
      } catch (error) {
        if (!controller.signal.aborted) {
          setResult({ path, error: error instanceof Error ? error.message : "Unable to load data." });
        }
      } finally {
        if (!controller.signal.aborted) timer = setTimeout(refresh, 5000);
      }
    }
    void refresh();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [path, revision]);
  return result?.path === path ? result : undefined;
}

export function Content<T>({ result, children }: {
  result: ReturnType<typeof useData<T>>; children: (data: T) => ReactNode;
}) {
  if (result?.error) return <p className="message error" role="alert">{result.error}</p>;
  if (result?.data === undefined) return <p className="message" role="status">Loading monitoring data…</p>;
  return children(result.data);
}

export function Panel({ title, subtitle, children, extra }: {
  title: string; subtitle?: string; children: ReactNode; extra?: ReactNode;
}) {
  return <section className="panel" aria-label={title}><header className="panel-head"><div><h2>{title}</h2>
    {subtitle && <p>{subtitle}</p>}</div>{extra}</header>{children}</section>;
}
