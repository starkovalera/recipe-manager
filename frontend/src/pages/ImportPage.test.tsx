import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ImportPage } from "./ImportPage";

function renderPage(onImported?: (recipeId: string) => void) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ImportPage onImported={onImported} />
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

  it("submits text import and displays succeeded recipe id", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ jobId: "job-1", status: "pending" }) })
      .mockResolvedValue({ ok: true, json: async () => ({ jobId: "job-1", status: "succeeded", createdRecipeId: "recipe-1" }) });
    vi.stubGlobal("fetch", fetchMock);

    renderPage();
    fireEvent.change(screen.getByLabelText("Text"), { target: { value: "Soup recipe" } });
    fireEvent.click(screen.getByRole("button", { name: "Import recipe" }));

    await waitFor(() => expect(screen.getByText(/Created recipe: recipe-1/)).toBeTruthy());
  });

  it("treats succeeded with flags as a successful import completion", async () => {
    const onImported = vi.fn();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ jobId: "job-1", status: "queued" }) })
      .mockResolvedValue({ ok: true, json: async () => ({ jobId: "job-1", status: "succeeded_with_flags", createdRecipeId: "recipe-1" }) });
    vi.stubGlobal("fetch", fetchMock);

    renderPage(onImported);
    fireEvent.change(screen.getByLabelText("Text"), { target: { value: "Soup recipe" } });
    fireEvent.click(screen.getByRole("button", { name: "Import recipe" }));

    await waitFor(() => expect(onImported).toHaveBeenCalledWith("recipe-1"));
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

    await waitFor(() => expect(screen.getByText("queued")).toBeTruthy());

    expect((screen.getByLabelText("Text") as HTMLTextAreaElement).value).toBe("");
    fireEvent.change(screen.getByLabelText("URL"), { target: { value: "https://example.com/recipe" } });
    fireEvent.click(screen.getByRole("button", { name: "Import recipe" }));

    await waitFor(() => expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(2));
    const postCalls = fetchMock.mock.calls.filter(([, init]) => init?.method === "POST");
    const secondRequest = postCalls[1][1] as RequestInit;
    expect((secondRequest.body as FormData).get("url")).toBe("https://example.com/recipe");
    expect((secondRequest.body as FormData).getAll("files")).toEqual([]);
  });
});
