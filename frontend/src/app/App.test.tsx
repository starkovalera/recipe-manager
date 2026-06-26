import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";


function mockFetch(payloads: Record<string, unknown>) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const path = new URL(url).pathname;
      const key = `${init?.method ?? "GET"} ${path}`;
      const payload = payloads[key] ?? payloads[`GET ${path}`];
      return {
        ok: true,
        status: init?.method === "DELETE" || init?.method === "PUT" ? 204 : 200,
        text: async () => (payload === undefined ? "" : JSON.stringify(payload)),
      };
    }),
  );
}


describe("App", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("opens on recipe grid with cover previews", async () => {
    mockFetch({
      "GET /recipes": {
        items: [{ id: "recipe-1", title: "Soup", coverImage: { id: "image-1", mediaUrl: "/media/cover.jpg", role: "COVER" }, hasOpenReviewFlags: true }],
      },
    });

    render(<App />);

    await waitFor(() => expect(screen.getByRole("button", { name: /Soup/ })).toBeTruthy());
    expect(screen.getByAltText("Soup cover")).toBeTruthy();
    expect(screen.getByLabelText("Soup requires review")).toBeTruthy();
  });

  it("navigates from import success to recipe detail", async () => {
    mockFetch({
      "GET /recipes": { items: [] },
      "POST /imports": { jobId: "job-1", status: "succeeded", createdRecipeId: "recipe-1" },
      "GET /imports/job-1": { jobId: "job-1", status: "succeeded", createdRecipeId: "recipe-1" },
      "GET /collections": { items: [] },
      "GET /recipes/recipe-1": {
        id: "recipe-1",
        title: "Soup",
        sourceName: "MANUAL",
        tags: [],
        instructions: ["Cook"],
        ingredients: [],
        images: [],
        coverOptions: [{ kind: "DEFAULT", label: "Default image", selected: true }],
        collections: [],
        resources: [],
        sources: [],
        debugResources: [],
        debugSources: [],
        reviewFlags: [],
      },
    });

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Import" }));
    fireEvent.change(screen.getByLabelText("Text"), { target: { value: "Soup recipe" } });
    fireEvent.click(screen.getByRole("button", { name: "Import recipe" }));

    await waitFor(() => expect(screen.getByText("MANUAL")).toBeTruthy());
    expect(screen.getByRole("heading", { name: "Soup" })).toBeTruthy();
  });
});
