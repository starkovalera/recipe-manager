import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, createImport, listRecipes, setApiDebugLoggingForTests } from "./client";

describe("api client", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
    setApiDebugLoggingForTests(false);
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
    expect(init.headers["X-Client-Id"]).toMatch(/^local_/);
    expect(init.body).toBeInstanceOf(FormData);
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
});
