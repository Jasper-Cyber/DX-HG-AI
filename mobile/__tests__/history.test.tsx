import React from "react";
import { render } from "@testing-library/react-native";
import HistoryScreen from "@/app/(tabs)/history";

jest.mock("react-native-safe-area-context", () => ({ SafeAreaView: require("react-native").View }));
jest.mock("@/components/TrendChart", () => ({ TrendChart: () => null }));
jest.mock("@/api/hooks", () => ({
  useMeasurements: () => ({ data: [] }),
  useTrends: () => ({ data: { series: [] }, isLoading: false }),
  useAlertHistory: () => ({ data: [
    { id: 2, state: "normal", title: "Recovered baseline", createdAt: "2026-01-02T00:00:00Z" },
    { id: 1, state: "attention", title: "Earlier warning", createdAt: "2026-01-01T00:00:00Z" },
  ], isLoading: false }),
}));

it("shows multiple saved alerts including a warning before the current normal state", () => {
  const screen = render(<HistoryScreen />);
  expect(screen.getByText("Recovered baseline")).toBeTruthy();
  expect(screen.getByText("Earlier warning")).toBeTruthy();
  expect(screen.queryByText("No past alerts.")).toBeNull();
});
