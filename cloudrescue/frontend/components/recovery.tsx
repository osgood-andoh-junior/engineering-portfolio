"use client";

import Link from "next/link";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Content, Panel, request, useData } from "./dashboard-data";

const headers = { "Content-Type": "application/json", "x-cloudrescue-action": "fault" };
const policyNames: Record<string, string> = {
  baseline: "No intervention", retry: "Retry only", breaker: "Circuit breaker",
  limit: "Rate limiting", failover: "Simulated failover", combined: "Combined",
  manual: "Manual intervention", investigate: "Human investigation",
};
const scenarios: Record<string, string> = {
  primary: "Primary outage", upstream: "Shared upstream outage", overload: "Overload",
  transient: "Transient transport errors", healthy_burst: "Healthy traffic burst", replay: "Saved incident replay",
};

type Section = "recovery" | "policy-lab" | "reliability" | "audit";
type Approval = {
  id: number; incident_id: number; target: string; action: string; operator: string;
  status: string; requested_at: string; approved_at: string | null; evidence: object | null;
};
type Center = { enabled: boolean; configured: boolean; operator: string; incidents: { id: number; target: string }[] };
type Recommendation = { strategy: string; reason: string; risk: string; candidates: { service: string; reason: string }[] };
type Catalog = {
  strategies: string[]; scenarios: string[]; parameters: Record<string, number>;
  parameter_schema: Record<string, { minimum: number; maximum: number }>;
};
type Metrics = {
  policy: string; request_success: number; downtime_seconds: number; mttd_seconds: number | null;
  diagnosis_seconds: number | null; mttr_seconds: number | null; recovered: boolean | null;
  error_budget_consumption: number; intervention_attempts: number; overhead_ms: number;
  failed_interventions: number; harmful: boolean; upstream_attempts: number;
};
type Experiment = { id: number; version: number; seed: number; scenario: string; results: Metrics[] };
type Analytics = {
  modeled: Record<string, { request_success: number; harmful_scenarios: number }>;
  observed: {
    incidents: number; closed: number; mttd_seconds: number | null; mttr_seconds: number | null;
    execution_success: number | null; execution_samples: number;
    durations: { id: number; target: string; seconds: number }[];
    error_trend: { hour: string; checks: number; error_rate: number }[];
  };
};
type Event = {
  id: number; approval_id: number | null; event: string; operator: string; occurred_at: string;
  evidence: object; action: string | null; target: string | null; approved_at: string | null;
};

function post<T>(path: string, body?: object) {
  return request<T>("/recovery/" + path, {
    method: "POST", headers, body: body ? JSON.stringify(body) : undefined,
  });
}

function useAction() {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  async function run(action: () => Promise<void>) {
    setBusy(true);
    setMessage("");
    try { await action(); } catch (error) {
      setMessage(error instanceof Error ? error.message : "Request failed.");
    } finally { setBusy(false); }
  }
  return { busy, message, run, setMessage };
}

export function RecoveryPages({ section, signedIn }: { section: Section; signedIn: boolean }) {
  if (!signedIn) return <Panel title="Administrator access"><p className="message">
    <Link href="/simulation">Sign in with the local administrator token</Link> to use recovery tools.</p></Panel>;
  if (section === "policy-lab") return <PolicyLab />;
  if (section === "reliability") return <Reliability />;
  if (section === "audit") return <Audit />;
  return <RecoveryCenter />;
}

