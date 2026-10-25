import React from "react";
import { fireEvent, render, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { api } from "@/api/client";
import EmergencyScreen from "@/app/emergency";

jest.mock("expo-router", () => ({ useLocalSearchParams: () => ({}) }));
jest.mock("react-native-safe-area-context", () => ({
  SafeAreaView: require("react-native").View,
}));
jest.mock("@/components/useUserLocation", () => ({
  useUserLocation: () => ({ lat: 40, lon: -74, resolved: true, loading: false, approximate: false }),
}));
jest.mock("@/api/client", () => ({ api: {
  getSettings: jest.fn(), getCareProfile: jest.fn(), getDispatchHistory: jest.fn(),
  evaluateEmergency: jest.fn(), dispatchEmergency: jest.fn(),
} }));

it("shows routing failure and retries to a real preview without claiming no dispatch is recommended", async () => {
  (api.getSettings as jest.Mock).mockResolvedValue({ emergencyEnabled: true });
  (api.getCareProfile as jest.Mock).mockResolvedValue({ emergencyContacts: [] });
  (api.getDispatchHistory as jest.Mock).mockResolvedValue([]);
  (api.evaluateEmergency as jest.Mock)
    .mockRejectedValueOnce(new Error("Backend unavailable"))
    .mockResolvedValueOnce({ enabled: true, recipientName: "Demo Hospital", channel: "simulated" });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity }, mutations: { retry: false, gcTime: Infinity } } });
  const screen = render(<QueryClientProvider client={client}><EmergencyScreen /></QueryClientProvider>);
  await waitFor(() => expect(screen.getByText("Unable to evaluate emergency routing")).toBeTruthy());
  expect(screen.getByText("Backend unavailable")).toBeTruthy();
  expect(screen.queryByText(/No dispatch is recommended/)).toBeNull();
  expect(screen.queryByText("Start dispatch…")).toBeNull();
  expect(screen.getByText("Call emergency services directly")).toBeTruthy();
  fireEvent.press(screen.getByText("Retry evaluation"));
  await waitFor(() => expect(screen.getByText("Demo Hospital")).toBeTruthy());
  expect(api.evaluateEmergency).toHaveBeenCalledTimes(2);
  screen.unmount();
  client.clear();
});
