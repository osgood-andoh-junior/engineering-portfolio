import { cookies } from "next/headers";
import { sessionValid } from "../../../../lib/admin-session";
import { localOrigin } from "../../../../lib/request-origin";

const slug = "(identity|messaging|storage)";
const reads = new RegExp(
  "^(/summary|/settings|/metrics|/services|/services/" + slug +
  "(/checks)?|/incidents(/[1-9][0-9]*(/diagnosis)?)?|/dependencies(/[1-9][0-9]*)?" +
  "|/replays(/[1-9][0-9]*)?|/scenarios(/[a-z]+)?|/evaluation)$"
);
const fault = new RegExp("^/services/" + slug + "/fault$");
const recoveryRead = /^\/recovery\/(policies|experiments(\/[1-9][0-9]*)?|center|approvals|audit|analytics)$/;
const recoveryWrite = /^\/recovery\/(experiments|recommendations\/[1-9][0-9]*|approvals(\/[1-9][0-9]*\/execute)?|stop|resume)$/;
const validationRead = /^\/(identity\/(me|accounts|events)|audit-chain\/export|benchmarks(\/[1-9][0-9]*(\/export\/(json|csv))?)?)$/;
const validationPost = /^\/(identity\/accounts|audit-chain\/verify|benchmarks)$/;

type Context = { params: Promise<{ path: string[] }> };

async function proxy(request: Request, context: Context) {
  const path = "/" + (await context.params).path.join("/");
  const url = new URL(request.url);
  const write = request.method !== "GET";
  const allowed = request.method === "PUT" ? fault.test(path) || path === "/dependencies" || path === "/recovery/policies" ||
    /^\/identity\/accounts\/[a-z][a-z0-9_-]{2,47}$/.test(path) :
    request.method === "DELETE" ? fault.test(path) :
    request.method === "POST" ? path === "/replays" || /^\/scenarios\/[a-z]+\/run$/.test(path) ||
      recoveryWrite.test(path) || validationPost.test(path) : reads.test(path) || recoveryRead.test(path) || validationRead.test(path);
  if (!allowed) {
    return Response.json({ detail: "Unknown endpoint" }, { status: 404 });
  }
  const headers = new Headers();
  let body: string | undefined;
  if (write || recoveryRead.test(path) || validationRead.test(path)) {
    // Browsers enforce Origin and cannot attach this custom header cross-site without CORS.
    if (write && (!localOrigin(request) || request.headers.get("x-cloudrescue-action") !== "fault")) {
      return Response.json({ detail: "Invalid request origin" }, { status: 403 });
    }
    const jar = await cookies();
    const token = jar.get("cloudrescue_identity")?.value ||
      (sessionValid(jar.get("cloudrescue_admin")?.value) ? process.env.ADMIN_TOKEN : undefined);
    if (!token) {
      return Response.json({ detail: "Sign in to perform this action" }, { status: 401 });
    }
    headers.set("Authorization", "Bearer " + token);
    headers.set("Content-Type", "application/json");
    if (write && request.method !== "DELETE") {
      body = await request.text();
      if (body.length > 1024) {
        return Response.json({ detail: "Request is too large" }, { status: 413 });
      }
    }
  }
  const base = process.env.CLOUDRESCUE_API_URL || "http://127.0.0.1:8000";
  try {
    const upstream = await fetch(base + path + url.search, {
      method: request.method, headers, body, cache: "no-store",
      redirect: "error", signal: AbortSignal.timeout(path === "/benchmarks" && write ? 120000 : 5000),
    });
    return new Response(upstream.body, {
      status: upstream.status,
      headers: { "Content-Type": upstream.headers.get("Content-Type") || "application/json",
        "Cache-Control": "no-store",
        ...(upstream.headers.get("Content-Disposition") && {
          "Content-Disposition": upstream.headers.get("Content-Disposition")!,
        }) },
    });
  } catch {
    return Response.json({ detail: "CloudRescue API is unavailable" }, { status: 503 });
  }
}

export { proxy as GET, proxy as PUT, proxy as DELETE, proxy as POST };
