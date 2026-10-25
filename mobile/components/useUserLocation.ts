/**
 * Location hook with graceful fallback (Tasks 24-25, Owner: maiabrunne).
 *
 * Requests live GPS via `expo-location`. When permission is denied or location is
 * unavailable, falls back to a provided default location and flags it approximate
 * (Req 10.6, 10.8). Never throws; the UI reads `approximate` to show a fallback
 * indicator.
 */
import * as Location from "expo-location";
import { useCallback, useEffect, useState } from "react";

export interface ResolvedLocation {
  lat: number | null;
  lon: number | null;
  approximate: boolean;
  loading: boolean;
  /** True once a resolution attempt has completed (success or fallback). */
  resolved: boolean;
}

export function useUserLocation(
  defaultLat?: number | null,
  defaultLon?: number | null,
): ResolvedLocation {
  const [state, setState] = useState<ResolvedLocation>({
    lat: null,
    lon: null,
    approximate: false,
    loading: true,
    resolved: false,
  });

  const fallback = useCallback(() => {
    if (defaultLat != null && defaultLon != null) {
      setState({
        lat: defaultLat,
        lon: defaultLon,
        approximate: true,
        loading: false,
        resolved: true,
      });
    } else {
      setState({ lat: null, lon: null, approximate: true, loading: false, resolved: true });
    }
  }, [defaultLat, defaultLon]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { status } = await Location.requestForegroundPermissionsAsync();
        if (status !== "granted") {
          if (!cancelled) fallback();
          return;
        }
        const pos = await Location.getCurrentPositionAsync({});
        if (!cancelled) {
          setState({
            lat: pos.coords.latitude,
            lon: pos.coords.longitude,
            approximate: false,
            loading: false,
            resolved: true,
          });
        }
      } catch {
        if (!cancelled) fallback();
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [fallback]);

  return state;
}
