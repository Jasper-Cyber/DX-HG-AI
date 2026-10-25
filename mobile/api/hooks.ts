/**
 * React Query hooks over the typed API client.
 *
 * Polling model: while the simulator status is "running", live data
 * (measurements + insights) is refetched on an interval so the Dashboard and
 * Insights screens update as new synthetic samples arrive. When the simulator
 * is paused, polling stops. The scenario/simulator-control hooks are
 * mutations that invalidate the relevant caches so screens re-read fresh state.
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";

import { api } from "./client";
import type {
  CareProfile,
  DispatchArgs,
  DispatchEvent,
  DispatchResult,
  EmergencyDecision,
  EvaluateArgs,
  InsightResponse,
  ProviderSuggestion,
  Reading,
  RunAnalysisResponse,
  Scenario,
  ScenarioState,
  Settings,
  TrendRange,
  TrendsResponse,
} from "./types";

/** How often to refetch live data while the simulator is running (ms). */
export const LIVE_POLL_INTERVAL_MS = 5000;

/** Centralized query keys so mutations can target invalidation precisely. */
export const queryKeys = {
  health: ["health"] as const,
  measurements: (params?: { metric?: string; from?: string; to?: string }) =>
    ["measurements", params ?? {}] as const,
  trends: (range: TrendRange) => ["trends", range] as const,
  insights: ["insights"] as const,
  scenario: ["scenario"] as const,
  careProfile: ["careProfile"] as const,
  providers: (params: { lat: number; lon: number; emergency?: boolean }) =>
    ["providers", params] as const,
  dispatchHistory: ["dispatchHistory"] as const,
  settings: ["settings"] as const,
};

/**
 * Interval used by live queries. Returns the poll interval while the simulator
 * is running, or `false` to disable polling when paused/unknown.
 *
 * Reads the scenario cache directly so each live query reacts to simulator
 * state without an extra subscription.
 */
function useLivePollInterval(): number | false {
  const { data } = useScenario();
  return data?.status === "running" ? LIVE_POLL_INTERVAL_MS : false;
}

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

export function useScenario(): UseQueryResult<ScenarioState> {
  return useQuery({
    queryKey: queryKeys.scenario,
    queryFn: ({ signal }) => api.getScenario(signal),
  });
}

export function useMeasurements(
  params: { metric?: string; from?: string; to?: string } = {},
): UseQueryResult<Reading[]> {
  const pollInterval = useLivePollInterval();
  return useQuery({
    queryKey: queryKeys.measurements(params),
    queryFn: ({ signal }) => api.getMeasurements(params, signal),
    refetchInterval: pollInterval,
  });
}

export function useTrends(range: TrendRange): UseQueryResult<TrendsResponse> {
  return useQuery({
    queryKey: queryKeys.trends(range),
    queryFn: ({ signal }) => api.getTrends(range, signal),
  });
}

export function useInsights(): UseQueryResult<InsightResponse> {
  const pollInterval = useLivePollInterval();
  return useQuery({
    queryKey: queryKeys.insights,
    queryFn: ({ signal }) => api.getInsights(signal),
    refetchInterval: pollInterval,
  });
}

export function useCareProfile(): UseQueryResult<CareProfile> {
  return useQuery({
    queryKey: queryKeys.careProfile,
    queryFn: ({ signal }) => api.getCareProfile(signal),
  });
}

export function useProviders(
  params: { lat: number; lon: number; emergency?: boolean },
  options: { enabled?: boolean } = {},
): UseQueryResult<ProviderSuggestion[]> {
  return useQuery({
    queryKey: queryKeys.providers(params),
    queryFn: ({ signal }) => api.getProviders(params, signal),
    enabled: options.enabled ?? true,
  });
}

export function useDispatchHistory(): UseQueryResult<DispatchEvent[]> {
  return useQuery({
    queryKey: queryKeys.dispatchHistory,
    queryFn: ({ signal }) => api.getDispatchHistory(signal),
  });
}

export function useSettings(): UseQueryResult<Settings> {
  return useQuery({
    queryKey: queryKeys.settings,
    queryFn: ({ signal }) => api.getSettings(signal),
  });
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

/** Set the active scenario (A/B/C) and refresh scenario + live data. */
export function useSetScenario(): UseMutationResult<ScenarioState, unknown, Scenario> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (scenario: Scenario) => api.setScenario(scenario),
    onSuccess: (state) => {
      qc.setQueryData(queryKeys.scenario, state);
      void qc.invalidateQueries({ queryKey: ["measurements"] });
      void qc.invalidateQueries({ queryKey: queryKeys.insights });
    },
  });
}

type SimulatorAction = "start" | "pause" | "reset";

/** Start / Pause / Reset the simulator. Refreshes scenario + live caches. */
export function useSimulatorControl(): UseMutationResult<ScenarioState, unknown, SimulatorAction> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (action: SimulatorAction) => {
      if (action === "start") return api.simulatorStart();
      if (action === "pause") return api.simulatorPause();
      return api.simulatorReset();
    },
    onSuccess: (state) => {
      qc.setQueryData(queryKeys.scenario, state);
      void qc.invalidateQueries({ queryKey: ["measurements"] });
      void qc.invalidateQueries({ queryKey: queryKeys.insights });
    },
  });
}

/** Recompute baselines + findings, then refresh insights/trends. */
export function useRunAnalysis(): UseMutationResult<RunAnalysisResponse, unknown, void> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.runAnalysis(),
    // /analysis/run returns a summary, not the full insight — refetch insights
    // and trends so screens pick up the recomputed state.
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.insights });
      void qc.invalidateQueries({ queryKey: ["trends"] });
    },
  });
}

export function useUpdateCareProfile(): UseMutationResult<CareProfile, unknown, CareProfile> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (profile: CareProfile) => api.updateCareProfile(profile),
    onSuccess: (profile) => qc.setQueryData(queryKeys.careProfile, profile),
  });
}

export function useUpdateSettings(): UseMutationResult<Settings, unknown, Partial<Settings>> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (patch: Partial<Settings>) => api.updateSettings(patch),
    onSuccess: (settings) => qc.setQueryData(queryKeys.settings, settings),
  });
}

export function useAckDisclaimer(): UseMutationResult<Settings, unknown, void> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.ackDisclaimer(),
    onSuccess: (settings) => qc.setQueryData(queryKeys.settings, settings),
  });
}

/** Evaluate the current alert + location into a routing decision (flat; `enabled:false` when off). */
export function useEmergencyEvaluation(): UseMutationResult<
  EmergencyDecision,
  unknown,
  EvaluateArgs
> {
  return useMutation({
    mutationFn: (args: EvaluateArgs) => api.evaluateEmergency(args),
  });
}

/** Perform a dispatch (simulated by default; real requires confirm + opt-in). */
export function useDispatch(): UseMutationResult<DispatchResult, unknown, DispatchArgs> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: DispatchArgs) => api.dispatchEmergency(args),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.dispatchHistory });
    },
  });
}
