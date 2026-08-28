import { describe, expect, it } from "vitest";
import { demoData } from "./data";

describe("demo dashboard contract", () => {
  it("ships enough deterministic data to exercise the operational view", () => {
    expect(demoData.demo).toBe(true);
    expect(demoData.services.length).toBeGreaterThanOrEqual(2);
    expect(demoData.deployments.length).toBeGreaterThanOrEqual(10);
    expect(demoData.dora.trend).toHaveLength(30);
    expect(demoData.dora.summary.change_fail_rate_percent).toBeGreaterThanOrEqual(0);
  });
});

