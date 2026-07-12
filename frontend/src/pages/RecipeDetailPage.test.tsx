import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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

  afterEach(() => {
    cleanup();
  });

  const recipeDetail = {
    id: "recipe-1",
    title: "Soup",
    note: null,
    instructions: ["Cook."],
    ingredients: [{ id: "ingredient-1", name: "Tomato", quantity: "2", unit: "pcs", note: "ripe", position: 0 }],
    sourceName: "MANUAL",
    authorName: "chef",
    tags: [{ id: "tag-1", name: "quick", description: null }],
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

  function stubRecipeFetch(detail = recipeDetail) {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => {
      const url = input.toString();
      if (url.includes("/collections")) {
        return { ok: true, json: async () => ({ items: [] }) };
      }
      if (url.includes("/tags")) {
        return {
          ok: true,
          json: async () => ({
            items: [
              { id: "tag-1", name: "quick", description: null },
              { id: "tag-2", name: "dinner", description: "Evening" },
            ],
          }),
        };
      }
      if (url.includes("/internal/recipes/recipe-1/embedding-input")) {
        return { ok: true, json: async () => ({ recipeId: "recipe-1", input: "soup tomato cook", inputHash: "hash-soup" }) };
      }
      if (url.includes("/recipes/recipe-1")) {
        return { ok: true, json: async () => detail };
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

  it("explains that a missing recipe may have been deleted", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.includes("/recipes/recipe-1") && !url.includes("/internal/")) {
        return {
          ok: false,
          status: 404,
          text: async () => JSON.stringify({ errorCode: "RECIPE_NOT_FOUND", message: "Recipe not found." }),
        };
      }
      return { ok: true, status: 200, text: async () => JSON.stringify({ items: [] }) };
    }));

    renderPage();

    await waitFor(() => expect(screen.getByText("Recipe not found. It may have been deleted.")).toBeTruthy());
  });

  it("does not render cached recipe content after a not-found refetch", async () => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.includes("/recipes/recipe-1") && !url.includes("/internal/")) {
        return {
          ok: false,
          status: 404,
          text: async () => JSON.stringify({ errorCode: "RECIPE_NOT_FOUND", message: "Recipe not found." }),
        };
      }
      return { ok: true, status: 200, text: async () => JSON.stringify({ items: [] }) };
    }));
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    client.setQueryData(["recipe", "recipe-1"], recipeDetail);

    render(
      <QueryClientProvider client={client}>
        <RecipeDetailPage recipeId="recipe-1" onDeleted={() => undefined} />
      </QueryClientProvider>,
    );

    await waitFor(() => expect(screen.getByText("Recipe not found. It may have been deleted.")).toBeTruthy());
    expect(screen.queryByRole("heading", { name: "Soup" })).toBeNull();
    expect(screen.queryByText("Tomato")).toBeNull();
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

  it("selects existing active tags and saves recipe tagIds without free-form tag input", async () => {
    const fetchMock = stubRecipeFetch();
    renderPage();

    await waitFor(() => expect(screen.getByRole("button", { name: /dinner/i })).toBeTruthy());
    expect(screen.queryByLabelText("Tags")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: /dinner/i }));
    fireEvent.click(screen.getByRole("button", { name: /^Save$/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/recipes/recipe-1"),
      expect.objectContaining({
        method: "PATCH",
        body: expect.stringContaining('"tagIds":["tag-1","tag-2"]'),
      }),
    ));
  });

  it("edits ingredients as structured rows and saves them with the recipe", async () => {
    const fetchMock = stubRecipeFetch();
    renderPage();

    await waitFor(() => expect(screen.getByLabelText("Ingredient 1 name")).toBeTruthy());
    expect(screen.getByLabelText("Ingredient 1 quantity")).toHaveProperty("value", "2");
    expect(screen.getByLabelText("Ingredient 1 unit")).toHaveProperty("value", "pcs");
    expect(screen.getByLabelText("Ingredient 1 note")).toHaveProperty("value", "ripe");

    fireEvent.change(screen.getByLabelText("Ingredient 1 name"), { target: { value: "Cherry tomato" } });
    fireEvent.change(screen.getByLabelText("Ingredient 1 quantity"), { target: { value: "200" } });
    fireEvent.change(screen.getByLabelText("Ingredient 1 unit"), { target: { value: "g" } });
    fireEvent.change(screen.getByLabelText("Ingredient 1 note"), { target: { value: "halved" } });
    fireEvent.click(screen.getByRole("button", { name: /^Save$/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/recipes/recipe-1"),
      expect.objectContaining({
        method: "PATCH",
        body: expect.stringContaining('"ingredients":[{"id":"ingredient-1","name":"Cherry tomato","quantity":"200","unit":"g","note":"halved"}]'),
      }),
    ));
  });

  it("edits source metadata and saves it with the recipe", async () => {
    const fetchMock = stubRecipeFetch();
    renderPage();

    await waitFor(() => expect(screen.getByLabelText("Author name")).toBeTruthy());
    expect(screen.getByLabelText("Author name")).toHaveProperty("value", "chef");
    expect(screen.getByLabelText("Source type")).toHaveProperty("value", "MANUAL");

    fireEvent.change(screen.getByLabelText("Author name"), { target: { value: "thread_chef" } });
    fireEvent.change(screen.getByLabelText("Source type"), { target: { value: "THREADS" } });
    fireEvent.click(screen.getByRole("button", { name: /^Save$/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/recipes/recipe-1"),
      expect.objectContaining({
        method: "PATCH",
        body: expect.stringContaining('"sourceName":"THREADS"'),
      }),
    ));
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/recipes/recipe-1"),
      expect.objectContaining({
        method: "PATCH",
        body: expect.stringContaining('"authorName":"thread_chef"'),
      }),
    );
  });

  it("adds and deletes ingredient rows locally before saving", async () => {
    const fetchMock = stubRecipeFetch();
    renderPage();

    await waitFor(() => expect(screen.getByLabelText("New ingredient name")).toBeTruthy());
    fireEvent.change(screen.getByLabelText("New ingredient name"), { target: { value: "Basil" } });
    fireEvent.change(screen.getByLabelText("New ingredient quantity"), { target: { value: "5" } });
    fireEvent.change(screen.getByLabelText("New ingredient unit"), { target: { value: "leaves" } });
    fireEvent.click(screen.getByRole("button", { name: /Add ingredient/i }));

    expect(screen.getByLabelText("Ingredient 2 name")).toHaveProperty("value", "Basil");
    fireEvent.click(screen.getByRole("button", { name: /Delete ingredient 1/i }));
    expect(screen.queryByLabelText("Ingredient 1 name")).toBeTruthy();
    expect(screen.getByLabelText("Ingredient 1 name")).toHaveProperty("value", "Basil");

    fireEvent.click(screen.getByRole("button", { name: /^Save$/i }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/recipes/recipe-1"),
      expect.objectContaining({
        method: "PATCH",
        body: expect.stringContaining('"ingredients":[{"name":"Basil","quantity":"5","unit":"leaves","note":null}]'),
      }),
    ));
  });

  it("validates editable recipe limits before saving", async () => {
    const fetchMock = stubRecipeFetch({
      ...recipeDetail,
      ingredients: Array.from({ length: 51 }, (_, index) => ({
        id: `ingredient-${index}`,
        name: `Ingredient ${index}`,
        quantity: "",
        unit: "",
        note: "",
        position: index,
      })),
    });
    renderPage();

    await waitFor(() => expect(screen.getByLabelText("Ingredient 51 name")).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: /Save/i }));

    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("Recipe is too long."));
    expect(fetchMock).not.toHaveBeenCalledWith(
      expect.stringContaining("/recipes/recipe-1"),
      expect.objectContaining({ method: "PATCH" }),
    );
  });

  it("validates empty ingredient names before saving", async () => {
    const fetchMock = stubRecipeFetch();
    renderPage();

    await waitFor(() => expect(screen.getByLabelText("Ingredient 1 name")).toBeTruthy());
    fireEvent.change(screen.getByLabelText("Ingredient 1 name"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: /Save/i }));

    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("Ingredient name is required."));
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
