// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import {
  clearQueryCache,
  fetchWithCache,
  getQueryData,
  invalidateQueries,
  setQueryData,
  useQuery,
} from "./queryCache";

beforeEach(() => {
  clearQueryCache();
});

afterEach(() => {
  clearQueryCache();
});

describe("queryCache", () => {
  it("caches query results and returns cached value on next call", async () => {
    let callCount = 0;
    const fetcher = async () => {
      callCount++;
      return { id: 1, name: "Test Item" };
    };

    const first = await fetchWithCache("test:item:1", fetcher);
    expect(first).toEqual({ id: 1, name: "Test Item" });
    expect(callCount).toBe(1);

    const second = await fetchWithCache("test:item:1", fetcher);
    expect(second).toEqual({ id: 1, name: "Test Item" });
    expect(callCount).toBe(1); // Cached, no second network call!
  });

  it("deduplicates concurrent in-flight requests for the same key", async () => {
    let callCount = 0;
    const fetcher = async () => {
      callCount++;
      await new Promise((r) => setTimeout(r, 20));
      return { value: 42 };
    };

    const [res1, res2] = await Promise.all([
      fetchWithCache("test:dedup", fetcher),
      fetchWithCache("test:dedup", fetcher),
    ]);

    expect(res1).toEqual({ value: 42 });
    expect(res2).toEqual({ value: 42 });
    expect(callCount).toBe(1);
  });

  it("invalidates queries matching prefix so next call refetches", async () => {
    let count = 0;
    const fetcher = async () => ++count;

    await fetchWithCache("today:my", fetcher);
    expect(count).toBe(1);

    await fetchWithCache("today:my", fetcher);
    expect(count).toBe(1);

    invalidateQueries("today");

    await fetchWithCache("today:my", fetcher);
    expect(count).toBe(2); // Refetched!
  });

  it("allows setting and getting query data synchronously", () => {
    expect(getQueryData("test:sync")).toBeNull();
    setQueryData("test:sync", { count: 99 });
    expect(getQueryData("test:sync")).toEqual({ count: 99 });
  });

  it("useQuery returns cached data immediately with isLoading = false", async () => {
    setQueryData("today:cached", { tasks: ["task 1"] });

    const fetcher = vi.fn().mockResolvedValue({ tasks: ["task 1", "task 2"] });

    const { result } = renderHook(() =>
      useQuery("today:cached", fetcher, { staleTime: 60_000 }),
    );

    // Synchronously available on first render!
    expect(result.current.data).toEqual({ tasks: ["task 1"] });
    expect(result.current.isLoading).toBe(false);
  });

  it("useQuery fetches and updates state when cache is empty", async () => {
    const fetcher = vi.fn().mockResolvedValue({ site: "City Mall" });

    const { result } = renderHook(() => useQuery("site:1", fetcher));

    await waitFor(() => {
      expect(result.current.data).toEqual({ site: "City Mall" });
    });
    expect(result.current.isLoading).toBe(false);
  });

  it("useQuery refetches when reloadSignal is incremented", async () => {
    let counter = 10;
    const fetcher = vi.fn().mockImplementation(async () => ({ count: ++counter }));

    let signal = 0;
    const { result, rerender } = renderHook(
      ({ s }) => useQuery("counter", fetcher, { reloadSignal: s, staleTime: 60_000 }),
      { initialProps: { s: signal } },
    );

    await waitFor(() => expect(result.current.data).toEqual({ count: 11 }));

    // Bump reloadSignal
    signal = 1;
    rerender({ s: signal });

    await waitFor(() => expect(result.current.data).toEqual({ count: 12 }));
  });
});
