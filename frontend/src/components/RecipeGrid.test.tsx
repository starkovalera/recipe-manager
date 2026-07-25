import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { RecipeGrid } from "./RecipeGrid";

describe("RecipeGrid media access", () => {
  beforeEach(() => vi.restoreAllMocks());
  afterEach(() => cleanup());

  it("batches visible covers and preserves successful siblings", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      text: async () => JSON.stringify({
        items: [
          {
            type: "recipe_image",
            id: "image-1",
            grant: { url: "https://signed.example/image-1", expiresAt: "2099-01-01T00:00:00Z", contentType: "image/jpeg", accessMode: "direct" },
          },
          { type: "recipe_image", id: "image-2", error: { code: "MEDIA_NOT_FOUND", message: "Media is unavailable." } },
        ],
      }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={client}>
        <RecipeGrid
          recipes={[
            { id: "recipe-1", title: "Soup", coverImage: { id: "image-1" } },
            { id: "recipe-2", title: "Salad", coverImage: { id: "image-2" } },
          ]}
          onSelect={vi.fn()}
        />
      </QueryClientProvider>,
    );

    await waitFor(() => expect(screen.getByAltText("Soup cover").getAttribute("src")).toBe("https://signed.example/image-1"));
    expect(screen.getByAltText("Salad cover").getAttribute("src")).toContain("default-recipe.svg");
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      items: [
        { type: "recipe_image", id: "image-1" },
        { type: "recipe_image", id: "image-2" },
      ],
    });
  });
});