function RecoveryCenter() {
  const [revision, setRevision] = useState(0);
  const center = useData<Center>("/recovery/center", revision);
  const approvals = useData<Approval[]>("/recovery/approvals", revision);
  const [incident, setIncident] = useState("");
  const [action, setAction] = useState("reset_fault");
  const [target, setTarget] = useState("");
  const [recommendation, setRecommendation] = useState<{ id: string; data: Recommendation }>();
  const [confirm, setConfirm] = useState<number>();
  const [stop, setStop] = useState(false);
  const { busy, message, run, setMessage } = useAction();
  const current = center?.data?.incidents.find(row => String(row.id) === incident);
  const diagnosis = recommendation?.id === incident ? recommendation.data : undefined;
  const refresh = () => setRevision(value => value + 1);
  function ask() {
    if (!current) return;
    void run(async () => {
      await post("approvals", { key: crypto.randomUUID(), incident_id: current.id,
        target: target || current.target, action });
      refresh();
      setMessage("Intervention requested. Confirm it in the approval list.");
    });
  }
  return <>
    <Panel title="Active incidents">
      <Content result={center}>{data => <div className="form">
        <p>{data.enabled ? "Local execution enabled" : "Local execution disabled or stopped"} · {data.operator}</p>
        {data.incidents.length ? <label>Incident<select aria-label="Incident" value={incident}
          onChange={event => { setIncident(event.target.value); setTarget(""); }}>
          <option value="">Select an active incident</option>
          {data.incidents.map(row => <option key={row.id} value={row.id}>#{row.id} · {row.target}</option>)}
        </select></label> : <p>No active incidents.</p>}
        <button disabled={!current || busy} onClick={() => void run(async () => {
          setRecommendation({ id: incident, data: await post("recommendations/" + incident) });
        })}>Review recommendation</button>
        {diagnosis && <article className="finding"><h3>{policyNames[diagnosis.strategy]}</h3>
          <p>{diagnosis.reason}</p><p>{diagnosis.risk}</p>
          <ul>{diagnosis.candidates.map(item => <li key={item.service}>{item.service} · {item.reason}</li>)}</ul>
        </article>}
        {current && data.enabled && <>
          <label>Target<select aria-label="Target" value={target || current.target} onChange={event => setTarget(event.target.value)}>
            {[...new Set([current.target, ...(diagnosis?.candidates.map(item => item.service) || [])])].map(name =>
              <option key={name}>{name}</option>)}
          </select></label>
          <label>Intervention<select aria-label="Intervention" value={action} onChange={event => setAction(event.target.value)}>
            <option value="reset_fault">Reset injected fault</option><option value="restart">Simulated restart</option>
          </select></label>
          <button className="secondary" disabled={busy} onClick={ask}>Request intervention</button>
        </>}
        {data.configured && <button className="secondary" onClick={() => setStop(true)}>
          {data.enabled ? "Emergency stop" : "Resume local execution"}</button>}
        {stop && <div className="controls"><span>{data.enabled ? "Block further local interventions?" :
          "Resume local execution and require new approvals?"}</span>
          <button disabled={busy} onClick={() => void run(async () => {
            await post(data.enabled ? "stop" : "resume", { confirm: true }); setStop(false); refresh();
          })}>{data.enabled ? "Confirm emergency stop" : "Confirm resume"}</button>
          <button className="secondary" onClick={() => setStop(false)}>Cancel</button></div>}
        {message && <p role="status">{message}</p>}
      </div>}</Content>
    </Panel>
    <Panel title="Intervention approvals"><Content result={approvals}>{rows =>
      rows.length ? <div className="table-wrap"><table><thead><tr>
        <th>Intervention</th><th>Target</th><th>Status</th><th>Approval</th>
      </tr></thead><tbody>{rows.map(row => <tr key={row.id}>
        <td>#{row.id} · {row.action.replaceAll("_", " ")}</td><td>{row.target}</td>
        <td>{row.status.replaceAll("_", " ")}</td><td>
          {row.status === "awaiting_approval" && center?.data?.enabled && (confirm === row.id ?
            <div className="controls"><button disabled={busy} onClick={() => void run(async () => {
              await post("approvals/" + row.id + "/execute", { confirm: true });
              setConfirm(undefined); refresh(); setMessage("Action applied. Awaiting monitoring verification.");
            })}>Confirm and execute #{row.id}</button>
            <button className="secondary" onClick={() => setConfirm(undefined)}>Cancel</button></div> :
            <button className="secondary" onClick={() => setConfirm(row.id)}>Review approval #{row.id}</button>)}
          {row.approved_at && new Date(row.approved_at).toLocaleString()}
        </td>
      </tr>)}</tbody></table></div> : <p className="message">No interventions recorded.</p>
    }</Content></Panel>
  </>;
}

function PolicyLab() {
  const catalog = useData<Catalog>("/recovery/policies");
  return <Content result={catalog}>{data => <ExperimentRunner catalog={data} />}</Content>;
}

function ExperimentRunner({ catalog }: { catalog: Catalog }) {
  const [scenario, setScenario] = useState("primary");
  const [seed, setSeed] = useState(42);
  const [replay, setReplay] = useState("");
  const [revision, setRevision] = useState(0);
  const saved = useData<Experiment[]>("/recovery/experiments", revision);
  const [parameters, setParameters] = useState(catalog.parameters);
  const [result, setResult] = useState<Experiment>();
  const { busy, message, run } = useAction();
  return <>
    <Panel title="Experiment runner" subtitle="Each comparison uses the same seed, topology, and request trace.">
      <form className="form" onSubmit={event => {
        event.preventDefault();
        void run(async () => {
          setResult(await post("experiments", { scenario, seed, parameters,
            ...(scenario === "replay" ? { replay_id: Number(replay) } : {}) }));
          setRevision(value => value + 1);
        });
      }}>
        <p>{catalog.strategies.map(name => policyNames[name]).join(" · ")}</p>
        <div className="controls">
          <label>Scenario<select aria-label="Scenario" value={scenario} onChange={event => setScenario(event.target.value)}>
            {catalog.scenarios.map(value => <option key={value} value={value}>{scenarios[value]}</option>)}
          </select></label>
          <label>Seed<input type="number" required min={0} max={2147483647} value={seed} onChange={event => setSeed(Number(event.target.value))} /></label>
          {scenario === "replay" && <label>Saved replay ID<input required min={1} type="number" value={replay}
            onChange={event => setReplay(event.target.value)} /></label>}
        </div>
        <fieldset className="policy-parameters">
          <legend>Policy parameters</legend>
          {Object.entries(parameters).map(([name, value]) => <label key={name}>
            <span className="capitalize">{name.replaceAll("_", " ")}</span>
            <input required type="number" value={value} min={catalog.parameter_schema[name].minimum}
              max={catalog.parameter_schema[name].maximum} onChange={event =>
                setParameters(previous => ({ ...previous, [name]: Number(event.target.value) }))} />
          </label>)}
        </fieldset>
        <button disabled={busy}>Run experiment</button>
        <button type="button" className="secondary" disabled={busy} onClick={() => void run(async () => {
          await request("/recovery/policies", { method: "PUT", headers, body: JSON.stringify(parameters) });
          setRevision(value => value + 1);
        })}>Publish Policy Lab defaults</button>
        {message && <p role="alert">{message}</p>}
      </form>
      <Content result={saved}>{rows => rows.length ? <div className="controls diagnosis-summary">
        <label>Saved experiment<select aria-label="Saved experiment" value={result?.id ?? ""} onChange={event => {
          const id = event.target.value;
          if (id) void run(async () => setResult(await request("/recovery/experiments/" + id)));
        }}><option value="">Choose an experiment</option>{rows.map(row =>
          <option key={row.id} value={row.id}>#{row.id} · {scenarios[row.scenario]} · seed {row.seed}</option>)}</select></label>
      </div> : <p className="message">No saved experiments.</p>}</Content>
    </Panel>
    {result && <Panel title="Modeled policy comparison" subtitle={scenarios[result.scenario] + " · seed " + result.seed + " · version " + result.version}>
      <SuccessChart data={result.results.map(row => ({ name: policyNames[row.policy], success: row.request_success }))} />
      <div className="table-wrap"><table><thead><tr><th>Policy</th><th>Success</th><th>Downtime</th>
        <th>Detect / diagnose / recover</th><th>Budget used</th><th>Attempts</th><th>Retry wait</th><th>Failed retries</th><th>Impact</th>
      </tr></thead><tbody>{result.results.map(row => <tr key={row.policy}>
        <td>{policyNames[row.policy]}</td><td>{percent(row.request_success)}</td><td>{row.downtime_seconds}s</td>
        <td>{[row.mttd_seconds, row.diagnosis_seconds, row.mttr_seconds].map(seconds).join(" / ")}</td>
        <td>{percent(row.error_budget_consumption)}</td><td>{row.intervention_attempts}</td>
        <td>{row.overhead_ms.toFixed(0)} ms</td><td>{row.failed_interventions}</td>
        <td>{row.harmful ? "Worse than baseline" : "At or above baseline"}</td>
      </tr>)}</tbody></table></div>
    </Panel>}
  </>;
}

const percent = (value: number | null) => value === null ? "—" : (value * 100).toFixed(1) + "%";
const seconds = (value: number | null) => value === null ? "—" : value.toFixed(1) + "s";

function SuccessChart({ data }: { data: { name: string; success: number }[] }) {
  return <div className="chart"><ResponsiveContainer width="100%" height="100%" minWidth={0}>
    <BarChart data={data} margin={{ top: 10, right: 16, bottom: 12 }}>
      <CartesianGrid vertical={false} stroke="#243043" /><XAxis dataKey="name" tick={{ fill: "#a1aec5", fontSize: 11 }} />
      <YAxis domain={[0, 1]} tickFormatter={percent} tick={{ fill: "#a1aec5", fontSize: 11 }} />
      <Tooltip formatter={value => [percent(Number(value)), "Request success"]}
        contentStyle={{ background: "#111a28", borderColor: "#354257" }} />
      <Bar dataKey="success" fill="#82afff" isAnimationActive={false} />
    </BarChart>
  </ResponsiveContainer></div>;
}

function Reliability() {
  const analytics = useData<Analytics>("/recovery/analytics");
  return <Content result={analytics}>{data => <>
    <Panel title="Observed simulator reliability" subtitle="Incidents and checks from the last seven days.">
      <dl><div><dt>Incidents / closed</dt><dd>{data.observed.incidents} / {data.observed.closed}</dd></div>
        <div><dt>Mean time to detect</dt><dd>{seconds(data.observed.mttd_seconds)}</dd></div>
        <div><dt>Mean time to recover</dt><dd>{seconds(data.observed.mttr_seconds)}</dd></div>
        <div><dt>Verified execution success ({data.observed.execution_samples} total terminal)</dt><dd>{percent(data.observed.execution_success)}</dd></div>
      </dl>
      <h3 className="diagnosis-summary">Recent closed incident durations</h3>
      <ul>{data.observed.durations.map(row => <li key={row.id}>#{row.id} · {row.target} · {seconds(row.seconds)}</li>)}</ul>
      <h3 className="diagnosis-summary">Recent check error trend</h3>
      <div className="table-wrap"><table><thead><tr><th>Hour</th><th>Checks</th><th>Error rate</th></tr></thead>
        <tbody>{data.observed.error_trend.map(row => <tr key={row.hour}>
          <td>{new Date(row.hour).toLocaleString()}</td><td>{row.checks}</td><td>{percent(row.error_rate)}</td>
        </tr>)}</tbody></table></div>
    </Panel>
    <Panel title="Modeled policy effectiveness" subtitle="Request-weighted results across the five benchmark scenarios.">
      <SuccessChart data={Object.entries(data.modeled).map(([name, result]) =>
        ({ name: policyNames[name], success: result.request_success }))} />
      <ul>{Object.entries(data.modeled).map(([name, result]) => <li key={name}>
        {policyNames[name]} · {percent(result.request_success)} success · {result.harmful_scenarios} scenarios below baseline</li>)}</ul>
    </Panel>
  </>}</Content>;
}

function Audit() {
  const events = useData<Event[]>("/recovery/audit");
  return <Panel title="Recovery audit trail"><Content result={events}>{rows => rows.length ?
    <div className="table-wrap"><table><thead><tr>
      <th>Event</th><th>Operator</th><th>Action / target</th><th>Approved at</th><th>Recorded at</th><th>Evidence</th>
    </tr></thead><tbody>{rows.map(row => <tr key={row.id}>
      <td>{row.event.replaceAll("_", " ")} {row.approval_id && "#" + row.approval_id}</td>
      <td>{row.operator}</td><td>{row.action?.replaceAll("_", " ") || "—"} / {row.target || "—"}</td>
      <td>{row.approved_at ? new Date(row.approved_at).toLocaleString() : "—"}</td>
      <td>{new Date(row.occurred_at).toLocaleString()}</td>
      <td><details><summary>Details</summary><pre>{JSON.stringify(row.evidence, null, 2)}</pre></details></td>
    </tr>)}</tbody></table></div> : <p className="message">No recovery audit events.</p>}
  </Content></Panel>;
}
