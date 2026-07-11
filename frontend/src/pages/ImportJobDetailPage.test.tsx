import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ImportJobDetailPage } from "./ImportJobDetailPage";

function renderPage(onOpenRecipe = vi.fn()) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <ImportJobDetailPage jobId="job-1" onOpenRecipe={onOpenRecipe} />
    </QueryClientProvider>,
  );
  return { client, onOpenRecipe };
}

describe("ImportJobDetailPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => cleanup());

  it("shows a user-friendly failed import with resources and retry", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => ({
      ok: true,
      status: init?.method === "POST" ? 202 : 200,
      text: async () =>
        JSON.stringify(
          init?.method === "POST"
            ? { jobId: "job-1", status: "queued", attemptCount: 1, maxAttempts: 3, sources: [] }
            : {
                jobId: "job-1",
                status: "failed",
                errorMessage: "NOT_A_RECIPE",
                attemptCount: 1,
                maxAttempts: 3,
                createdAt: "2026-07-11T10:00:00Z",
                startedAt: "2026-07-11T10:00:01Z",
                finishedAt: "2026-07-11T10:00:05Z",
                sources: [
                  { type: "IMAGE", originalName: "recipe.jpg", mediaUrl: "/media/recipe.jpg" },
                  { type: "URL", url: "https://example.com/recipe" },
                  { type: "TEXT", text: "Recipe text" },
                ],
              },
        ),
    }));
    vi.stubGlobal("fetch", fetchMock);

    renderPage();

    await waitFor(() => expect(screen.getByRole("heading", { name: "Import details" })).toBeTruthy());
    expect(screen.getByText("Failed")).toBeTruthy();
    expect(screen.getByText("No recipe could be found in the provided sources.")).toBeTruthy();
    expect(screen.getByText("Attempt 1 of 3")).toBeTruthy();
    expect(screen.getByAltText("recipe.jpg")).toBeTruthy();
    expect(screen.getByRole("link", { name: "https://example.com/recipe" })).toBeTruthy();
    expect(screen.getByText("Recipe text")).toBeTruthy();
    expect(screen.queryByText("job-1")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Retry import" }));

    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith("/imports/job-1/retry") && init?.method === "POST")).toBe(true));
    await waitFor(() => expect(screen.queryByRole("button", { name: "Retry import" })).toBeNull());
  });

  it("uses the unexpected error fallback and opens a successful recipe", async () => {
    const onOpenRecipe = vi.fn();
    const responses = [
      {
        jobId: "job-1",
        status: "failed",
        errorMessage: "SOMETHING_NEW",
        attemptCount: 3,
        maxAttempts: 3,
        sources: [],
      },
      {
        jobId: "job-1",
        status: "succeeded",
        createdRecipeId: "recipe-1",
        attemptCount: 1,
        maxAttempts: 3,
        sources: [],
      },
    ];
    const fetchMock = vi.fn().mockImplementation(() =>
      Promise.resolve({ ok: true, status: 200, text: async () => JSON.stringify(responses.shift()) }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const first = renderPage();
    await waitFor(() => expect(screen.getByText("Unexpected error.")).toBeTruthy());
    expect(screen.queryByRole("button", { name: "Retry import" })).toBeNull();
    cleanup();
    first.client.clear();

    renderPage(onOpenRecipe);
    await waitFor(() => expect(screen.getByRole("button", { name: "Open recipe" })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Open recipe" }));
    expect(onOpenRecipe).toHaveBeenCalledWith("recipe-1");
  });
});
