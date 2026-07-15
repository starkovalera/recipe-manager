import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RoleManagementPage } from "./RoleManagementPage";

describe("RoleManagementPage", () => {
  afterEach(() => cleanup());

  it("renders backend roles and assigns and revokes them", async () => {
    let roles: string[] = [];
    let status = "ACTIVE";
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = new URL(String(input)).pathname;
      if (init?.method === "PUT") roles = ["DEBUG"];
      if (init?.method === "DELETE") roles = [];
      if (path.endsWith("/status") && init?.method === "PATCH") {
        status = JSON.parse(String(init.body)).status;
      }
      const payload = path === "/internal/access/users"
        ? {
            availableRoles: [{ value: "DEBUG", label: "Debug tools" }],
            statistics: [{ role: "DEBUG", userCount: 0 }],
            items: [{ id: "user-1", email: "user@example.test", roles, status }],
          }
        : { id: "user-1", email: "user@example.test", roles, status };
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
      expect.stringContaining("/internal/access/users/user-1/roles/DEBUG"),
      expect.objectContaining({ method: "PUT" }),
    ));
    await waitFor(() => expect(screen.getByRole("button", { name: "Revoke Debug tools" })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Revoke Debug tools" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/internal/access/users/user-1/roles/DEBUG"),
      expect.objectContaining({ method: "DELETE" }),
    ));

    fireEvent.click(screen.getByRole("button", { name: "Deactivate" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/internal/access/users/user-1/status"),
      expect.objectContaining({ method: "PATCH", body: JSON.stringify({ status: "DEACTIVATED" }) }),
    ));
    await waitFor(() => expect(screen.getByRole("button", { name: "Activate" })).toBeTruthy());
  });
});
