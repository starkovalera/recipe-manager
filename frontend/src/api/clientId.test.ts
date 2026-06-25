import { describe, expect, it, beforeEach } from "vitest";

import { getClientId } from "./clientId";

describe("getClientId", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("persists a stable generated client id", () => {
    const first = getClientId();
    const second = getClientId();

    expect(first).toMatch(/^local_/);
    expect(second).toBe(first);
    expect(localStorage.getItem("recipe-manager-client-id")).toBe(first);
  });
});
