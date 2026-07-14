import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  DEFAULT_API_BASE_URL,
  deleteRecipe,
  createImport,
  getMediaBlob,
  listRecipes,
  mediaUrl,
  setApiDebugLoggingForTests,
  setApiTokenProvider,
} from "./client";

describe("api client", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
    setApiDebugLoggingForTests(false);
    setApiTokenProvider(null);
  });

  it("sends import form data with a stable client id", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ jobId: "job-1", status: "pending" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await createImport({ clientImportId: "import-1", text: "Recipe" });

    expect(fetchMock).toHaveBeenCalledOnce();
    const [, init] = fetchMock.mock.calls[0];
    expect(new Headers(init.headers).get("X-Client-Id")).toMatch(/^local_/);
    expect(init.body).toBeInstanceOf(FormData);
  });

  it("requests a fresh bearer token for every API request", async () => {
    const tokens = ["token-one", "token-two"];
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, text: async () => JSON.stringify({ items: [] }) });
    vi.stubGlobal("fetch", fetchMock);
    setApiTokenProvider(async () => tokens.shift() ?? null);

    await listRecipes();
    await listRecipes();

    expect(new Headers(fetchMock.mock.calls[0][1].headers).get("Authorization")).toBe("Bearer token-one");
    expect(new Headers(fetchMock.mock.calls[1][1].headers).get("Authorization")).toBe("Bearer token-two");
  });

  it("loads protected media with a bearer token", async () => {
    const blob = new Blob(["image"], { type: "image/jpeg" });
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, blob: async () => blob });
    vi.stubGlobal("fetch", fetchMock);
    setApiTokenProvider(async () => "media-token");

    await expect(getMediaBlob("/media/image-key")).resolves.toBe(blob);

    expect(fetchMock).toHaveBeenCalledOnce();
    expect(fetchMock.mock.calls[0][0]).toBe(`${DEFAULT_API_BASE_URL}/media/image-key`);
    expect(new Headers(fetchMock.mock.calls[0][1].headers).get("Authorization")).toBe("Bearer media-token");
  });

  it("throws ApiError for backend error payloads", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => ({ errorCode: "NOT_A_RECIPE", message: "Add a source." }),
      }),
    );

    await expect(createImport({ clientImportId: "import-1" })).rejects.toMatchObject({
      errorCode: "NOT_A_RECIPE",
      message: "Add a source.",
    } satisfies Partial<ApiError>);
  });

  it("fetches recipe list", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ items: [{ id: "recipe-1", title: "Soup" }] }),
      }),
    );

    const recipes = await listRecipes();

    expect(recipes.items[0].title).toBe("Soup");
  });

  it("logs frontend api requests when debug logging is enabled", async () => {
    const info = vi.spyOn(console, "info").mockImplementation(() => undefined);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ items: [] }),
      }),
    );
    setApiDebugLoggingForTests(true);

    await listRecipes();

    expect(info).toHaveBeenCalledWith("[recipes.frontend.api] request", expect.objectContaining({ method: "GET", path: "/recipes" }));
    expect(info).toHaveBeenCalledWith(
      "[recipes.frontend.api] response",
      expect.objectContaining({ method: "GET", path: "/recipes", status: 200 }),
    );
  });

  it("handles empty 204 responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 204,
        text: async () => "",
      }),
    );

    await expect(deleteRecipe("recipe-1")).resolves.toBeUndefined();
  });

  it("routes local media through the gateway base", () => {
    const configuredBase = import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;

    expect(DEFAULT_API_BASE_URL).toBe("http://127.0.0.1:8081");
    expect(mediaUrl("/media/image-key")).toBe(`${configuredBase}/media/image-key`);
    expect(mediaUrl("https://cdn.example.test/image.jpg")).toBe("https://cdn.example.test/image.jpg");
  });
});
