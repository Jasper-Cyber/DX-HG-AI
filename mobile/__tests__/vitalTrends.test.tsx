import { fireEvent, render } from "@testing-library/react-native";
import type { Reading } from "@/api/types";
import { HeartRateCharts } from "@/components/HeartRateCharts";
import { Vo2MaxTrends } from "@/components/Vo2MaxTrends";
import { dailyMetricHistory, healthTrends } from "@/utils/healthTrends";
const reading = (metricType: Reading["metricType"], day: number, hour: number, value: number, quality: Reading["quality"] = "ok"): Reading => ({
  metricType, timestamp: new Date(Date.UTC(2026, 0, day, hour)).toISOString(), value, quality, isSynthetic: true, scenario: "A",
});
const heart = Array.from({ length: 8 }, (_, i) => [reading("hr", i + 1, 0, 50 + i), reading("hr", i + 1, 1, 60 + i), reading("hr", i + 1, 2, 70 + i)]).flat();
heart.push(reading("hr", 8, 3, 999, "low"));
const vo2 = Array.from({ length: 16 }, (_, i) => reading("vo2max", i + 1, 0, 40 + i * .2));

it("calculates seven daily HR min/mean/max values, including a partial today", () => {
  const days = dailyMetricHistory(heart, "hr", 7);
  expect(days).toHaveLength(7);
  expect(days[0].date).toBe("2026-01-02");
  expect(days[6]).toMatchObject({ date: "2026-01-08", min: 57, mean: 67, max: 77, count: 3 });
});

it("renders both HR charts and lets users inspect a different day", () => {
  const screen = render(<HeartRateCharts readings={heart} />);
  expect(screen.getByText("Heart Rate Today")).toBeTruthy();
  expect(screen.getByText("Preceding 7 Days HR")).toBeTruthy();
  expect(screen.getAllByText("Minimum").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Average").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Maximum").length).toBeGreaterThan(0);
  fireEvent.press(screen.getByLabelText("Heart rate for 2026-01-02"));
  expect(screen.getByText("2026-01-02")).toBeTruthy();
  expect(screen.getByText("51.0")).toBeTruthy();
  expect(screen.getByText("61.0")).toBeTruthy();
  expect(screen.getByText("71.0")).toBeTruthy();
});

it("compares daily VO2 values without requiring 12 hourly readings", () => {
  const summary = healthTrends(vo2, "vo2max")!;
  expect(summary.change).toBeCloseTo(1.4);
  expect(summary.forecast).toBeNull();
});

it("shows the VO2 scatter view, units, delta, and reading navigation", () => {
  const screen = render(<Vo2MaxTrends readings={vo2} />);
  expect(screen.getByText("VO₂ Max Trends")).toBeTruthy();
  expect(screen.getByText("2026-01-15")).toBeTruthy();
  expect(screen.getByText(/Daily synthetic demo values/)).toBeTruthy();
  fireEvent.press(screen.getByText("← Earlier reading"));
  expect(screen.getByText("2026-01-14")).toBeTruthy();
  fireEvent.press(screen.getByText("90 days"));
  expect(screen.getByText("2026-01-15")).toBeTruthy();
});

it("leaves empty dates blank and reports no VO2 data instead of inventing values", () => {
  const sparse = [reading("hr", 8, 0, 60), reading("hr", 6, 0, 70, "low")];
  expect(dailyMetricHistory(sparse, "hr", 7)[4]).toMatchObject({ mean: null, count: 0 });
  expect(render(<Vo2MaxTrends readings={sparse} />).getByText(/No daily VO₂ max history yet/)).toBeTruthy();
});

it("selects VO2 data through the native chart point touch handler", () => {
  const screen = render(<Vo2MaxTrends readings={vo2} />);
  fireEvent.press(screen.getByLabelText("VO₂ max for 2026-01-03: 40.4 mL/kg/min"));
  expect(screen.getByText("2026-01-03")).toBeTruthy();
});

it("switches between the dashboard heart charts without duplicating them", () => {
  const screen = render(<HeartRateCharts readings={heart} compact />);
  expect(screen.getByText("Preceding 7 Days HR")).toBeTruthy();
  expect(screen.queryByText("Heart Rate Today")).toBeNull();
  fireEvent.press(screen.getByLabelText("Show today’s heart rate"));
  expect(screen.getByText("Heart Rate Today")).toBeTruthy();
  expect(screen.queryByText("Preceding 7 Days HR")).toBeNull();
  fireEvent.press(screen.getByLabelText("Show 7-day heart rate range"));
  expect(screen.getByText("Preceding 7 Days HR")).toBeTruthy();
});
