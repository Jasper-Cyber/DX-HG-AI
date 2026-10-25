import type { TrendPoint, TrendSeries } from "@/api/types";
import { seriesHasData, seriesRange, shortLabel, toTrendChartData } from "@/utils/trends";

function pt(period: string, mean: number | null): TrendPoint {
  return { period, mean, min: mean, max: mean, count: mean === null ? 0 : 1 };
}

const points: TrendPoint[] = [
  pt("2026-01-01T00:00:00Z", 10),
  pt("2026-01-02T00:00:00Z", null),
  pt("2026-01-03T00:00:00Z", 30),
];

describe("toTrendChartData", () => {
  it("bridges null means from the previous known value", () => {
    const data = toTrendChartData(points);
    expect(data.map((p) => p.value)).toEqual([10, 10, 30]);
  });

  it("skips leading nulls with no prior value", () => {
    const data = toTrendChartData([pt("t", null), pt("t2", 5)]);
    expect(data.map((p) => p.value)).toEqual([5]);
  });

  it("labels every Nth point and flags anomalies by period", () => {
    const anomalies = new Set(["2026-01-03T00:00:00Z"]);
    const data = toTrendChartData(points, { labelEvery: 2, anomalyPeriods: anomalies });
    expect(data[0].label).toBeDefined();
    expect(data[1].label).toBeUndefined();
    expect(data[2].anomaly).toBe(true);
  });
});

describe("shortLabel", () => {
  it("formats month/day from a date period", () => {
    expect(shortLabel("2026-03-09T00:00:00Z")).toBe("3/9");
  });
  it("returns the raw period when it cannot be parsed as a date", () => {
    expect(shortLabel("not a date")).toBe("not a date");
  });
});

describe("seriesRange / seriesHasData", () => {
  const series: TrendSeries = {
    metric: "hr",
    points,
    baselineMean: 20,
  };

  it("computes min/max ignoring nulls", () => {
    expect(seriesRange(series)).toEqual({ min: 10, max: 30 });
  });

  it("reports no data when all means are null", () => {
    const empty: TrendSeries = { ...series, points: [pt("t", null)] };
    expect(seriesRange(empty)).toBeNull();
    expect(seriesHasData(empty)).toBe(false);
    expect(seriesHasData(series)).toBe(true);
  });
});
