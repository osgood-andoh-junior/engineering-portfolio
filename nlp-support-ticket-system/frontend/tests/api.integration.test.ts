// @vitest-environment node
import { afterAll, beforeAll, expect, test, vi } from "vitest";
import { spawn, type ChildProcess } from "node:child_process";
import { once } from "node:events";
import { createServer } from "node:net";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { api, post, type Ticket } from "@/lib/api";

let processHandle: ChildProcess;
let directory: string;
let logs = "";
beforeAll(async () => {
  directory = await mkdtemp(join(tmpdir(), "ticket-integration-"));
  const socket = createServer();
  socket.listen(0, "127.0.0.1");
  await once(socket, "listening");
  const address = socket.address();
  if (!address || typeof address === "string") throw new Error("No test port");
  const port = address.port;
  await new Promise<void>(resolve => socket.close(() => resolve()));
  const root = resolve("..");
  const python = process.env.TEST_PYTHON || join(root, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
  processHandle = spawn(python, ["-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", String(port)], {
    cwd: root, windowsHide: true,
    env: { ...process.env, DATABASE_PATH: join(directory, "test.db"), ARTIFACT_DIR: join(directory, "artifacts") },
  });
  let spawnError: Error | undefined;
  processHandle.on("error", error => { spawnError = error; });
  processHandle.stderr?.on("data", chunk => { logs += chunk.toString(); });
  vi.stubEnv("NEXT_PUBLIC_API_URL", "http://127.0.0.1:" + port);
  const deadline = Date.now() + 20000;
  while (Date.now() < deadline) {
    if (spawnError) throw spawnError;
    if (processHandle.exitCode !== null) throw new Error(logs);
    try { await api("/health"); return; } catch { await new Promise(resolve => setTimeout(resolve, 100)); }
  }
  throw new Error("FastAPI did not start: " + logs);
});
afterAll(async () => {
  vi.unstubAllEnvs();
  if (processHandle && processHandle.exitCode === null && processHandle.pid) {
    const exited = once(processHandle, "exit");
    processHandle.kill();
    await exited;
  }
  if (directory) await rm(directory, { recursive: true, force: true });
});
test("frontend API client talks to real FastAPI and SQLite", async () => {
  expect(await api("/health")).toEqual({ status: "ok", database: "sqlite" });
  const ticket = await api<Ticket>("/api/tickets", post({ text: "Integration fixture", actual_category: "Other" }));
  expect(await api<Ticket>("/api/tickets/" + ticket.id)).toEqual(ticket);
  expect(await api<Ticket[]>("/api/tickets")).toEqual([ticket]);
  await expect(api("/api/predictions", post({ ticket_id: ticket.id }))).rejects.toMatchObject({ code: "STUDENT_ML_NOT_IMPLEMENTED", component: "naive_bayes" });
  await expect(api("/api/training/start", post({}))).rejects.toMatchObject({ code: "STUDENT_ML_NOT_IMPLEMENTED" });
  expect(await api("/api/models")).toEqual([]);
  expect(await api("/api/evaluations")).toEqual([]);
  await expect(api("/api/tickets", post({ text: " " }))).rejects.toThrow();
  expect(await api("/api/tickets/" + ticket.id, { method: "DELETE" })).toBeUndefined();
});
