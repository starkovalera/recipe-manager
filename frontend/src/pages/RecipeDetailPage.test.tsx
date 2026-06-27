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
    images: [{ id: "image-1", mediaUrl: "/media/source.jpg" }, { id: "cover-1", mediaUrl: "/media/cover.jpg" }],
    coverImage: { id: "cover-1", mediaUrl: "/media/cover.jpg" },
    coverOptions: [
      { kind: "IMAGE", label: "Current cover", selected: true, image: { id: "cover-1", mediaUrl: "/media/cover.jpg" } },
      { kind: "DEFAULT", label: "Default image", selected: false },
      { kind: "IMAGE", label: "Source image", selected: false, image: { id: "image-1", mediaUrl: "/media/source.jpg" } },
    ],
    collections: [],
    resources: [
      {
        id: "source-url",
        type: "URL",
        source: "MANUAL",
        role: "SOURCE",
        status: "ignored",
        url: "https://example.test/post",
      },
      {
        id: "source-image",
        type: "IMAGE",
        source: "URL",
        role: "SOURCE",
        status: "used",
        parentResourceId: "source-url",
        imageId: "image-1",
      },
      {
        id: "source-cover",
        type: "IMAGE",
        source: "GENERATED",
        role: "COVER_CANDIDATE",
        status: "used",
        imageId: "cover-1",
      },
    ],
    sources: [],
    debugResources: [],
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
      expect.stringContaining("/recipes/recipe-1/resources/source-url"),
      expect.objectContaining({
        method: "PATCH",
        body: expect.stringContaining('"status":"used"'),
      }),
    ));
  });

  it("shows delete source info and confirms before deleting source resources", async () => {
    const fetchMock = stubRecipeFetch();
    vi.stubGlobal("confirm", vi.fn(() => false));

    renderPage();

    await waitFor(() => expect(screen.getByText("https://example.test/post")).toBeTruthy());
    const deleteButton = screen.getByRole("button", { name: /delete source/i });
    const infoButton = screen.getByLabelText(/source deletion details/i);
    expect(infoButton.getAttribute("title")).toBe("Delete the link and all related media files.");
    expect(deleteButton.compareDocumentPosition(infoButton) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

    fireEvent.click(deleteButton);

    expect(globalThis.confirm).toHaveBeenCalledWith("Are you sure you want to delete this source?");
    expect(fetchMock).not.toHaveBeenCalledWith(
      expect.stringContaining("/recipes/recipe-1/resources/source-url"),
      expect.objectContaining({ method: "PATCH" }),
    );
  });

  it("confirms before deleting image resources", async () => {
    const fetchMock = stubRecipeFetch();
    vi.stubGlobal("confirm", vi.fn(() => true));

    renderPage();

    await waitFor(() => expect(screen.getByRole("button", { name: /Delete image/i })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /Delete image/i }));

    expect(globalThis.confirm).toHaveBeenCalledWith("Are you sure you want to delete this image?");
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/recipes/recipe-1/resources/source-image"),
      expect.objectContaining({
        method: "PATCH",
        body: expect.stringContaining('"status":"deleted"'),
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

  it("validates editable recipe limits before saving", async () => {
    const fetchMock = stubRecipeFetch();
    renderPage();

    await waitFor(() => expect(screen.getByRole("button", { name: /Save/i })).toBeTruthy());
    fireEvent.change(screen.getByLabelText("Ingredients"), {
      target: { value: Array.from({ length: 51 }, (_, index) => `Ingredient ${index}`).join("\n") },
    });
    fireEvent.click(screen.getByRole("button", { name: /Save/i }));

    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("Recipe is too long."));
    expect(fetchMock).not.toHaveBeenCalledWith(
      expect.stringContaining("/recipes/recipe-1"),
      expect.objectContaining({ method: "PATCH" }),
    );
  });

  it("validates editable note length before saving", async () => {
    const fetchMock = stubRecipeFetch();
    renderPage();

    await waitFor(() => expect(screen.getByRole("button", { name: /Save/i })).toBeTruthy());
    fireEvent.change(screen.getByLabelText("Note"), { target: { value: "x".repeat(501) } });
    fireEvent.click(screen.getByRole("button", { name: /Save/i }));

    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("Recipe note is too long."));
    expect(fetchMock).not.toHaveBeenCalledWith(
      expect.stringContaining("/recipes/recipe-1"),
      expect.objectContaining({ method: "PATCH" }),
    );
  });
});
