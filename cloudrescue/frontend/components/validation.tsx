"use client";

import Link from "next/link";
import { useState } from "react";
import { Content, Panel, request, useData } from "./dashboard-data";

type Section = "benchmark-lab" | "security" | "audit-verification" | "reliability-report";
type Stat = { n: number; mean?: number; median?: number; p05?: number; p95?: number; ci95?: [number, number] };
type Report = {
  id: number; trial_count: number; version: string; master_seed: number;
  families: string[]; distribution_per_family: Record<string, number>;
  held_out: Record<string, Record<string, Stat>>;
};
type Account = { username: string; role: string; active: boolean };
type Verification = { valid: boolean; count?: number; digest?: string; anchored?: boolean; reason?: string; failure_at?: number };
const headers = { "Content-Type": "application/json", "x-cloudrescue-action": "fault" };

function change<T>(path: string, data: object | null, method = "POST") {
  return request<T>(path, { method, headers, body: JSON.stringify(data) });
}

function useAction() {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  async function run(action: () => Promise<void>) {
    setBusy(true);
    setMessage("");
    try { await action(); } catch (error) {
      setMessage(error instanceof Error ? error.message : "The operation failed.");
    } finally { setBusy(false); }
  }
  return { busy, message, run, setMessage };
}

export function ValidationPages({ section, signedIn }: { section: Section; signedIn: boolean }) {
  if (!signedIn) return <Panel title="Operator sign-in"><p className="message">
    <Link href="/simulation">Sign in</Link> to access this workspace.</p></Panel>;
  if (section === "security") return <Accounts />;
  if (section === "audit-verification") return <Audit />;
  return <Benchmarks reportOnly={section === "reliability-report"} />;
}

