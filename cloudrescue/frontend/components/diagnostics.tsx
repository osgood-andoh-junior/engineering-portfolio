"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { Content, Panel, request, useData } from "./dashboard-data";

type Edge = [string, string];
type Graph = { version: number; edges: Edge[]; services: string[] };
type Evidence = {
  service: string; time: number; available: boolean; latency_ms: number;
  status_code: number | null; blocked_by: string | null; check_id: number | null;
};
type Candidate = {
  service: string; confidence: number; symptoms: string[]; reason: string;
  possible_cascade: string[]; evidence: Evidence[];
};
type Analysis = {
  status: string; candidates: Candidate[]; affected: string[];
  graph_version?: number | null;
  ground_truth?: (string | { service: string; mode: string; occurred_at: string })[];
};
type Frame = Analysis & { time: number; observations: Evidence[] };
type Replay = Analysis & {
  title: string; frames: Frame[]; predictions: Record<string, number>;
  first_detection: Record<string, number>; first_diagnosis: Record<string, number>;
  injected_faults?: Record<string, [string, number]>;
};
type Scenario = { id: string; title: string };
type Saved = Scenario & { source: string };
type Evaluation = {
  accuracy: number; precision: number | null; recall: number | null; false_positive_rate: number | null;
  exact_matches: number; mean_detection_seconds: number | null; mean_diagnosis_seconds: number | null;
  detection_samples: number; diagnosis_samples: number; calibration_reason: string;
  scenarios: (Scenario & Pick<Replay, "ground_truth" | "predictions" | "first_detection">)[];
};

function percent(value: number | null) {
  return value === null ? "—" : Math.round(value * 100) + "%";
}

function truthNames(groundTruth: Analysis["ground_truth"]) {
  return groundTruth?.map(value => typeof value === "string" ? value : value.service + " (" + value.mode + ")").join(", ") ||
    "No matching fault record or expected major cause";
}

export function Findings({ analysis }: { analysis: Analysis }) {
  return <>
    <p className="diagnosis-summary">Affected services · {analysis.affected.join(", ") || "None observed"}</p>
    {analysis.candidates.length === 0 && <p className="message">Insufficient evidence to identify a suspected cause.</p>}
    {analysis.candidates.map(candidate => <article className="finding" key={candidate.service}>
      <h3>{candidate.service} · {percent(candidate.confidence)} rule confidence</h3>
      <p>{candidate.reason}</p>
      <p>Observed downstream symptoms · {candidate.symptoms.join(", ") || "None"}</p>
      <p>Potential downstream impact · {candidate.possible_cascade.join(", ") || "None"}</p>
      <ul>{candidate.evidence.map(row => <li key={row.service}>
        {row.service} at {row.time.toFixed(2)}s · {row.status_code ?? "No HTTP response"} · {row.latency_ms.toFixed(1)} ms
        {row.blocked_by && " · blocked by " + row.blocked_by}
        {row.check_id && " · check #" + row.check_id}
      </li>)}</ul>
    </article>)}
  </>;
}

export function IncidentDiagnosis({ id }: { id: number }) {
  const data = useData<Analysis>("/incidents/" + id + "/diagnosis");
  return <Panel title="Root-cause analysis" subtitle="Rule-based inference from recorded local health checks.">
    <Content result={data}>{analysis => <>
      <p className="diagnosis-summary">Topology version · {analysis.graph_version ?? "Unavailable"}</p>
      <Findings analysis={analysis} />
      <h3 className="diagnosis-summary">Recorded fault injections at onset</h3>
      <p>{truthNames(analysis.ground_truth)}</p>
    </>}</Content>
  </Panel>;
}

export function Topology({ signedIn }: { signedIn: boolean }) {
  const [revision, setRevision] = useState(0);
  const data = useData<Graph>("/dependencies", revision);
  return <Panel title="Service dependency graph" subtitle="Arrows point from each dependent to its upstream service.">
    <Content result={data}>{graph => <GraphEditor key={graph.version} graph={graph} signedIn={signedIn}
      refresh={() => setRevision(value => value + 1)} />}</Content>
  </Panel>;
}

