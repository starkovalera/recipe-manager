import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ImportPage } from "./ImportPage";

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ImportPage />
    </QueryClientProvider>,
  );
}

describe("ImportPage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("submits text import and displays succeeded recipe id", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ jobId: "job-1", status: "pending" }) })
      .mockResolvedValue({ ok: true, json: async () => ({ jobId: "job-1", status: "succeeded", createdRecipeId: "recipe-1" }) });
    vi.stubGlobal("fetch", fetchMock);

    renderPage();
    fireEvent.change(screen.getByLabelText("Text"), { target: { value: "Soup recipe" } });
    fireEvent.click(screen.getByRole("button", { name: "Import" }));

    await waitFor(() => expect(screen.getByText(/Created recipe: recipe-1/)).toBeTruthy());
  });
});
