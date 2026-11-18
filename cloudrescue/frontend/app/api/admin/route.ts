import { timingSafeEqual } from "node:crypto";
import { NextResponse } from "next/server";
import { createSession, sessionSeconds } from "../../../lib/admin-session";
import { localOrigin } from "../../../lib/request-origin";

export async function POST(request: Request) {
  const url = localOrigin(request);
  if (!url) {
    return Response.json({ detail: "Invalid request origin" }, { status: 403 });
  }
  if (!request.headers.get("content-type")?.startsWith("application/x-www-form-urlencoded")) {
    return Response.json({ detail: "Invalid sign-in form" }, { status: 400 });
  }
  const body = await request.text();
  if (body.length > 4096) {
    return Response.json({ detail: "Sign-in form is too large" }, { status: 413 });
  }
  const form = new URLSearchParams(body);
  const response = NextResponse.redirect(new URL("/simulation", url), 303);
  const base = process.env.CLOUDRESCUE_API_URL || "http://127.0.0.1:8000";
  if (form.get("action") === "logout") {
    const session = request.headers.get("cookie")?.match(/(?:^|;\s*)cloudrescue_identity=([A-Za-z0-9_-]+)/)?.[1];
    if (session) {
      const revoked = await fetch(base + "/identity/logout", {
        method: "POST", headers: { "Content-Type": "application/json", Authorization: "Bearer " + session },
        body: JSON.stringify({ token: session }), signal: AbortSignal.timeout(5000),
      }).catch(() => null);
      if (!revoked || (!revoked.ok && revoked.status !== 401)) {
        return Response.json({ detail: "Unable to revoke session. Try again." }, { status: 503 });
      }
    }
    response.cookies.delete("cloudrescue_admin");
    response.cookies.delete("cloudrescue_identity");
    return response;
  }
  if (form.get("username")) {
    const login = await fetch(base + "/identity/login", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: form.get("username"), password: form.get("password") }),
      signal: AbortSignal.timeout(5000), cache: "no-store",
    }).catch(() => null);
    if (!login?.ok) return NextResponse.redirect(new URL("/simulation?auth=invalid", url), 303);
    const { token } = await login.json();
    response.cookies.set("cloudrescue_identity", token, {
      httpOnly: true, sameSite: "strict", secure: url.protocol === "https:", path: "/", maxAge: sessionSeconds,
    });
    response.cookies.delete("cloudrescue_admin");
    return response;
  }
  const input = form.get("token");
  const token = process.env.ADMIN_TOKEN;
  if (!token || typeof input !== "string" ||
      Buffer.byteLength(input) !== Buffer.byteLength(token) ||
      !timingSafeEqual(Buffer.from(input), Buffer.from(token))) {
    return NextResponse.redirect(new URL("/simulation?auth=invalid", url), 303);
  }
  response.cookies.set("cloudrescue_admin", createSession(), {
    httpOnly: true, sameSite: "strict", secure: url.protocol === "https:",
    path: "/", maxAge: sessionSeconds,
  });
  const authorized = await fetch(base + "/identity/me", {
    headers: { Authorization: "Bearer " + token }, cache: "no-store", signal: AbortSignal.timeout(5000),
  }).catch(() => null);
  if (!authorized?.ok) return NextResponse.redirect(new URL("/simulation?auth=invalid", url), 303);
  return response;
}
