import { render } from "@testing-library/react-native";

// gifted-charts pulls in a native gradient package that isn't needed to test
// our components' logic; stub it so MetricCard/MiniTrend render in the test env.
jest.mock("react-native-gifted-charts", () => ({ LineChart: () => null }));

import { AlertBanner } from "@/components/AlertBanner";
import { DEFAULT_EMERGENCY_GUIDANCE, EmergencyGuidanceCard } from "@/components/EmergencyGuidanceCard";
import { EXPERIMENTAL_NOTICE, ExperimentalNotice } from "@/components/ExperimentalNotice";
import { MetricCard } from "@/components/MetricCard";

describe("ExperimentalNotice", () => {
  it("renders the experimental/not-liable copy", () => {
    const { getByText } = render(<ExperimentalNotice />);
    expect(getByText(EXPERIMENTAL_NOTICE)).toBeTruthy();
  });
});

describe("EmergencyGuidanceCard", () => {
  it("shows default guidance when none provided", () => {
    const { getByText } = render(<EmergencyGuidanceCard />);
    expect(getByText(DEFAULT_EMERGENCY_GUIDANCE)).toBeTruthy();
  });

  it("prefers backend-provided guidance", () => {
    const { getByText } = render(<EmergencyGuidanceCard guidance="Call 000 now." />);
    expect(getByText("Call 000 now.")).toBeTruthy();
  });
});

describe("AlertBanner", () => {
  it("renders the state label and title", () => {
    const { getByText } = render(<AlertBanner state="attention" title="Check this" />);
    expect(getByText("Check this")).toBeTruthy();
    expect(getByText(/NEEDS FURTHER ASSESSMENT/i)).toBeTruthy();
  });
});

describe("MetricCard", () => {
  it("shows a no-data state when no reading is present", () => {
    const { getByText } = render(<MetricCard metric="hr" />);
    expect(getByText("Heart Rate")).toBeTruthy();
    expect(getByText("No data")).toBeTruthy();
  });

  it("renders a formatted value for an ok reading", () => {
    const { getByText } = render(
      <MetricCard
        metric="hr"
        reading={{
          timestamp: "2026-01-01T00:00:00Z",
          metricType: "hr",
          value: 72,
          quality: "ok",
          isSynthetic: true,
          scenario: "A",
        }}
      />,
    );
    expect(getByText("72")).toBeTruthy();
    expect(getByText("bpm")).toBeTruthy();
  });
});
