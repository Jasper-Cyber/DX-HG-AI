import { ApiError, api } from "@/api/client";
import { alertStateMeta } from "@/utils/alerts";

describe("api.getMeasurements parsing", () => {
  const realFetch = global.fetch;
  afterEach(() => {
    global.fetch = realFetch;
  });

  it("unwraps the { items } envelope into a Reading[]", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => "application/json" },
      json: async () => ({
        count: 1,
        isExperimental: true,
        items: [
          {
            timestamp: "2026-01-01T00:00:00Z",
            metricType: "hr",
            value: 72,
            quality: "ok",
            isSynthetic: true,
            scenario: "A",
          },
        ],
      }),
    }) as unknown as typeof fetch;

    const readings = await api.getMeasurements({ metric: "hr" });
    expect(Array.isArray(readings)).toBe(true);
    expect(readings).toHaveLength(1);
    expect(readings[0].value).toBe(72);
  });

  it("throws a structured ApiError on a non-2xx response", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 422,
      headers: { get: () => "application/json" },
      json: async () => ({ error: "bad_metric", detail: "Unknown metric" }),
    }) as unknown as typeof fetch;

    await expect(api.getMeasurements({ metric: "nope" })).rejects.toBeInstanceOf(ApiError);
  });

  it("wraps a network failure as an ApiError with status 0", async () => {
    global.fetch = jest.fn().mockRejectedValue(new Error("offline")) as unknown as typeof fetch;
    await expect(api.getInsights()).rejects.toMatchObject({ status: 0 });
  });
});

describe("alertStateMeta", () => {
  it("maps each state to a label", () => {
    expect(alertStateMeta("normal").label).toMatch(/normal/i);
    expect(alertStateMeta("trend_review").label).toMatch(/trend/i);
    expect(alertStateMeta("attention").label).toMatch(/assessment/i);
  });
});