function Benchmarks({ reportOnly }: { reportOnly: boolean }) {
  const [revision, setRevision] = useState(0);
  const runs = useData<{ id: number; seed: number }[]>("/benchmarks", revision);
  const [seed, setSeed] = useState(42);
  const [report, setReport] = useState<Report>();
  const [metric, setMetric] = useState("request_success");
  const { busy, message, run } = useAction();
  return <>
    <Panel title={reportOnly ? "Saved benchmark reports" : "Run a workload benchmark"}
      subtitle="Modeled experiments use development, validation, and held-out partitions.">
      {!reportOnly && <form className="form" onSubmit={event => {
        event.preventDefault();
        void run(async () => { setReport(await change("/benchmarks", { seed })); setRevision(value => value + 1); });
      }}><label>Master seed<input type="number" min="0" max="2147483647" required value={seed}
        onChange={event => setSeed(Number(event.target.value))} /></label>
        <button disabled={busy}>{busy ? "Running…" : "Run benchmark"}</button></form>}
      <Content result={runs}>{rows => <label className="controls diagnosis-summary">Saved run
        <select aria-label="Saved run" value={report?.id ?? ""} onChange={event => {
          const id = event.target.value;
          if (id) void run(async () => setReport(await request("/benchmarks/" + id)));
        }}><option value="">Select a run</option>{rows.map(row => <option key={row.id} value={row.id}>
          #{row.id} · seed {row.seed}</option>)}</select></label>}</Content>
      {message && <p role="alert">{message}</p>}
    </Panel>
    {report && <Panel title="Held-out performance" subtitle={report.trial_count + " trials · seed " + report.master_seed}>
      <p className="diagnosis-summary">{report.families.join(" · ")}</p>
      <p>{Object.entries(report.distribution_per_family).map(([name, count]) => name.replaceAll("_", " ") + " " + count + " per family").join(" · ")}</p>
      <p>Intervals describe variation across modeled workloads. Results depend on the chosen traffic and failure assumptions.</p>
      <div className="controls diagnosis-summary"><label>Metric <select value={metric} onChange={event => setMetric(event.target.value)}>
        {Object.keys(report.held_out.baseline).map(key => <option key={key} value={key}>{key.replaceAll("_", " ")}</option>)}
      </select></label><a href={"/api/cloud/benchmarks/" + report.id + "/export/json"}>Export JSON</a>
        <a href={"/api/cloud/benchmarks/" + report.id + "/export/csv"}>Export CSV</a></div>
      <div className="table-wrap"><table><thead><tr><th>Policy</th><th>Samples</th><th>Mean</th><th>Median</th>
        <th>5th / 95th percentile</th><th>95% confidence interval</th><th>Below baseline</th></tr></thead>
        <tbody>{Object.entries(report.held_out).map(([policy, metrics]) => {
          const stat = metrics[metric];
          const ratio = ["request_success", "paired_success_delta", "harmful", "false_positive", "false_negative"].includes(metric);
          const format = (value?: number) => value === undefined ? "—" : ratio ? (value * 100).toFixed(2) + "%" : value.toFixed(2);
          return <tr key={policy}><td className="capitalize">{policy.replaceAll("_", " ")}</td><td>{stat.n}</td>
            <td>{format(stat.mean)}</td><td>{format(stat.median)}</td><td>{format(stat.p05)} / {format(stat.p95)}</td>
            <td>{stat.ci95?.map(format).join(" to ") || "—"}</td>
            <td>{((metrics.harmful.mean ?? 0) * 100).toFixed(1)}%</td></tr>;
        })}</tbody></table></div>
    </Panel>}
  </>;
}

const roles = ["viewer", "operator", "administrator"];

function Accounts() {
  const [revision, setRevision] = useState(0);
  const accounts = useData<Account[]>("/identity/accounts", revision);
  const events = useData<{ id: number; actor: string; action: string; time: string }[]>("/identity/events", revision);
  const { busy, message, run, setMessage } = useAction();
  return <>
    <Panel title="Operator accounts">
      <Content result={accounts}>{rows => <>
        <form className="form" onSubmit={event => {
          event.preventDefault();
          const form = event.currentTarget;
          const data = Object.fromEntries(new FormData(form));
          void run(async () => {
            await change("/identity/accounts", data);
            form.reset(); setRevision(value => value + 1); setMessage("Account created.");
          });
        }}>
          <label>New username<input required name="username" pattern="[a-z][a-z0-9_\-]{2,47}" /></label>
          <label>Initial password<input required name="password" type="password" minLength={12} maxLength={128} autoComplete="new-password" /></label>
          <label>New account role<select name="role">{roles.map(role => <option key={role}>{role}</option>)}</select></label>
          <button disabled={busy}>Create account</button>
        </form>
        <div className="table-wrap"><table><thead><tr><th>Username</th><th>Role and access</th></tr></thead>
          <tbody>{rows.map(row => <tr key={row.username + row.role + row.active}><td>{row.username}</td><td>
            <form className="controls" onSubmit={event => {
              event.preventDefault();
              const data = new FormData(event.currentTarget);
              void run(async () => {
                await change("/identity/accounts/" + row.username,
                  { role: data.get("role"), active: data.get("active") === "on" }, "PUT");
                setRevision(value => value + 1); setMessage("Account updated.");
              });
            }}><select aria-label={"Role for " + row.username} name="role" defaultValue={row.role}>
              {roles.map(role => <option key={role}>{role}</option>)}</select>
              <label><input type="checkbox" name="active" defaultChecked={row.active} /> Active</label>
              <button className="secondary" disabled={busy}>Save role and access</button></form>
          </td></tr>)}</tbody></table></div>
      </>}</Content>
      {message && <p role="status">{message}</p>}
    </Panel>
    <Panel title="Authorization events"><Content result={events}>{rows =>
      rows.length ? <ul>{rows.map(row => <li key={row.id}>{row.actor} · {row.action.replaceAll("_", " ")} · {new Date(row.time).toLocaleString()}</li>)}</ul>
        : <p className="message">No authorization events.</p>
    }</Content></Panel>
  </>;
}

function Audit() {
  const [checkpoint, setCheckpoint] = useState("");
  const [result, setResult] = useState<Verification>();
  const { busy, message, run } = useAction();
  return <Panel title="Audit-chain integrity" subtitle="Compare against a checkpoint stored independently of the database.">
    <a href="/api/cloud/audit-chain/export" download="cloudrescue-audit.json">Export audit records</a>
    <form className="form" onSubmit={event => {
      event.preventDefault();
      void run(async () => setResult(await change("/audit-chain/verify", checkpoint.trim() ? JSON.parse(checkpoint) : null)));
    }}>
      <label>Independent checkpoint JSON<textarea rows={4} value={checkpoint}
        onChange={event => setCheckpoint(event.target.value)} /></label>
      <button disabled={busy}>Verify integrity</button>
    </form>
    {message && <p role="alert">{message}</p>}
    {result && <div role="status" className="diagnosis-summary">
      {result.valid ? <><p>{result.anchored ? "Chain and checkpoint verified." : "Chain links verified."}</p>
        <a download="cloudrescue-checkpoint.json" href={"data:application/json," +
          encodeURIComponent(JSON.stringify({ count: result.count, digest: result.digest }))}>Save current checkpoint</a></>
        : <p>Verification failed {result.failure_at ? "at record " + result.failure_at : ""} · {result.reason}</p>}
    </div>}
  </Panel>;
}
