import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RoleManagementPage } from "./RoleManagementPage";

describe("RoleManagementPage", () => {
  afterEach(() => cleanup());

  it("renders backend roles and assigns and revokes them", async () => {
    let roles: string[] = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = new URL(String(input)).pathname;
      if (init?.method === "PUT") roles = ["debug"];
      if (init?.method === "DELETE") roles = [];
      const payload = path === "/internal/access/users"
        ? {
            availableRoles: [{ value: "debug", label: "Debug tools" }],
            statistics: [{ role: "debug", userCount: 0 }],
            items: [{ id: "user-1", email: "user@example.test", roles }],
          }
        : { id: "user-1", email: "user@example.test", roles };
      return { ok: true, status: 200, text: async () => JSON.stringify(payload) };
    });
    vi.stubGlobal("fetch", fetchMock);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={client}>
        <RoleManagementPage />
      </QueryClientProvider>,
    );

    await waitFor(() => expect(screen.getByRole("button", { name: "Assign Debug tools" })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Assign Debug tools" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/internal/access/users/user-1/roles/debug"),
      expect.objectContaining({ method: "PUT" }),
    ));
    await waitFor(() => expect(screen.getByRole("button", { name: "Revoke Debug tools" })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Revoke Debug tools" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/internal/access/users/user-1/roles/debug"),
      expect.objectContaining({ method: "DELETE" }),
    ));
  });
});
