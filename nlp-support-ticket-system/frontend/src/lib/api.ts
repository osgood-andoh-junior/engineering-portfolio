export const categories = ["Network", "Account", "Payment", "Software", "Hardware", "Other"] as const;
export type Category = typeof categories[number];
export type Ticket = { id: number; text: string; actual_category: Category | null; predicted_category: Category | null; confidence: number | null; model_version: string | null; created_at: string };
export type Model = { id: number; model: string; version: string; artifact_path: string; created_at: string };
export type Metrics = { accuracy: number; precision: number; recall: number; f1: number };
export type Evaluation = { id: number; model_version: string; metrics: Metrics; created_at: string };
export type Prediction = { category: Category; confidence: number; model: string; processing_time_ms: number };
export type TrainingRun = { id: number; model: string; status: string; error: string | null; created_at: string };
export class ApiError extends Error {
  constructor(message: string, public code?: string, public component?: string) { super(message); this.name = "ApiError"; }
}
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  let response: Response;
  try { response = await fetch(base + path, { ...init, headers: { "Content-Type": "application/json", ...init?.headers }, cache: "no-store" }); }
  catch { throw new ApiError("Cannot reach the backend. Start FastAPI and check the API URL.", "CONNECTION_ERROR"); }
  if (response.status === 204) return undefined as T;
  const data = await response.json();
  if (!response.ok) {
    const detail = typeof data.detail === "string" ? data.detail : Array.isArray(data.detail) ? data.detail.map((item: { msg: string }) => item.msg).join("; ") : null;
    throw new ApiError(data.message || detail || "The request failed.", data.error, data.component);
  }
  return data as T;
}
export const post = (body: unknown): RequestInit => ({ method: "POST", body: JSON.stringify(body) });
export const percent = (value: number | null | undefined) => value == null ? "—" : (value * 100).toFixed(1) + "%";
