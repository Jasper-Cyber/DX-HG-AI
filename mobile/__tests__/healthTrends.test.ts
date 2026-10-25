import type { Reading } from "@/api/types";
import { healthTrends } from "@/utils/healthTrends";

export function trendReadings(): Reading[] {
  return Array.from({ length: 15 * 24 }, (_, i) => ({
    timestamp: new Date(Date.UTC(2026, 0, 1, i)).toISOString(), metricType: "hr" as const,
    value: i >= 14 * 24 ? 999 : 60 + Math.floor(i / 24),
    quality: "ok" as const, isSynthetic: true, scenario: "A" as const,
  }));
}

describe("health trend calculations", () => {
  it("compares equal complete periods and excludes the incomplete simulation day", () => {
    const result = healthTrends(trendReadings(), "hr")!;
    expect(result.current).toHaveLength(7);
    expect(result.current[0].date).toBe("2026-01-08");
    expect(result.yesterday.date).toBe("2026-01-14");
    expect(result.previousAverage).toBe(63);
    expect(result.average).toBe(70);
    expect(result.change).toBe(7);
    expect(result.sampleCount).toBe(168);
    expect(result.forecast).toEqual({ value: 74, date: "2026-01-15", daysUsed: 7 });
  });
  it("keeps calendar gaps and suppresses sparse comparisons and forecasts", () => {
    const rows = trendReadings().map(r => ({ ...r, quality: r.timestamp < "2026-01-13" ? "missing" as const : "ok" as const }));
    const result = healthTrends(rows, "hr")!;
    expect(result.current[0]).toMatchObject({ mean: null, count: 0 });
    expect(result.change).toBeNull();
    expect(result.forecast).toBeNull();
  });
  it("does not treat zero means as missing or divide a comparison by zero", () => {
    const result = healthTrends(trendReadings().map(r => ({ ...r, value: 0 })), "hr")!;
    expect(result.average).toBe(0);
    expect(result.change).toBe(0);
    expect(result.percentChange).toBeNull();
    expect(result.forecast?.value).toBe(0);
  });
  it("never produces an impossible oxygen estimate or a rhythm prediction", () => {
    const rows = trendReadings().map((r, i) => ({ ...r, metricType: "spo2" as const, value: 86.5 + Math.floor(i / 24) }));
    expect(healthTrends(rows, "spo2")!.forecast).toBeNull();
    expect(healthTrends(trendReadings().map(r => ({ ...r, metricType: "rhythm" as const })), "rhythm")!.forecast).toBeNull();
  });
  it("uses 30 days for monthly bars and does not fabricate earlier history", () => {
    const result = healthTrends(trendReadings(), "hr", 30)!;
    expect(result.current).toHaveLength(30);
    expect(result.current[0].mean).toBeNull();
    expect(result.change).toBeNull();
    expect(healthTrends([], "hr")).toBeNull();
  });
});
