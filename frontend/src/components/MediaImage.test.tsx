import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MediaImage } from "./MediaImage";

function renderImage(grant?: Parameters<typeof MediaImage>[0]["grant"]) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MediaImage grant={grant} fallbackSrc="/default.svg" alt="Recipe" />
    </QueryClientProvider>,
  );
}

describe("MediaImage", () => {
  beforeEach(() => vi.restoreAllMocks());
  afterEach(() => cleanup());

  it("uses direct grants without fetching the media", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    renderImage({ url: "https://signed.example/image", contentType: "image/jpeg", accessMode: "direct" });

    expect(screen.getByAltText("Recipe").getAttribute("src")).toBe("https://signed.example/image");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("fetches authenticated grants and revokes the object URL", async () => {
    const blob = new Blob(["image"], { type: "image/jpeg" });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, status: 200, blob: async () => blob }));
    const createObjectURL = vi.fn().mockReturnValue("blob:recipe");
    const revokeObjectURL = vi.fn();
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: createObjectURL });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revokeObjectURL });

    const view = renderImage({ url: "/media/recipe_image/image-1", contentType: "image/jpeg", accessMode: "authenticated_fetch" });
    await waitFor(() => expect(screen.getByAltText("Recipe").getAttribute("src")).toBe("blob:recipe"));
    expect(createObjectURL).toHaveBeenCalledWith(blob);

    view.unmount();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:recipe");
  });
});
