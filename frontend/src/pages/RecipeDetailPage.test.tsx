import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RecipeDetailPage } from "./RecipeDetailPage";


function renderPage(recipeId = "recipe-1") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <RecipeDetailPage recipeId={recipeId} />
    </QueryClientProvider>,
  );
}

describe("RecipeDetailPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders cover and source images", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          id: "recipe-1",
          title: "Soup",
          note: null,
          instructions: ["Cook."],
          ingredients: [{ id: "ingredient-1", name: "Tomato", position: 0 }],
          images: [{ id: "image-1", role: "SOURCE", mediaUrl: "/media/source.jpg" }],
          coverImage: { id: "cover-1", role: "COVER", mediaUrl: "/media/cover.jpg", sourceImageId: "image-1" },
          sources: [],
          reviewFlags: [],
        }),
      }),
    );

    renderPage();

    await waitFor(() => expect(screen.getByAltText("Soup cover")).toBeTruthy());
    expect(screen.getByAltText("Soup source image 1")).toBeTruthy();
  });
});
