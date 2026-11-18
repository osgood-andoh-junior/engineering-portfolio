"use client";

import Link from "next/link";
import { Activity, Bell, ChevronRight, CircleCheck, Cloud, Database, FlaskConical, Gauge,
  LayoutDashboard, Network, Radio, RotateCcw, Server, Settings2, Shield, TriangleAlert, XCircle } from "lucide-react";
import { useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Content, Panel, request, useData } from "./dashboard-data";
import { EvaluationPage, IncidentDiagnosis, ReplayPage, Topology } from "./diagnostics";
import { RecoveryPages } from "./recovery";
import { ValidationPages } from "./validation";
import {
  duration, labels, sections, type Check, type Detail, type Incident, type IncidentDetail,
  type Metrics, type Mode, type Section, type Service, type Settings, type State, type Summary,
} from "../lib/types";

const icons = [LayoutDashboard, Server, Bell, Gauge, FlaskConical, Network, RotateCcw, Activity,
  Shield, FlaskConical, Gauge, Database, FlaskConical, Shield, CircleCheck, Activity, Settings2];
const descriptions: Record<Section, string> = {
  overview: "Monitor service health and incident activity across your local environment.",
  services: "Inspect the three simulated services and their latest health checks.",
  incidents: "Review detected outages, recovery milestones, and supporting checks.",
  metrics: "Explore response latency and failure rates from collected health checks.",
  simulation: "Change how local services respond to health checks.",
  dependencies: "Inspect the versioned topology used by the local simulators.",
  replay: "Step through observations and compare inferences with simulated ground truth.",
  evaluation: "Review diagnostic results and timing across the seeded experiments.",
  recovery: "Review incident evidence and authorize local simulator interventions.",
  "policy-lab": "Compare recovery policies on the same modeled request traffic.",
  reliability: "Review observed simulator incidents and modeled policy effectiveness.",
  audit: "Inspect operator approvals, actions, and monitoring evidence.",
  "benchmark-lab": "Run seeded workload comparisons and inspect confidence intervals.",
  security: "Manage local identities and review authorization events.",
  "audit-verification": "Export and verify the integrity of recorded actions.",
  "reliability-report": "Review held-out policy results and performance distributions.",
  settings: "View the active monitoring configuration for this environment.",
};

function date(value: string | null) {
  return value ? new Date(value).toLocaleString() : "—";
}

function Badge({ state }: { state: State }) {
  return <span className={"badge " + state}><i />{labels[state]}</span>;
}

export function Dashboard({ section, signedIn, invalidLogin }: {
  section: Section; signedIn: boolean; invalidLogin: boolean;
}) {
  const summary = useData<Summary>("/summary");
  const title = sections.find(([key]) => key === section)?.[1];
  const lastCheck = summary?.data?.last_check_at;
  const stale = lastCheck && (summary?.receivedAt ?? 0) - Date.parse(lastCheck) > 60000;
  const signal = summary?.error ? "API unavailable" : stale ? "Checks delayed" :
    lastCheck ? "Monitoring active" : "Awaiting checks";

  return <div className="shell">
    <aside className="sidebar">
      <Link className="brand" href="/"><span className="brand-icon"><Cloud size={21} /></span>
        <span>CloudRescue<small>Reliability simulator</small></span></Link>
      <nav aria-label="Dashboard">{sections.map(([key, name], index) => {
        const Icon = icons[index];
        return <Link href={key === "overview" ? "/" : "/" + key} key={key}
          aria-current={key === section ? "page" : undefined}><Icon size={17} />{name}</Link>;
      })}</nav>
      <div className="environment"><span className="environment-icon"><Shield size={17} /></span>
        <span>Local sandbox<small>Synthetic telemetry</small></span></div>
    </aside>
    <main>
      <div className="topbar"><span>Workspace <ChevronRight size={13} /> <strong>{title}</strong></span>
        <span className={"signal " + (lastCheck && !stale && !summary?.error ? "online" : "")}><i />{signal}</span></div>
      <div className="page">
        <div className="page-heading"><h1>{title}</h1><p>{descriptions[section]}</p></div>
        {section === "overview" && <><Content result={summary}>{data => <SummaryCards data={data} />}</Content>
          <Telemetry /><IncidentList recent /></>}
        {section === "services" && <Services />}
        {section === "incidents" && <IncidentList />}
        {section === "metrics" && <Telemetry filter />}
        {section === "simulation" && <Simulation signedIn={signedIn} invalidLogin={invalidLogin} />}
        {section === "dependencies" && <Topology signedIn={signedIn} />}
        {section === "replay" && <ReplayPage signedIn={signedIn} />}
        {section === "evaluation" && <EvaluationPage />}
        {(section === "recovery" || section === "policy-lab" || section === "reliability" ||
          section === "audit") && <RecoveryPages section={section} signedIn={signedIn} />}
        {(section === "benchmark-lab" || section === "security" || section === "audit-verification" ||
          section === "reliability-report") && <ValidationPages section={section} signedIn={signedIn} />}
        {section === "settings" && <Configuration />}
      </div>
    </main>
  </div>;
}

