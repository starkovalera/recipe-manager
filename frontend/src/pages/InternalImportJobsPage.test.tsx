import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { InternalImportJobsPage } from "./InternalImportJobsPage";

afterEach(() => cleanup());

describe("InternalImportJobsPage", () => {
  it("explains that a successful import recipe may have been deleted", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      text: async () => JSON.stringify({
        items: [{
          id: "job-1",
          ownerId: "local-user",
          clientId: "client-1",
          status: "succeeded",
          createdRecipeId: null,
          attemptCount: 1,
          maxAttempts: 3,
          statusHistory: [],
          sources: [],
          events: [],
        }],
      }),
    }));
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={client}>
        <InternalImportJobsPage onOpenRecipe={vi.fn()} />
      </QueryClientProvider>,
    );

    await waitFor(() => expect(screen.getByText("Recipe not found. It may have been deleted.")).toBeTruthy());
    expect(screen.queryByRole("button", { name: "Open recipe" })).toBeNull();
  });
});
