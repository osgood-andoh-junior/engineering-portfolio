export function localOrigin(request: Request): URL | null {
  const origin = request.headers.get("origin");
  if (!origin) return null;
  try {
    const url = new URL(origin);
    if (url.origin !== origin ||
        !["127.0.0.1", "localhost", "[::1]"].includes(url.hostname) ||
        url.host !== request.headers.get("host") ||
        !["http:", "https:"].includes(url.protocol)) return null;
    return url;
  } catch {
    return null;
  }
}
