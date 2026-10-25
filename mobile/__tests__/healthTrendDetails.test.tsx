import { fireEvent, render } from "@testing-library/react-native";
import { HealthTrendDetails } from "@/components/HealthTrendDetails";
import { MetricCard } from "@/components/MetricCard";
import type { Reading } from "@/api/types";
const readings: Reading[] = Array.from({ length: 15 * 24 }, (_, i) => ({
  timestamp: new Date(Date.UTC(2026, 0, 1, i)).toISOString(), metricType: "hr",
  value: 60 + Math.floor(i / 24), quality: "ok", isSynthetic: true, scenario: "A",
}));

it("lets a user select a weekly scatter point and switch to monthly bars", () => {
  const screen = render(<HealthTrendDetails readings={readings} metric="hr" />);
  expect(screen.getByLabelText(/Weekly daily-average scatterplot/)).toBeTruthy();
  fireEvent.press(screen.getByLabelText(/Select 2026-01-08, daily average/));
  expect(screen.getByText("2026-01-08")).toBeTruthy();
  expect(screen.getByLabelText(/2026-01-08: average/).props.accessibilityState.selected).toBe(true);
  expect(screen.queryByText("Experimental estimate")).toBeNull();
  fireEvent.press(screen.getByText("Forecast & methodology +"));
  expect(screen.getByText("Experimental estimate")).toBeTruthy();
  expect(screen.getByText(/Not a measured value/)).toBeTruthy();
  fireEvent.press(screen.getByLabelText("Monthly trend"));
  expect(screen.queryByLabelText(/Weekly daily-average scatterplot/)).toBeNull();
  expect(screen.getByText("Daily averages · last 30 complete UTC days")).toBeTruthy();
  expect(screen.getByText("Not enough comparable history")).toBeTruthy();
});

it("starts compact and expands details without hiding the current reading", () => {
  const screen = render(<MetricCard metric="hr" reading={readings[readings.length - 1]} readings={readings} historyReadings={readings} />);
  expect(screen.queryByText("Weekly trend")).toBeNull();
  expect(screen.getByText("74")).toBeTruthy();
  fireEvent.press(screen.getByLabelText("Expand Heart Rate details"));
  expect(screen.getByText("Weekly trend")).toBeTruthy();
  fireEvent.press(screen.getByLabelText("Collapse Heart Rate details"));
  expect(screen.queryByText("Weekly trend")).toBeNull();
  expect(screen.getByText("74")).toBeTruthy();
});