function SummaryCards({ data }: { data: Summary }) {
  const cards = [
    ["Services", data.total, Server, "neutral"], ["Healthy", data.healthy, CircleCheck, "healthy"],
    ["Degraded", data.degraded, TriangleAlert, "degraded"], ["Down", data.down, XCircle, "down"],
    ["Recovering", data.recovering, Activity, "recovering"], ["Active incidents", data.active_incidents, Bell, "neutral"],
  ] as const;
  return <div className="cards">{cards.map(([label, count, Icon, tone]) =>
    <div className="card" key={label}><span className={"stat-icon " + tone}><Icon size={16} /></span>
      <span>{label}</span><strong>{count}</strong></div>)}</div>;
}

function Telemetry({ filter = false }: { filter?: boolean }) {
  const [hours, setHours] = useState("1");
  const [service, setService] = useState("");
  const data = useData<Metrics>("/metrics?hours=" + hours + (service ? "&service=" + service : ""));
  return <div className="telemetry">
    <div className="telemetry-bar"><div><h2>Monitoring telemetry</h2>
      <p>{data?.data?.availability != null ? data.data.availability.toFixed(2) + "% availability · " +
        data.data.checks + " checks" : "Synthetic health checks"}</p></div>
      <div className="controls">{filter && <select aria-label="Service filter" value={service}
        onChange={event => setService(event.target.value)}>
        <option value="">All services</option><option value="identity">Identity</option>
        <option value="messaging">Messaging</option><option value="storage">Storage</option>
      </select>}
      <select aria-label="Time period" value={hours} onChange={event => setHours(event.target.value)}>
        <option value="1">Last hour</option><option value="6">Last 6 hours</option>
        <option value="24">Last 24 hours</option><option value="168">Last 7 days</option>
      </select></div>
    </div>
    <Content result={data}>{metrics => <div className="two-col">
      <Chart title="Response latency" subtitle="Average of successful checks" data={metrics} series="latency_ms" color="#65a6ff" unit="ms" />
      <Chart title="Request error rate" subtitle="Share of failed health checks" data={metrics} series="error_rate" color="#b997ff" unit="%" />
    </div>}</Content>
  </div>;
}

function Chart({ title, subtitle, data, series, color, unit }: {
  title: string; subtitle: string; data: Metrics; series: "latency_ms" | "error_rate"; color: string; unit: string;
}) {
  return <Panel title={title} subtitle={subtitle} extra={<Activity size={17} className="muted" />}>
    {!data.points.some(point => point[series] !== null) ? <p className="message chart">No measurements for this period.</p> :
      <div className="chart"><ResponsiveContainer width="100%" height="100%" minWidth={0}>
        <AreaChart data={data.points} margin={{ top: 12, right: 16, left: 4, bottom: 8 }}>
          <defs><linearGradient id={series} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.3} /><stop offset="100%" stopColor={color} stopOpacity={0.02} />
          </linearGradient></defs>
          <CartesianGrid stroke="#243043" strokeDasharray="3 5" vertical={false} />
          <XAxis dataKey="time" tick={{ fill: "#a1aec5", fontSize: 11 }} minTickGap={28}
            tickFormatter={value => new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} />
          <YAxis width={56} tick={{ fill: "#a1aec5", fontSize: 11 }} unit={unit}
            domain={series === "error_rate" ? [0, 100] : [0, "auto"]} />
          <Tooltip labelFormatter={value => date(String(value))} contentStyle={{ background: "#111a28", borderColor: "#354257" }}
            formatter={value => [String(value) + (unit === "%" ? "%" : " " + unit), title]} />
          <Area type="linear" dataKey={series} stroke={color} fill={"url(#" + series + ")"}
            strokeWidth={2} dot={data.points.length < 3} isAnimationActive={false} />
        </AreaChart>
      </ResponsiveContainer></div>}
  </Panel>;
}

