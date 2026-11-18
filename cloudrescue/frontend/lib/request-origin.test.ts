import { expect, it } from "vitest";
import { localOrigin } from "./request-origin";

it("allows localhost requests with a matching browser origin", () => {
  const request = new Request("http://0.0.0.0:3000/api/admin", {
    headers: { host: "127.0.0.1:3000", origin: "http://127.0.0.1:3000" },
  });
  expect(localOrigin(request)?.origin).toBe("http://127.0.0.1:3000");
});

it("rejects cross-origin and non-local requests", () => {
  for (const [host, origin] of [
    ["127.0.0.1:3000", "http://127.0.0.1:3001"],
    ["example.com", "https://example.com"],
  ]) {
    const request = new Request("http://127.0.0.1:3000/api/admin", {
      headers: { host, origin },
    });
    expect(localOrigin(request)).toBeNull();
  }
});
