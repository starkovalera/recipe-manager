import { describe, expect, it, vi } from "vitest";

import { grantRefreshDelay, mediaReferenceKey } from "./useMediaAccess";

describe("media access cache helpers", () => {
  it("keys grants by stable type and id", () => {
    expect(mediaReferenceKey({ type: "recipe_image", id: "image-1" })).toBe("recipe_image:image-1");
  });

  it("refreshes expiring direct grants before expiry", () => {
    vi.spyOn(Date, "now").mockReturnValue(new Date("2026-07-24T10:00:00Z").getTime());

    expect(grantRefreshDelay([
      {
        url: "https://signed.example/image",
        expiresAt: "2026-07-24T10:01:00Z",
        contentType: "image/jpeg",
        accessMode: "direct",
      },
    ])).toBe(55_000);
  });
});