function GraphEditor({ graph, signedIn, refresh }: { graph: Graph; signedIn: boolean; refresh: () => void }) {
  const [edges, setEdges] = useState(graph.edges);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState<Graph>();
  const [version, setVersion] = useState(String(graph.version));
  async function publish() {
    setBusy(true);
    try {
      await request("/dependencies", { method: "PUT", headers: writeHeaders,
        body: JSON.stringify({ expected_version: graph.version, edges }) });
      setMessage("Dependency graph published.");
      refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Publication failed.");
    } finally { setBusy(false); }
  }
  async function load(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      setHistory(await request<Graph>("/dependencies/" + Number(version)));
      setMessage("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Version unavailable.");
    }
  }
  const displayed = history ?? graph;
  const positions = Object.fromEntries(displayed.services.map((service, index) => [
    service, [index === 0 ? 320 : index === 1 ? 160 : 480, index === 0 ? 55 : 172],
  ]));
  return <>
    <svg className="dependency-diagram" viewBox="0 0 640 225" role="img"
      aria-label={"Topology version " + displayed.version + ": " + displayed.edges.map(edge => edge.join(" depends on ")).join(", ")}>
      <defs><marker id="arrow" markerWidth="9" markerHeight="9" refX="8" refY="4" orient="auto">
        <path d="M0 0L8 4L0 8z" fill="#82afff" /></marker></defs>
      {displayed.edges.map(([child, parent]) => {
        const [x1, y1] = positions[child], [x2, y2] = positions[parent];
        const ratio = Math.min(80 / Math.abs(x2 - x1), 26 / Math.abs(y2 - y1));
        return <line key={child + parent} x1={x1 + (x2 - x1) * ratio} y1={y1 + (y2 - y1) * ratio}
          x2={x2 + (x1 - x2) * ratio} y2={y2 + (y1 - y2) * ratio}
          stroke="#82afff" strokeWidth="2" markerEnd="url(#arrow)" />;
      })}
      {displayed.services.map(service => {
        const [x, y] = positions[service];
        return <g key={service}><rect x={x - 79} y={y - 24} width="158" height="48" rx="8" fill="#172942" stroke="#456188" />
          <text x={x} y={y + 5} fill="#e8edf7" textAnchor="middle" className="capitalize">{service}</text></g>;
      })}
    </svg>
    <form className="controls diagnosis-summary" onSubmit={load}>
      <label>Graph version <input type="number" min="1" required value={version} onChange={event => setVersion(event.target.value)} /></label>
      <button className="secondary">View version</button>
      {history && <button type="button" className="secondary" onClick={() => setHistory(undefined)}>Show current</button>}
    </form>
    {signedIn ? <fieldset className="graph-edit" disabled={busy}>
      <legend>Edit current version {graph.version}</legend>
      {graph.services.flatMap(child => graph.services.filter(parent => parent !== child).map(parent => {
        const active = edges.some(edge => edge[0] === child && edge[1] === parent);
        return <label key={child + parent}><input type="checkbox" checked={active} onChange={() =>
          setEdges(active ? edges.filter(edge => edge[0] !== child || edge[1] !== parent) : [...edges, [child, parent]])} />
          {child} depends on {parent}</label>;
      }))}
      <button onClick={() => void publish()}>Publish dependencies</button>
    </fieldset> : <p className="diagnosis-summary"><Link href="/simulation">Sign in</Link> to publish dependencies.</p>}
    {message && <p className="diagnosis-summary" role="status">{message}</p>}
  </>;
}

const writeHeaders = { "Content-Type": "application/json", "x-cloudrescue-action": "fault" };