function Services() {
  const services = useData<Service[]>("/services");
  const [selected, select] = useState("");
  return <Content result={services}>{items => items.length === 0 ?
    <p className="message">No services have been seeded.</p> : <>
      <div className="service-grid">{items.map(service => <Panel title={service.name} subtitle="Local simulated service"
        key={service.slug} extra={<Badge state={service.state} />}>
        <dl><div><dt>Consecutive failures</dt><dd>{service.consecutive_failures}</dd></div>
          <div><dt>Last successful check</dt><dd>{date(service.last_success_at)}</dd></div></dl>
        <button className="secondary panel-button" onClick={() => select(service.slug)}>View health checks</button>
      </Panel>)}</div>{selected && <HealthHistory key={selected} slug={selected} />}
    </>}</Content>;
}

function HealthHistory({ slug }: { slug: string }) {
  const detail = useData<Detail>("/services/" + slug);
  const checks = useData<Check[]>("/services/" + slug + "/checks");
  return <Panel title={detail?.data?.name || slug} subtitle="Latest health checks">
    <Content result={checks}>{items => items.length ? <div className="table-wrap"><table><thead><tr>
      <th>Time</th><th>HTTP</th><th>Latency</th><th>Result</th></tr></thead><tbody>
      {items.map(check => <tr key={check.id}><td>{date(check.checked_at)}</td><td>{check.status_code ?? "—"}</td>
        <td>{check.latency_ms.toFixed(1)} ms</td><td>{check.available ? "Available" : check.error}</td></tr>)}
    </tbody></table></div> : <p className="message">No health checks recorded.</p>}</Content>
  </Panel>;
}

function IncidentList({ recent = false }: { recent?: boolean }) {
  const [page, setPage] = useState(0);
  const incidents = useData<Incident[]>("/incidents?limit=" + (recent ? 5 : 20) + "&offset=" + page * 20);
  const [selected, select] = useState<number>();
  return <><Panel title={recent ? "Recent incidents" : "Incident history"} extra={recent && <Link href="/incidents">View all</Link>}>
    <Content result={incidents}>{items => items.length ? <div className="table-wrap"><table><thead><tr>
      <th>Service</th><th>Status</th><th>Detected</th><th>Duration</th><th>Timeline</th>
    </tr></thead><tbody>{items.map(item => <tr key={item.id}><td className="capitalize">{item.service_slug}</td>
      <td><span className={"badge " + (item.closed_at ? "healthy" : "down")}><i />{item.closed_at ? "Resolved" : "Open"}</span></td>
      <td>{date(item.detected_at)}</td><td>{duration(item.duration_seconds)}</td>
      <td><button className="secondary" onClick={() => select(item.id)}>Incident #{item.id}</button></td>
    </tr>)}</tbody></table></div> : <div className="empty"><Radio size={22} /><p>No incidents recorded{page ? " on this page" : ""}.</p></div>}</Content>
    {!recent && (page > 0 || incidents?.data?.length === 20) && <div className="controls panel-button">
      <button className="secondary" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</button>
      <button className="secondary" disabled={incidents?.data?.length !== 20} onClick={() => setPage(page + 1)}>Next</button>
    </div>}
  </Panel>{selected && <Timeline key={selected} id={selected} />}</>;
}

function Timeline({ id }: { id: number }) {
  const detail = useData<IncidentDetail>("/incidents/" + id);
  return <><Panel title={"Incident #" + id + " timeline"}><Content result={detail}>{item => <>
    <dl><div><dt>First observed failure</dt><dd>{date(item.started_at)}</dd></div>
      <div><dt>Detection delay</dt><dd>{duration(item.detection_seconds)}</dd></div>
      <div><dt>Recovery confirmation time</dt><dd>{duration(item.recovery_seconds)}</dd></div>
      <div><dt>Resolved at</dt><dd>{date(item.closed_at)}</dd></div></dl>
    <ol className="timeline">{item.events.map(event => <li key={event.check.id + "-" + event.kind}>
      <strong className="capitalize">{event.kind.replaceAll("_", " ")}</strong>
      <span>{date(event.occurred_at)} · {event.check.status_code ?? event.check.error} · {event.check.latency_ms.toFixed(1)} ms</span>
    </li>)}</ol>
  </>}</Content></Panel><IncidentDiagnosis id={id} /></>;
}

