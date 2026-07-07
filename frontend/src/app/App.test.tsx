import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { queryClient } from "./queryClient";


function mockFetch(payloads: Record<string, unknown>) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const path = new URL(url).pathname;
      const key = `${init?.method ?? "GET"} ${path}`;
      const payload =
        payloads[key] ??
        payloads[`GET ${path}`] ??
        (path === "/notifications" || path === "/tags" ? { items: [] } : undefined);
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

  afterEach(() => {
    cleanup();
    queryClient.clear();
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

  it("paginates recipe list requests", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const path = new URL(url).pathname;
      const payloads: Record<string, unknown> = {
        "GET /recipes": {
          items: [{ id: "recipe-1", title: "Soup", coverImage: null }],
          total: 25,
          limit: 24,
          offset: 0,
        },
        "GET /notifications": { items: [] },
      };
      const payload = payloads[`${init?.method ?? "GET"} ${path}`] ?? payloads[`GET ${path}`];
      return {
        ok: true,
        status: 200,
        text: async () => (payload === undefined ? "{}" : JSON.stringify(payload)),
      };
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    await waitFor(() => expect(screen.getByRole("button", { name: /Soup/ })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Next" }));

    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes("/recipes?limit=24&offset=24"))).toBe(true));
  });

  it("selects autocomplete chips and filters recipe list requests", async () => {
    const searchBodies: Array<{ text?: string | null; selected?: Array<{ type: string; value?: string | null }> }> = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const parsed = new URL(url);
      const path = parsed.pathname;
      if (path === "/search" && init?.method === "POST" && typeof init.body === "string") {
        searchBodies.push(JSON.parse(init.body));
      }
      const payloads: Record<string, unknown> = {
        "GET /recipes": {
          items: [{ id: "recipe-1", title: "Chicken Soup", coverImage: null }],
          total: 1,
          limit: 24,
          offset: 0,
        },
        "POST /search": {
          items: [{ id: "recipe-1", title: "Chicken Soup", coverImage: null, matchReasons: [{ type: "filter", label: "Selected filters" }] }],
          limit: 24,
          offset: 0,
          hasMore: false,
        },
        "GET /search/suggestions": {
          items: [{ type: "ingredient_query", value: "chicken", label: "Ingredient - chicken" }],
        },
        "GET /notifications": { items: [] },
      };
      const payload = payloads[`${init?.method ?? "GET"} ${path}`] ?? payloads[`GET ${path}`];
      return {
        ok: true,
        status: 200,
        text: async () => (payload === undefined ? "{}" : JSON.stringify(payload)),
      };
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    await waitFor(() => expect(screen.getByRole("button", { name: /Chicken Soup/ })).toBeTruthy());
    fireEvent.change(screen.getByLabelText("Search recipes"), { target: { value: "chick" } });
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes("/search/suggestions?q=chick&limit=10"))).toBe(true));
    await waitFor(() => expect(searchBodies.some((body) => body.text === "chick")).toBe(true));
    await waitFor(() => expect(screen.getByRole("button", { name: "Ingredient - chicken" })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Ingredient - chicken" }));

    await waitFor(() =>
      expect(searchBodies.some((body) => body.selected?.some((chip) => chip.type === "ingredient_query" && chip.value === "chicken"))).toBe(true),
    );
    expect(screen.getByRole("button", { name: "Remove Ingredient - chicken filter" })).toBeTruthy();
  });

  it("paginates collection list requests", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const path = new URL(url).pathname;
      const payloads: Record<string, unknown> = {
        "GET /recipes": { items: [], total: 0, limit: 24, offset: 0 },
        "GET /notifications": { items: [] },
        "GET /collections": {
          items: [{ id: "collection-1", name: "Weeknight", recipeCount: 0 }],
          total: 25,
          limit: 24,
          offset: 0,
        },
      };
      const payload = payloads[`${init?.method ?? "GET"} ${path}`] ?? payloads[`GET ${path}`];
      return {
        ok: true,
        status: 200,
        text: async () => (payload === undefined ? "{}" : JSON.stringify(payload)),
      };
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Collections" }));

    await waitFor(() => expect(screen.getByRole("button", { name: /Weeknight/ })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Next" }));

    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes("/collections?limit=24&offset=24"))).toBe(true));
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
      "GET /internal/recipes/recipe-1/embedding-input": {
        recipeId: "recipe-1",
        input: "soup cook",
        inputHash: "hash-soup",
      },
    });

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Import" }));
    fireEvent.change(screen.getByLabelText("Text"), { target: { value: "Soup recipe" } });
    fireEvent.click(screen.getByRole("button", { name: "Import recipe" }));

    await waitFor(() => expect(screen.getByRole("heading", { name: "Soup" })).toBeTruthy());
    expect(screen.getAllByText("MANUAL").length).toBeGreaterThan(0);
  });

  it("shows internal import jobs with status history and events", async () => {
    mockFetch({
      "GET /recipes": { items: [] },
      "GET /internal/import-jobs": {
        items: [
          {
            id: "job-1",
            ownerId: "local-user",
            clientId: "client-1",
            clientImportId: "import-1",
            status: "succeeded",
            createdRecipeId: "recipe-1",
            startedAt: "2026-06-27T10:00:00Z",
            finishedAt: "2026-06-27T10:01:00Z",
            statusHistory: [
              { status: "queued", changedAt: "2026-06-27T09:59:00Z" },
              { status: "running", changedAt: "2026-06-27T10:00:00Z" },
              { status: "succeeded", changedAt: "2026-06-27T10:01:00Z" },
            ],
            sources: [{ id: "source-1", type: "URL", status: "ready", url: "https://example.com/post", position: 0 }],
            events: [{ id: "event-1", eventType: "recipe_created", createdAt: "2026-06-27T10:01:00Z" }],
          },
        ],
      },
    });

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Import jobs" }));

    await waitFor(() => expect(screen.getByRole("heading", { name: "Import jobs / Job events" })).toBeTruthy());
    expect(screen.getByText("job-1")).toBeTruthy();
    expect(screen.getByText(/user local-user/)).toBeTruthy();
    expect(screen.getByText(/queued/)).toBeTruthy();
    expect(screen.getByText(/running/)).toBeTruthy();
    expect(screen.getByText(/recipe_created/)).toBeTruthy();
    expect(screen.getByText(/https:\/\/example.com\/post/)).toBeTruthy();
  });

  it("shows internal recipe embedding status", async () => {
    mockFetch({
      "GET /recipes": { items: [] },
      "GET /internal/embeddings": {
        items: [
          {
            recipeId: "recipe-1",
            ownerId: "local-user",
            recipeTitle: "Soup",
            status: "ready",
            model: "test-embedding",
            inputHash: "abcdef1234567890",
            failedAttempts: 1,
            updatedAt: "2026-07-02T10:00:00Z",
            lastAttemptAt: "2026-07-02T09:59:00Z",
            events: [
              {
                id: "event-1",
                eventType: "saved",
                statusAfter: "ready",
                createdAt: "2026-07-02T10:00:00Z",
                payload: { dimension: 1536 },
              },
            ],
          },
        ],
      },
      "POST /internal/embeddings/recipe-1/retry": {},
    });

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Embeddings" }));

    await waitFor(() => expect(screen.getByRole("heading", { name: "Recipe embeddings" })).toBeTruthy());
    expect(screen.getByText("Soup")).toBeTruthy();
    expect(screen.getByText(/ready - user local-user - recipe recipe-1/)).toBeTruthy();
    expect(screen.getByText("test-embedding")).toBeTruthy();
    expect(screen.getByText("abcdef123456...")).toBeTruthy();
    expect(screen.getByText("Events (1)")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/internal/embeddings/recipe-1/retry"),
      expect.objectContaining({ method: "POST" }),
    ));
  });

  it("shows internal search debug explanation and embedding input preview", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const path = new URL(url).pathname;
      const method = init?.method ?? "GET";
      const payloads: Record<string, unknown> = {
        "GET /recipes": { items: [] },
        "GET /notifications": { items: [] },
        "POST /internal/search/explain": {
          textPresent: true,
          filters: { tagId: null, ingredientQueries: ["apple"], sourceName: null, authorName: null, titleRecipeId: null },
          provider: "test",
          model: "test-embedding",
          distanceMetric: "cosine",
          candidateCount: 1,
          returnedCount: 1,
          limit: 20,
          offset: 0,
          hasMore: false,
          snapshotPersisted: false,
          items: [
            {
              id: "recipe-1",
              title: "Apple Cake",
              coverImage: null,
              hasOpenReviewFlags: false,
              matchReasons: [
                { type: "ingredient_query", label: "apple", score: null },
                { type: "semantic", label: "Semantic match", score: 0.9 },
              ],
              debug: {
                rank: 1,
                distance: 0.1,
                similarity: 0.9,
                embeddingStatus: "ready",
                embeddingModel: "test-embedding",
                inputHash: "abcdef1234567890",
                embeddingInputPreview: "apple cake apple bake",
              },
            },
          ],
        },
        "GET /internal/recipes/recipe-1/embedding-input": {
          recipeId: "recipe-1",
          input: "apple cake apple bake",
          inputHash: "abcdef1234567890",
        },
      };
      const payload = payloads[`${method} ${path}`] ?? payloads[`GET ${path}`];
      return {
        ok: true,
        status: 200,
        text: async () => (payload === undefined ? "{}" : JSON.stringify(payload)),
      };
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Search Debug" }));

    await waitFor(() => expect(screen.getByRole("heading", { name: "Search Debug" })).toBeTruthy());
    fireEvent.change(screen.getByLabelText("Search text"), { target: { value: "apple cake" } });
    fireEvent.change(screen.getByLabelText("Selected chips JSON"), { target: { value: '[{"type":"ingredient_query","value":"apple"}]' } });
    fireEvent.click(screen.getByRole("button", { name: "Explain search" }));

    await waitFor(() => expect(screen.getByText("Apple Cake")).toBeTruthy());
    expect(screen.getByText(/query provider test - query model test-embedding/)).toBeTruthy();
    expect(screen.getByText("cosine")).toBeTruthy();
    expect(screen.getByText("recipe-1")).toBeTruthy();
    expect(screen.getByText("ready")).toBeTruthy();
    expect(screen.getByText("apple cake apple bake")).toBeTruthy();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/internal/search/explain"),
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining('"ingredient_query"'),
      }),
    ));
  });

  it("shows notification history, marks notifications read, and opens successful recipe imports", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const path = new URL(url).pathname;
      const method = init?.method ?? "GET";
      const payloads: Record<string, unknown> = {
        "GET /recipes": { items: [] },
        "GET /notifications": {
          items: [
            {
              id: "notification-1",
              type: "IMPORT_SUCCEEDED",
              status: "unread",
              title: "Import completed",
              message: "Soup was imported.",
              entityType: "RECIPE",
              entityId: "recipe-1",
              createdAt: "2026-06-27T10:01:00Z",
            },
          ],
        },
        "GET /tags": { items: [] },
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
        "GET /internal/recipes/recipe-1/embedding-input": {
          recipeId: "recipe-1",
          input: "soup cook",
          inputHash: "hash-soup",
        },
        "GET /collections": { items: [] },
      };
      const payload = payloads[`${method} ${path}`] ?? payloads[`GET ${path}`];
      return {
        ok: true,
        status: method === "PATCH" ? 200 : 200,
        text: async () => (payload === undefined ? "{}" : JSON.stringify(payload)),
      };
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    await waitFor(() => expect(screen.getByRole("status").textContent).toContain("Import completed"));
    fireEvent.click(screen.getByRole("button", { name: "Notifications" }));

    await waitFor(() => expect(screen.getByRole("heading", { name: "Notifications" })).toBeTruthy());
    expect(screen.getAllByText("Soup was imported.").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Mark read" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/notifications/notification-1"),
      expect.objectContaining({
        method: "PATCH",
        body: expect.stringContaining('"status":"read"'),
      }),
    ));

    fireEvent.click(screen.getByRole("button", { name: "Open recipe" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Soup" })).toBeTruthy());
  });

  it("marks all visible unread notifications read through the newest notification cutoff", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const path = new URL(url).pathname;
      const method = init?.method ?? "GET";
      const payloads: Record<string, unknown> = {
        "GET /recipes": { items: [] },
        "GET /notifications": {
          items: [
            {
              id: "notification-new",
              type: "IMPORT_SUCCEEDED",
              status: "unread",
              title: "Newest",
              message: "Newest notification.",
              createdAt: "2026-06-27T10:02:00Z",
            },
            {
              id: "notification-old",
              type: "IMPORT_STARTED",
              status: "unread",
              title: "Older",
              message: "Older notification.",
              createdAt: "2026-06-27T10:01:00Z",
            },
          ],
        },
      };
      const payload = payloads[`${method} ${path}`] ?? payloads[`GET ${path}`];
      return {
        ok: true,
        status: 200,
        text: async () => (payload === undefined ? "{}" : JSON.stringify(payload)),
      };
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Notifications" }));

    await waitFor(() => expect(screen.getByRole("heading", { name: "Notifications" })).toBeTruthy());
    await waitFor(() => expect(screen.getAllByText("Newest notification.").length).toBeGreaterThan(0));
    fireEvent.click(screen.getByRole("button", { name: "Mark all read" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/notifications/read-all"),
      expect.objectContaining({
        method: "PATCH",
        body: expect.stringContaining('"lastNotificationId":"notification-new"'),
      }),
    ));
  });

  it("manages tags and confirms deletion with usage count", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const path = new URL(url).pathname;
      const method = init?.method ?? "GET";
      const payloads: Record<string, unknown> = {
        "GET /recipes": { items: [] },
        "GET /notifications": { items: [] },
        "GET /tags": {
          items: [{ id: "tag-1", name: "breakfast", description: "Morning food" }],
          total: 1,
          limit: 24,
          offset: 0,
        },
        "POST /tags": { id: "tag-2", name: "dessert", description: "Sweet" },
        "PATCH /tags/tag-1": { id: "tag-1", name: "brunch", description: "Late morning" },
        "GET /tags/tag-1/usage": { recipeCount: 2 },
        "DELETE /tags/tag-1": {
          id: "tag-1",
          name: "brunch",
          description: "Late morning",
          deletedAt: "2026-06-28T10:00:00Z",
        },
      };
      const payload = payloads[`${method} ${path}`] ?? payloads[`GET ${path}`];
      return {
        ok: true,
        status: method === "DELETE" ? 200 : 200,
        text: async () => (payload === undefined ? "{}" : JSON.stringify(payload)),
      };
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Tags" }));

    await waitFor(() => expect(screen.getByRole("heading", { name: "Tags (1)" })).toBeTruthy());
    await waitFor(() => expect(screen.getByDisplayValue("breakfast")).toBeTruthy());
    expect(screen.queryByText("Name for breakfast")).toBeNull();
    expect(screen.queryByText("Description for breakfast")).toBeNull();
    expect(screen.queryByText("Save breakfast")).toBeNull();
    expect(screen.queryByText("Delete breakfast")).toBeNull();

    fireEvent.change(screen.getAllByPlaceholderText("Name")[0], { target: { value: "dessert" } });
    fireEvent.change(screen.getAllByPlaceholderText("Description")[0], { target: { value: "Sweet" } });
    fireEvent.click(screen.getByRole("button", { name: "Create tag" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/tags"),
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining('"name":"dessert"'),
      }),
    ));

    fireEvent.change(screen.getByDisplayValue("breakfast"), { target: { value: "brunch" } });
    fireEvent.change(screen.getByDisplayValue("Morning food"), { target: { value: "Late morning" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/tags/tag-1"),
      expect.objectContaining({
        method: "PATCH",
        body: expect.stringContaining('"name":"brunch"'),
      }),
    ));

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes("/tags/tag-1/usage"))).toBe(true));
    expect(confirmSpy).toHaveBeenCalledWith("This tag is used by 2 recipes.");
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/tags/tag-1"),
      expect.objectContaining({ method: "DELETE" }),
    ));
  });

  it("paginates tag management requests", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = new URL(String(input));
      const path = url.pathname;
      const payloads: Record<string, unknown> = {
        "/recipes": { items: [], total: 0, limit: 24, offset: 0 },
        "/notifications": { items: [] },
      };
      if (path === "/tags") {
        const offset = Number(url.searchParams.get("offset") ?? "0");
        return {
          ok: true,
          status: 200,
          text: async () => JSON.stringify({
            items: [{ id: `tag-${offset}`, name: `tag ${offset}`, description: null }],
            total: 50,
            limit: 24,
            offset,
          }),
        };
      }
      return {
        ok: true,
        status: 200,
        text: async () => JSON.stringify(payloads[path] ?? {}),
      };
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Tags" }));

    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes("/tags?limit=24&offset=0"))).toBe(true));
    await waitFor(() => expect(screen.getByText("Showing 1-24 of 50")).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => String(url).includes("/tags?limit=24&offset=24"))).toBe(true));
  });
});
