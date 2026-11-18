import { describe, expect, it } from "vitest";
import { duration } from "./types";

describe("incident duration", () => {
  it("formats unavailable, short, and long durations", () => {
    expect(duration(null)).toBe("—");
    expect(duration(11.6)).toBe("12s");
    expect(duration(126)).toBe("2m 6s");
  });
});
