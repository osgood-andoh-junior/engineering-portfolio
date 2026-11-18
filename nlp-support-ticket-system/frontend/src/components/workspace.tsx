"use client";
import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from "react";
import { api, ApiError, categories, percent, post, type Evaluation, type Model, type Prediction, type Ticket, type TrainingRun } from "@/lib/api";

function useData<T>(path: string) {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<Error>();
  const [loading, setLoading] = useState(true);
  const reload = useCallback(async () => {
    setLoading(true); setError(undefined);
    try { setData(await api<T>(path)); } catch (error) { setError(error as Error); }
    finally { setLoading(false); }
  }, [path]);
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    void api<T>(path, { signal: controller.signal })
      .then(value => { if (active) setData(value); })
      .catch(error => { if (active) setError(error as Error); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; controller.abort(); };
  }, [path]);
  return { data, error, loading, reload };
}
export function ErrorMessage({ error }: { error?: Error }) {
  if (!error) return null;
  return <div className="error-box" role="alert"><strong>{error instanceof ApiError && error.code ? error.code : "Request failed"}</strong>{error instanceof ApiError && error.component && <code>Component: {error.component}</code>}<p>{error.message}</p></div>;
}
function Heading({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return <div className="page-heading"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>{action}</div>;
}
function Empty({ title, children }: { title: string; children: ReactNode }) {
  return <div className="empty"><span className="empty-icon" aria-hidden="true">◇</span><h3>{title}</h3><p>{children}</p></div>;
}
function LoadState({ loading, error, retry }: { loading: boolean; error?: Error; retry: () => void }) {
  if (loading) return <p className="loading" role="status">Loading workspace data…</p>;
  return error ? <><ErrorMessage error={error} /><button className="button secondary" onClick={retry}>Retry</button></> : null;
}
const date = (value: string) => new Date(value).toLocaleString();
function Stat({ label, value, note }: { label: string; value: string; note: string }) {
  return <div className="stat"><span>{label}</span><strong>{value}</strong><small>{note}</small></div>;
}
function TicketTable({ tickets, action }: { tickets: Ticket[]; action?: (ticket: Ticket) => ReactNode }) {
  return <div className="table-scroll"><table><thead><tr><th>Ticket</th><th>Actual label</th><th>Prediction</th><th>Confidence</th><th>Created</th>{action && <th>Actions</th>}</tr></thead><tbody>{tickets.map(ticket => <tr key={ticket.id}><td className="ticket-text"><small>#{ticket.id}</small>{ticket.text}</td><td>{ticket.actual_category ?? <span className="muted">Unlabeled</span>}</td><td>{ticket.predicted_category ? <span className="tag">{ticket.predicted_category}</span> : "—"}</td><td>{percent(ticket.confidence)}</td><td>{date(ticket.created_at)}</td>{action && <td>{action(ticket)}</td>}</tr>)}</tbody></table></div>;
}
export function Dashboard() {
  const tickets = useData<Ticket[]>("/api/tickets");
  const models = useData<Model[]>("/api/models");
  const evaluations = useData<Evaluation[]>("/api/evaluations");
  const error = tickets.error || models.error || evaluations.error;
  const loading = tickets.loading || models.loading || evaluations.loading;
  const rows = tickets.data ?? [];
  const current = models.data?.[0];
  const latest = evaluations.data?.find(e => e.model_version === current?.version);
  const predictions = rows.filter(t => t.predicted_category);
  return <><Heading eyebrow="OVERVIEW" title="Your intelligence workspace" description="From support tickets to understanding. Build, experiment, and measure." action={<Link className="button" href="/classify">Classify a ticket ↗</Link>} />
    <LoadState loading={loading} error={error} retry={() => { void tickets.reload(); void models.reload(); void evaluations.reload(); }} />
    {!loading && !error && <><div className="stats">
      <Stat label="Total tickets" value={String(rows.length)} note="Stored in your local dataset" />
      <Stat label="Labeled tickets" value={String(rows.filter(t => t.actual_category).length)} note="Available for supervised learning" />
      <Stat label="Current model" value={current ? current.model.replaceAll("_", " ") : "Not trained"} note={current?.version ?? "Complete your first implementation"} />
      <Stat label="Latest accuracy" value={percent(latest?.metrics.accuracy)} note={latest ? "Evaluation for current model" : "No evaluation recorded"} />
    </div><div className="dashboard-grid"><section className="panel"><div className="panel-heading"><h2>Ticket categories</h2><span className="muted">Actual labels</span></div><div className="distribution">{categories.map(category => { const count = rows.filter(t => t.actual_category === category).length; return <div className="distribution-row" key={category}><span>{category}</span><div className="bar-track"><div style={{ width: rows.length ? count / rows.length * 100 + "%" : "0%" }} /></div><strong>{count}</strong></div>; })}</div><p className="panel-footnote">{rows.filter(t => !t.actual_category).length} unlabeled tickets</p></section>
      <section className="journey"><div className="eyebrow">THE LEARNING PATH</div><span className="step-number">01 <span>/ 06</span></span><h2>Start with the fundamentals.</h2><p>Explore Bag of Words and Naive Bayes in your first notebook. The ML implementation is yours to build.</p><Link className="button secondary" href="/experiments">Explore experiments →</Link></section>
      <section className="panel wide"><div className="panel-heading"><h2>Recent predictions</h2><Link href="/tickets">View tickets →</Link></div>{predictions.length ? <TicketTable tickets={predictions.slice(0, 5)} /> : <Empty title="Your first prediction starts here">Implement and train a classifier, then classify a saved ticket to see its result here.</Empty>}</section>
      <section className="panel wide"><div className="panel-heading"><h2>Latest evaluation</h2><span className="muted">Current model</span></div>{latest ? <div className="stats compact">{Object.entries(latest.metrics).map(([name, value]) => <Stat key={name} label={name} value={percent(value)} note="" />)}</div> : <p className="panel-footnote">No evaluation metrics recorded for the current model.</p>}</section>
    </div></>}
  </>;
}
export function Tickets() {
  const { data, loading, error, reload } = useData<Ticket[]>("/api/tickets");
  const [text, setText] = useState("");
  const [category, setCategory] = useState("");
  const [editing, setEditing] = useState<number>();
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<Error>();
  const [notice, setNotice] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setActionError(undefined); setNotice("");
    try {
      await api(editing ? "/api/tickets/" + editing : "/api/tickets", { method: editing ? "PATCH" : "POST", body: JSON.stringify({ text, actual_category: category || null }) });
      setText(""); setCategory(""); setEditing(undefined); setNotice("Ticket saved."); await reload();
    } catch (error) { setActionError(error as Error); } finally { setBusy(false); }
  }
  async function remove(ticket: Ticket) {
    if (!window.confirm("Delete ticket #" + ticket.id + "?")) return;
    setBusy(true); setActionError(undefined);
    try { await api("/api/tickets/" + ticket.id, { method: "DELETE" }); if (editing === ticket.id) { setEditing(undefined); setText(""); setCategory(""); } await reload(); }
    catch (error) { setActionError(error as Error); } finally { setBusy(false); }
  }
  return <><Heading eyebrow="DATASET" title="Tickets" description="Collect examples and assign labels for your experiments." /><section className="panel form-panel"><h2>{editing ? "Edit ticket #" + editing : "Add a ticket"}</h2><form onSubmit={submit}><label htmlFor="ticket-text">Ticket text</label><textarea id="ticket-text" required maxLength={10000} value={text} onChange={e => setText(e.target.value)} placeholder="Describe the support issue…" /><div className="form-row"><div><label htmlFor="category">Actual category <span className="muted">(optional)</span></label><select id="category" value={category} onChange={e => setCategory(e.target.value)}><option value="">Unlabeled</option>{categories.map(c => <option key={c}>{c}</option>)}</select></div><button className="button" disabled={busy || !text.trim()}>{busy ? "Saving…" : "Save ticket"}</button>{editing && <button type="button" className="button secondary" onClick={() => { setEditing(undefined); setText(""); setCategory(""); }}>Cancel</button>}</div></form><ErrorMessage error={actionError} /><p role="status" className="success">{notice}</p></section><section className="panel"><div className="panel-heading"><h2>Ticket library</h2><span className="muted">{data?.length ?? "—"} tickets</span></div><LoadState loading={loading} error={error} retry={reload} />{!loading && !error && (data?.length ? <TicketTable tickets={data} action={ticket => <div className="table-actions"><button disabled={busy} onClick={() => { setEditing(ticket.id); setText(ticket.text); setCategory(ticket.actual_category ?? ""); }}>Edit</button><button disabled={busy} onClick={() => void remove(ticket)}>Delete</button></div>} /> : <Empty title="A fresh dataset">Add your first support ticket above. No sample records have been added.</Empty>)}</section></>;
}
export function Classify() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<Prediction>();
  const [error, setError] = useState<Error>();
  const [busy, setBusy] = useState(false);
  const [save, setSave] = useState(true);
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(undefined); setResult(undefined);
    try {
      const source = save ? { ticket_id: (await api<Ticket>("/api/tickets", post({ text }))).id } : { text };
      setResult(await api<Prediction>("/api/predictions", post(source)));
    } catch (error) { setError(error as Error); } finally { setBusy(false); }
  }
  return <><Heading eyebrow="INFERENCE" title="Classify a ticket" description="Put your current model to work on a support request." /><div className="two-column"><section className="panel form-panel"><h2>Support request</h2><form onSubmit={submit}><label htmlFor="classify-text">Ticket text</label><textarea id="classify-text" required maxLength={10000} value={text} onChange={e => setText(e.target.value)} placeholder="I cannot connect to the Wi-Fi." rows={7} /><label className="checkbox"><input type="checkbox" checked={save} onChange={e => setSave(e.target.checked)} />Save ticket to the dataset before classification</label><p className="muted small">Saved tickets remain in the dataset if classification is unavailable.</p><button className="button" disabled={busy || !text.trim()}>{busy ? "Classifying…" : "Classify"}</button></form></section><section className="panel result-panel"><div className="panel-heading"><h2>Prediction result</h2><span className="tag">Model output</span></div><ErrorMessage error={error} />{result ? <dl className="result-list"><dt>Predicted category</dt><dd className="result-category">{result.category}</dd><dt>Confidence</dt><dd>{percent(result.confidence)}</dd><dt>Model</dt><dd>{result.model}</dd><dt>Processing time</dt><dd>{result.processing_time_ms.toFixed(2)} ms</dd></dl> : !error && <Empty title="Ready when your model is">Submit a ticket to request a prediction. Unimplemented ML components return a development error.</Empty>}</section></div></>;
}
const modelOptions = [["naive_bayes", "Naive Bayes"], ["neural_network", "Neural Network"], ["rnn", "RNN"], ["attention", "RNN + Attention"], ["transformer", "Transformer"]];
export function Training() {
  const [model, setModel] = useState("naive_bayes");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error>();
  const [notice, setNotice] = useState("");
  const runs = useData<TrainingRun[]>("/api/training/runs");
  async function start(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(undefined); setNotice("");
    try { const result = await api<{ run_id: number }>("/api/training/start", post({ model })); setNotice("Training run #" + result.run_id + " completed."); }
    catch (error) { setError(error as Error); }
    finally { setBusy(false); await runs.reload(); }
  }
  return <><Heading eyebrow="MODEL DEVELOPMENT" title="Training" description="Train a classifier using the labeled tickets in your local dataset." /><section className="panel form-panel"><h2>Start a training run</h2><p className="muted">V1 runs training synchronously. Implement the model contract before starting a run.</p><form onSubmit={start}><label htmlFor="model">Classifier</label><select id="model" value={model} onChange={e => setModel(e.target.value)}>{modelOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><button className="button" disabled={busy}>{busy ? "Training…" : "Start training"}</button></form><ErrorMessage error={error} /><p role="status" className="success">{notice}</p></section><section className="panel"><div className="panel-heading"><h2>Training history</h2></div><LoadState loading={runs.loading} error={runs.error} retry={runs.reload} />{!runs.loading && !runs.error && (runs.data?.length ? <div className="table-scroll"><table><thead><tr><th>Run</th><th>Model</th><th>Status</th><th>Error</th><th>Started</th></tr></thead><tbody>{runs.data.map(run => <tr key={run.id}><td>#{run.id}</td><td>{run.model}</td><td><span className="tag">{run.status}</span></td><td>{run.error ?? "—"}</td><td>{date(run.created_at)}</td></tr>)}</tbody></table></div> : <Empty title="No training runs yet">Your attempts and their outcomes will appear here.</Empty>)}</section></>;
}
export function Models() {
  const models = useData<Model[]>("/api/models");
  const evaluations = useData<Evaluation[]>("/api/evaluations");
  const loading = models.loading || evaluations.loading;
  const error = models.error || evaluations.error;
  return <><Heading eyebrow="MODEL REGISTRY" title="Models" description="Compare registered versions using your recorded evaluation results." /><section className="panel"><div className="panel-heading"><h2>Registered models</h2><span className="muted">Latest version is used for inference</span></div><LoadState loading={loading} error={error} retry={() => { void models.reload(); void evaluations.reload(); }} />{!loading && !error && (models.data?.length ? <div className="table-scroll"><table><thead><tr>{["Model", "Version", "Accuracy", "Precision", "Recall", "F1", "Training date"].map(name => <th key={name}>{name}</th>)}</tr></thead><tbody>{models.data.map(model => { const metrics = evaluations.data?.find(e => e.model_version === model.version)?.metrics; return <tr key={model.id}><td>{model.model}</td><td className="version">{model.version}</td><td>{percent(metrics?.accuracy)}</td><td>{percent(metrics?.precision)}</td><td>{percent(metrics?.recall)}</td><td>{percent(metrics?.f1)}</td><td>{date(model.created_at)}</td></tr>; })}</tbody></table></div> : <Empty title="Your model registry is empty">A successfully trained and saved model will be registered here. Metrics appear only after you store a real evaluation.</Empty>)}</section></>;
}
const experiments = [
  ["01", "Bag of Words + Naive Bayes", "Text preprocessing, vocabulary, representation, and your first classifier.", "01_bow_naive_bayes.ipynb"],
  ["02", "TF-IDF", "A new representation and a comparison with your first experiment.", "02_tfidf.ipynb"],
  ["03", "Embeddings + Neural Network", "Explore learned representations and a neural classifier.", "03_embeddings_nn.ipynb"],
  ["04", "RNN", "Explore sequential representations and recurrent models.", "04_rnn.ipynb"],
  ["05", "Attention", "Extend your sequence experiment with attention.", "05_attention.ipynb"],
  ["06", "Transformer", "Complete your learning path and compare your models.", "06_transformer.ipynb"],
];
export function Experiments() {
  return <><Heading eyebrow="ML LABORATORY" title="Six experiments. One learning journey." description="Your notebooks are the laboratory. Your implementations belong in the ML core." /><div className="info-banner"><span aria-hidden="true">↗</span><div><strong>Start with Experiment 01</strong><p>Open JupyterLab from the project root, then choose a notebook in ml/notebooks/.</p></div><code>jupyter lab</code></div><div className="experiment-grid">{experiments.map(([number, name, description, file]) => <article className="panel experiment" key={number}><div className="experiment-top"><span>{number}</span><span className="tag">Student-owned</span></div><h2>Experiment {number} — {name}</h2><p>{description}</p><code>ml/notebooks/{file}</code><div className="experiment-bottom">Notebook scaffold <span>→</span></div></article>)}</div></>;
}