export function ReplayPage({ signedIn }: { signedIn: boolean }) {
  const scenarios = useData<Scenario[]>("/scenarios");
  const [revision, setRevision] = useState(0);
  const saved = useData<Saved[]>("/replays", revision);
  const [data, setData] = useState<Replay>();
  const [source, setSource] = useState("cascade");
  const [id, setId] = useState("");
  const [index, setIndex] = useState(0);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  async function run(path: string, init?: RequestInit) {
    setBusy(true);
    setMessage("");
    try {
      setData(await request<Replay>(path, init));
      setIndex(0);
      if (init) setRevision(value => value + 1);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Replay unavailable.");
    } finally { setBusy(false); }
  }
  const frame = data?.frames[index];
  async function runLive() {
    setBusy(true);
    setMessage("");
    try {
      const result = await request<{ expires_at: string }>("/scenarios/" + source + "/run", {
        method: "POST", headers: writeHeaders,
      });
      setMessage("Local faults scheduled until " + new Date(result.expires_at).toLocaleTimeString() + ".");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Local scenario failed.");
    } finally { setBusy(false); }
  }
  return <>
    <Panel title="Load replay" subtitle="Seeded experiments and recorded observations use isolated replay sessions.">
      <div className="form">
        <label>Scenario<select aria-label="Scenario" value={source} onChange={event => setSource(event.target.value)}>
          {scenarios?.data?.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}
          <option value="incident">Recorded incident</option>
        </select></label>
        {source === "incident" && <label>Incident ID<input type="number" min="1" value={id} onChange={event => setId(event.target.value)} /></label>}
        <div className="controls">
          {source !== "incident" && <button disabled={busy || !scenarios?.data} onClick={() => void run("/scenarios/" + source)}>Preview scenario</button>}
          {source !== "incident" && <button className="secondary" disabled={busy || !signedIn || !scenarios?.data}
            onClick={() => void runLive()}>Run on local simulators</button>}
          <button disabled={busy || !signedIn || (source === "incident" && Number(id) <= 0)} onClick={() => void run("/replays", {
            method: "POST", headers: writeHeaders,
            body: JSON.stringify({ source, ...(source === "incident" && { incident_id: Number(id) }) }),
          })}>Save replay</button>
        </div>
        {!signedIn && <p><Link href="/simulation">Sign in</Link> to save a replay.</p>}
        {message && <p role="status">{message}</p>}
      </div>
      <Content result={saved}>{items => items.length ? <div className="controls diagnosis-summary">
        {items.map(item => <button className="secondary" key={item.id} disabled={busy} onClick={() => void run("/replays/" + item.id)}>
          #{item.id} {item.title}</button>)}
      </div> : <p className="message">No saved replay sessions.</p>}</Content>
    </Panel>
    {data && <Panel title={data.title} subtitle={"Simulated ground truth · " + truthNames(data.ground_truth)}>
      {data.injected_faults && <p className="diagnosis-summary">Scripted injection · {
        Object.entries(data.injected_faults).map(([service, [mode, latency]]) =>
          service + " " + mode + (latency ? " (" + latency + " ms)" : "")).join(", ")
      }</p>}
      {frame ? <>
        <div className="controls diagnosis-summary">
          <button className="secondary" onClick={() => setIndex(index - 1)} disabled={!index}>Previous frame</button>
          <strong>Frame {index + 1} of {data.frames.length} · {frame.time.toFixed(2)}s</strong>
          <button className="secondary" onClick={() => setIndex(index + 1)} disabled={index + 1 >= data.frames.length}>Next frame</button>
        </div>
        <label className="diagnosis-summary">Replay frame <input aria-label="Replay frame" type="range" min={0}
          max={data.frames.length - 1} value={index} onChange={event => setIndex(Number(event.target.value))} /></label>
        <ul className="diagnosis-summary">{frame.observations.map(row => <li key={row.service}>
          {row.service} · {row.status_code ?? "Connection failure"} · {row.latency_ms.toFixed(1)} ms
          {row.blocked_by && " · blocked by " + row.blocked_by}
        </li>)}</ul>
        <Findings analysis={frame} />
      </> : <p className="message">No replay frames.</p>}
      <p className="diagnosis-summary">Predicted across replay · {Object.keys(data.predictions).join(", ") || "No major cause"}</p>
    </Panel>}
  </>;
}

export function EvaluationPage() {
  const data = useData<Evaluation>("/evaluation");
  return <Panel title="Seeded diagnostic evaluation" subtitle="Results from five synthetic local scenarios.">
    <Content result={data}>{results => <>
      <dl>
        <div><dt>Exact root-cause match</dt><dd>{percent(results.accuracy)} ({results.exact_matches}/{results.scenarios.length})</dd></div>
        <div><dt>Precision</dt><dd>{percent(results.precision)}</dd></div>
        <div><dt>Recall</dt><dd>{percent(results.recall)}</dd></div>
        <div><dt>False-positive rate</dt><dd>{percent(results.false_positive_rate)}</dd></div>
        <div><dt>Mean detection delay ({results.detection_samples} samples)</dt><dd>{results.mean_detection_seconds ?? "—"}s</dd></div>
        <div><dt>Mean diagnosis delay ({results.diagnosis_samples} samples)</dt><dd>{results.mean_diagnosis_seconds ?? "—"}s</dd></div>
      </dl>
      <p className="diagnosis-summary">{results.calibration_reason}</p>
      <div className="table-wrap"><table><thead><tr><th>Scenario</th><th>Expected causes</th><th>Predicted causes</th></tr></thead>
        <tbody>{results.scenarios.map(item => <tr key={item.id}><td>{item.title}</td>
          <td>{truthNames(item.ground_truth)}</td><td>{Object.keys(item.predictions).join(", ") || "None"}</td></tr>)}</tbody>
      </table></div>
    </>}</Content>
  </Panel>;
}
