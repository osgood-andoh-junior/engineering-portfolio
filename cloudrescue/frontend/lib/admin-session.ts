import { createHmac, timingSafeEqual } from "node:crypto";

export const sessionSeconds = 1800;

function sign(value: string) {
  return createHmac("sha256", process.env.ADMIN_TOKEN || "")
    .update("cloudrescue-admin-session:" + value).digest("hex");
}

export function createSession() {
  const value = String(Math.floor(Date.now() / 1000) + sessionSeconds);
  return value + "." + sign(value);
}

export function sessionValid(cookie: string | undefined) {
  if (!process.env.ADMIN_TOKEN || !cookie || !/^\d+\.[a-f0-9]{64}$/.test(cookie)) return false;
  const [value, signature] = cookie.split(".");
  return Number(value) > Date.now() / 1000 &&
    timingSafeEqual(Buffer.from(signature), Buffer.from(sign(value)));
}