function Simulation({ signedIn, invalidLogin }: { signedIn: boolean; invalidLogin: boolean }) {
  const [slug, setSlug] = useState("messaging");
  const [mode, setMode] = useState<Exclude<Mode, "healthy">>("latency");
  const [latency, setLatency] = useState("1200");
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");
  const [revision, setRevision] = useState(0);
  const detail = useData<Detail>("/services/" + slug, revision);
  async function apply(clear: boolean) {
    setPending(true);
    setMessage("");
    try {
      const fault = await request<{ mode: Mode }>("/services/" + slug + "/fault", {
        method: clear ? "DELETE" : "PUT",
        headers: { "Content-Type": "application/json", "x-cloudrescue-action": "fault" },
        body: clear ? undefined : JSON.stringify(mode === "latency" ? { mode, latency_ms: Number(latency) } : { mode }),
      });
      setMessage("Fault mode updated to " + labels[fault.mode].toLowerCase() + ".");
      setRevision(value => value + 1);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Fault update failed.");
    } finally { setPending(false); }
  }
  return <div className="two-col"><Panel title="Fault controls" subtitle="Changes affect the selected local simulator.">
    <div className="form">
      <label>Service<select aria-label="Service" value={slug} disabled={pending} onChange={event => setSlug(event.target.value)}>
        <option value="identity">Identity Service</option><option value="messaging">Messaging Service</option>
        <option value="storage">Storage Service</option>
      </select></label>
      <Content result={detail}>{service => <div className="controls"><Badge state={service.state} />
        <span>Current fault · {service.fault ? labels[service.fault.mode] : "Unavailable"}</span></div>}</Content>
      <label>Fault mode<select value={mode} onChange={event => setMode(event.target.value as typeof mode)}>
        <option value="latency">Increased latency</option><option value="error">HTTP 500</option>
        <option value="disconnect">Connection failure</option>
      </select></label>
      {mode === "latency" && <label>Latency (ms)<input type="number" min="1" max="10000"
        value={latency} onChange={event => setLatency(event.target.value)} /></label>}
      <div className="controls"><button disabled={!signedIn || pending} onClick={() => void apply(false)}>Apply fault</button>
        <button className="secondary" disabled={!signedIn || pending} onClick={() => void apply(true)}>Restore service</button></div>
      {message && <p role="status">{message}</p>}
    </div></Panel>
    <Panel title="Administrator access" subtitle="Required to change simulator behavior." extra={<Shield size={17} />}>
      <form className="form" action="/api/admin" method="post">
        {signedIn ? <><p>Signed in for this browser session.</p><button className="secondary" name="action" value="logout">Sign out</button></> :
          <><label>Username<input name="username" autoComplete="username" /></label>
            <label>Password<input name="password" type="password" autoComplete="current-password" /></label>
            <label>Development admin token<input name="token" type="password" autoComplete="off" /></label>
            {invalidLogin && <p className="error" role="alert">The credentials were rejected.</p>}
            <button>Sign in</button></>}
      </form>
    </Panel></div>;
}

function Configuration() {
  const settings = useData<Settings>("/settings");
  return <Panel title="Monitoring configuration" subtitle="Managed through the local environment." extra={<Database size={17} />}>
    <Content result={settings}>{data => <dl>{([
      ["Poll interval", data.poll_seconds + "s"], ["Request timeout", data.timeout_seconds + "s"],
      ["Maximum backoff", data.max_backoff_seconds + "s"], ["Concurrent requests", data.max_concurrency],
      ["Latency threshold", data.degraded_ms + " ms"], ["Failures before outage", data.down_after],
      ["Healthy checks to confirm recovery", data.recover_after],
    ] as const).map(([name, value]) => <div key={name}><dt>{name}</dt><dd>{value}</dd></div>)}</dl>}</Content>
  </Panel>;
}
