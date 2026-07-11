import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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

  afterEach(() => {
    cleanup();
  });

  it("stays on the form and does not poll an accepted import job", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({ jobId: "job-1", status: "queued" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    renderPage();
    fireEvent.change(screen.getByLabelText("Text"), { target: { value: "Soup recipe" } });
    fireEvent.click(screen.getByRole("button", { name: "Import recipe" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    expect(String(fetchMock.mock.calls[0][0])).toContain("/imports");
    expect(screen.queryByText("queued")).toBeNull();
    expect(screen.queryByText(/Created recipe/)).toBeNull();
  });

  it("uses a new client import id for every accepted submission", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({ jobId: "job-1", status: "queued" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    renderPage();
    fireEvent.change(screen.getByLabelText("Text"), { target: { value: "First recipe" } });
    fireEvent.click(screen.getByRole("button", { name: "Import recipe" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    fireEvent.change(screen.getByLabelText("Text"), { target: { value: "Second recipe" } });
    fireEvent.click(screen.getByRole("button", { name: "Import recipe" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));

    const firstBody = fetchMock.mock.calls[0][1]?.body as FormData;
    const secondBody = fetchMock.mock.calls[1][1]?.body as FormData;
    expect(firstBody.get("clientImportId")).not.toBe(secondBody.get("clientImportId"));
  });

  it("submits selected image files with the import request", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ jobId: "job-1", status: "succeeded", createdRecipeId: "recipe-1" }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const file = new File(["image"], "recipe.jpg", { type: "image/jpeg" });

    renderPage();
    fireEvent.change(screen.getByLabelText("Images"), { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: "Import recipe" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const request = fetchMock.mock.calls[0][1] as RequestInit;
    expect(request.body).toBeInstanceOf(FormData);
    expect((request.body as FormData).getAll("files")).toEqual([file]);
  });

  it("clears form values and selected files after a queued import is accepted", async () => {
    const fetchMock = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      if (init?.method === "POST") {
        return Promise.resolve({ ok: true, json: async () => ({ jobId: `job-${fetchMock.mock.calls.length}`, status: "queued" }) });
      }
      return Promise.resolve({ ok: true, json: async () => ({ jobId: "job-1", status: "queued" }) });
    });
    vi.stubGlobal("fetch", fetchMock);
    const file = new File(["image"], "recipe.jpg", { type: "image/jpeg" });

    renderPage();
    fireEvent.change(screen.getByLabelText("Text"), { target: { value: "Recipe from image" } });
    fireEvent.change(screen.getByLabelText("Images"), { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: "Import recipe" }));

    await waitFor(() => expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1));

    expect((screen.getByLabelText("Text") as HTMLTextAreaElement).value).toBe("");
    fireEvent.change(screen.getByLabelText("URL"), { target: { value: "https://example.com/recipe" } });
    fireEvent.click(screen.getByRole("button", { name: "Import recipe" }));

    await waitFor(() => expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(2));
    const postCalls = fetchMock.mock.calls.filter(([, init]) => init?.method === "POST");
    const secondRequest = postCalls[1][1] as RequestInit;
    expect((secondRequest.body as FormData).get("url")).toBe("https://example.com/recipe");
    expect((secondRequest.body as FormData).getAll("files")).toEqual([]);
  });

  it("keeps form values and selected files when import creation fails", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      text: async () =>
        JSON.stringify({
          errorCode: "IMPORT_CREATION_FAILED",
          message: "Failed to create import. Please try again.",
        }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const file = new File(["image"], "recipe.jpg", { type: "image/jpeg" });

    renderPage();
    fireEvent.change(screen.getByLabelText("URL"), { target: { value: "https://example.com/recipe" } });
    fireEvent.change(screen.getByLabelText("Text"), { target: { value: "Recipe text" } });
    fireEvent.change(screen.getByLabelText("Images"), { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: "Import recipe" }));

    await waitFor(() => expect(screen.getByRole("alert").textContent).toBe("Failed to create import. Please try again."));
    expect((screen.getByLabelText("URL") as HTMLInputElement).value).toBe("https://example.com/recipe");
    expect((screen.getByLabelText("Text") as HTMLTextAreaElement).value).toBe("Recipe text");
    expect((screen.getByLabelText("Images") as HTMLInputElement).files?.[0]).toBe(file);
  });
});
