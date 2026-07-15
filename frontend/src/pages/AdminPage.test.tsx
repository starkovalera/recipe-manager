import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AdminPage } from "./AdminPage";
import type { CurrentUser } from "../api/types";

function renderPage(showRoleManagement: boolean) {
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, status: 200, text: async () => JSON.stringify({ items: [] }) })));
  const user: CurrentUser = {
    id: "user-1",
    email: "user@example.test",
    features: { showAdminPages: true, showRoleManagement, showRecipeDebug: false },
  };
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <AdminPage currentUser={user} onOpenRecipe={() => undefined} />
    </QueryClientProvider>,
  );
}

describe("AdminPage", () => {
  afterEach(() => cleanup());

  it("hides role management without its capability", () => {
    renderPage(false);
    expect(screen.queryByRole("button", { name: "Roles" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Invitations" })).toBeNull();
  });

  it("shows role management with its capability", () => {
    renderPage(true);
    expect(screen.getByRole("button", { name: "Roles" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Invitations" })).toBeTruthy();
  });
});
