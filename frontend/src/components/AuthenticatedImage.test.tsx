import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({ getMediaBlob: vi.fn() }));

vi.mock("../api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/client")>()),
  getMediaBlob: mocks.getMediaBlob,
}));

import { AuthenticatedImage } from "./AuthenticatedImage";

describe("AuthenticatedImage", () => {
  const createObjectURL = vi.fn(() => "blob:authenticated-image");
  const revokeObjectURL = vi.fn();

  beforeEach(() => {
    mocks.getMediaBlob.mockResolvedValue(new Blob(["image"], { type: "image/jpeg" }));
    vi.stubGlobal("URL", { ...URL, createObjectURL, revokeObjectURL });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("renders protected API media from an authenticated blob URL", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { unmount } = render(
      <QueryClientProvider client={client}>
        <AuthenticatedImage src="/media/image-key" alt="Recipe" />
      </QueryClientProvider>,
    );

    const image = screen.getByAltText("Recipe");
    expect(image.getAttribute("src")).toBeNull();
    await waitFor(() => expect(image.getAttribute("src")).toBe("blob:authenticated-image"));
    expect(mocks.getMediaBlob).toHaveBeenCalledWith("/media/image-key");

    unmount();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:authenticated-image");
  });
});
