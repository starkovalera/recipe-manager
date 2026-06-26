import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RecipeDetailPage } from "./RecipeDetailPage";


function renderPage(recipeId = "recipe-1") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <RecipeDetailPage recipeId={recipeId} onDeleted={() => undefined} />
    </QueryClientProvider>,
  );
}

describe("RecipeDetailPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  const recipeDetail = {
    id: "recipe-1",
    title: "Soup",
    note: null,
    instructions: ["Cook."],
    ingredients: [{ id: "ingredient-1", name: "Tomato", position: 0 }],
    sourceName: "MANUAL",
    tags: [],
    nutritionEstimate: null,
    images: [{ id: "image-1", role: "SOURCE", mediaUrl: "/media/source.jpg" }],
    coverImage: { id: "cover-1", role: "COVER", mediaUrl: "/media/cover.jpg", sourceImageId: "image-1" },
    coverOptions: [
      { kind: "CURRENT_COVER", label: "Current cover", selected: true, image: { id: "cover-1", role: "COVER", mediaUrl: "/media/cover.jpg", sourceImageId: "image-1" } },
      { kind: "DEFAULT", label: "Default image", selected: false },
      { kind: "IMAGE", label: "Source image", selected: false, image: { id: "image-1", role: "SOURCE", mediaUrl: "/media/source.jpg" } },
    ],
    collections: [],
    sources: [],
    reviewFlags: [],
  };

  function stubRecipeFetch() {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => {
      const url = input.toString();
      if (url.includes("/collections")) {
        return { ok: true, json: async () => ({ items: [] }) };
      }
      if (url.includes("/recipes/recipe-1")) {
        return { ok: true, json: async () => recipeDetail };
      }
      return { ok: true, json: async () => ({ items: [] }) };
    });
    vi.stubGlobal("fetch", fetchMock);
    return fetchMock;
  }

  it("renders cover and source images", async () => {
    stubRecipeFetch();

    renderPage();

    await waitFor(() => expect(screen.getByAltText("Soup cover")).toBeTruthy());
    expect(screen.getByAltText("Current cover")).toBeTruthy();
    await waitFor(() => expect((screen.getByRole("radio", { name: /Current cover/i }) as HTMLInputElement).checked).toBe(true));
    expect(screen.getByAltText("Source image")).toBeTruthy();
  });

  it("saves the generated current cover when it remains selected", async () => {
    const fetchMock = stubRecipeFetch();
    renderPage();

    await waitFor(() => expect((screen.getByRole("radio", { name: /Current cover/i }) as HTMLInputElement).checked).toBe(true));
    fireEvent.click(screen.getByRole("button", { name: /Save/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/recipes/recipe-1"),
      expect.objectContaining({
        method: "PATCH",
        body: expect.stringContaining('"imageId":"cover-1"'),
      }),
    ));
  });
});
