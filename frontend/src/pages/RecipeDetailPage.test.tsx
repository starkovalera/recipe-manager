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
    sources: [
      {
        id: "source-url",
        type: "URL",
        source: "MANUAL",
        status: "ignored",
        url: "https://example.test/post",
      },
      {
        id: "source-image",
        type: "IMAGE",
        source: "URL",
        status: "used",
        parentSourceId: "source-url",
        imageId: "image-1",
      },
    ],
    debugSources: [],
    reviewFlags: [
      {
        id: "flag-1",
        type: "CONTENT_WARNING",
        status: "open",
        reasonCode: "CONTENT_WARNING",
        message: "Review suggested: CONTENT_WARNING.",
        details: { hasConflicts: true, hasIgnored: true },
      },
    ],
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
    expect(screen.getByRole("button", { name: /Open Current cover/i })).toBeTruthy();
    expect(screen.getByAltText("Source image")).toBeTruthy();
  });

  it("shows an open review warning and resolves it", async () => {
    const fetchMock = stubRecipeFetch();

    renderPage();

    await waitFor(() => expect(screen.getAllByText(/requires review/i).length).toBeGreaterThan(0));
    expect(screen.getByText(/conflicting information/i)).toBeTruthy();
    expect(screen.getByText(/some sources were ignored/i)).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /resolve warning/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/recipes/recipe-1/review-flags/flag-1"),
      expect.objectContaining({
        method: "PATCH",
        body: expect.stringContaining('"status":"resolved"'),
      }),
    ));
  });

  it("shows URL source warning and can keep ignored source", async () => {
    const fetchMock = stubRecipeFetch();

    renderPage();

    await waitFor(() => expect(screen.getByText("https://example.test/post")).toBeTruthy());
    expect(screen.getByText(/ignored when creating the recipe/i)).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /keep source/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/recipes/recipe-1/sources/source-url"),
      expect.objectContaining({
        method: "PATCH",
        body: expect.stringContaining('"status":"used"'),
      }),
    ));
  });

  it("opens source image preview and can set an image as cover", async () => {
    const fetchMock = stubRecipeFetch();

    renderPage();

    await waitFor(() => expect(screen.getByRole("button", { name: /Open Source image/i })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /Open Source image/i }));
    expect(screen.getByRole("dialog", { name: /Source image/i })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /Use Source image as cover/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/recipes/recipe-1"),
      expect.objectContaining({
        method: "PATCH",
        body: expect.stringContaining('"imageId":"image-1"'),
      }),
    ));
  });

  it("saves the generated current cover when it remains selected", async () => {
    const fetchMock = stubRecipeFetch();
    renderPage();

    await waitFor(() => expect(screen.getByRole("button", { name: /Save/i })).toBeTruthy());
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
