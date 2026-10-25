import type { Reading } from "@/api/types";
import {
  formatMetricValue,
  hasUsableValue,
  latestForMetric,
  miniSeriesForMetric,
  qualityLabel,
} from "@/utils/metrics";

function reading(partial: Partial<Reading>): Reading {
  return {
    timestamp: "2026-01-01T00:00:00Z",
    metricType: "hr",
    value: 60,
    quality: "ok",
    isSynthetic: true,
    scenario: "A",
    ...partial,
  };
}

describe("formatMetricValue", () => {
  it("shows a dash for missing values", () => {
    expect(formatMetricValue(null, "hr")).toBe("—");
    expect(formatMetricValue(Number.NaN, "hr")).toBe("—");
  });

  it("rounds integer-style metrics", () => {
    expect(formatMetricValue(72.6, "hr")).toBe("73");
    expect(formatMetricValue(45.2, "hrv")).toBe("45");
    expect(formatMetricValue(97.8, "spo2")).toBe("98");
  });

  it("formats sleep with one decimal", () => {
    expect(formatMetricValue(7.25, "sleep")).toBe("7.3");
  });

  it("maps rhythm to Regular/Irregular", () => {
    expect(formatMetricValue(0, "rhythm")).toBe("Regular");
    expect(formatMetricValue(1, "rhythm")).toBe("Irregular");
  });
});

describe("qualityLabel", () => {
  it("labels low and missing quality", () => {
    expect(qualityLabel("ok")).toBe("");
    expect(qualityLabel("low")).toBe("Low quality");
    expect(qualityLabel("missing")).toBe("No data");
  });
});

describe("latestForMetric", () => {
  it("returns the most recent reading for the metric", () => {
    const readings = [
      reading({ metricType: "hr", timestamp: "2026-01-01T00:00:00Z", value: 60 }),
      reading({ metricType: "hr", timestamp: "2026-01-01T01:00:00Z", value: 70 }),
      reading({ metricType: "hrv", timestamp: "2026-01-01T02:00:00Z", value: 40 }),
    ];
    expect(latestForMetric(readings, "hr")?.value).toBe(70);
    expect(latestForMetric(readings, "hrv")?.value).toBe(40);
  });

  it("returns undefined when the metric is absent or input empty", () => {
    expect(latestForMetric([], "hr")).toBeUndefined();
    expect(latestForMetric(undefined, "hr")).toBeUndefined();
    expect(latestForMetric([reading({ metricType: "hrv" })], "spo2")).toBeUndefined();
  });
});

describe("miniSeriesForMetric", () => {
  it("returns values oldest→newest limited to the tail", () => {
    const readings = [
      reading({ metricType: "hr", timestamp: "2026-01-01T02:00:00Z", value: 3 }),
      reading({ metricType: "hr", timestamp: "2026-01-01T00:00:00Z", value: 1 }),
      reading({ metricType: "hr", timestamp: "2026-01-01T01:00:00Z", value: 2 }),
    ];
    expect(miniSeriesForMetric(readings, "hr", 2)).toEqual([2, 3]);
  });
});

describe("hasUsableValue", () => {
  it("is true only for ok readings with a value", () => {
    expect(hasUsableValue(reading({ value: 60, quality: "ok" }))).toBe(true);
    expect(hasUsableValue(reading({ value: null, quality: "missing" }))).toBe(false);
    expect(hasUsableValue(reading({ value: 60, quality: "low" }))).toBe(false);
    expect(hasUsableValue(undefined)).toBe(false);
  });
});

import { readingsInWindow, summarizeMetric } from "@/utils/metrics";

describe("measurement summaries", () => {
  it("uses the simulation clock and a trailing 24-hour window", () => {
    const rows = [reading({ timestamp: "2026-01-01T00:00:00Z" }), reading({ timestamp: "2026-01-01T01:00:00Z" }), reading({ timestamp: "2026-01-02T00:00:00Z" })];
    expect(readingsInWindow(rows, 24)).toEqual(rows.slice(1));
    expect(readingsInWindow(rows, null)).toEqual(rows);
  });
  it("excludes unusable samples from statistics but retains the gaps", () => {
    const rows = [reading({ value: 60 }), reading({ value: 80 }), reading({ value: 200, quality: "low" }), reading({ value: null, quality: "missing" }), reading({ value: Infinity })];
    const summary = summarizeMetric(rows, "hr");
    expect(summary).toMatchObject({ min: 60, mean: 70, max: 80, validCount: 2, totalCount: 5 });
    expect(miniSeriesForMetric(rows, "hr")).toEqual([60, 80, null, null, null]);
  });
  it("does not invent values for an empty window", () => {
    expect(summarizeMetric([], "hr")).toMatchObject({ min: null, mean: null, max: null, validCount: 0 });
  });
  it("counts rhythm flags only among valid observations", () => {
    const rows = [reading({ metricType: "rhythm", value: 1 }), reading({ metricType: "rhythm", value: 0 }), reading({ metricType: "rhythm", value: 1, quality: "low" })];
    expect(summarizeMetric(rows, "rhythm")).toMatchObject({ flagged: 1, validCount: 2, totalCount: 3 });
  });
});
