import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { UsersPage } from "./UsersPage";

describe("UsersPage", () => {
  afterEach(() => cleanup());

  it("renders backend roles and assigns and revokes them", async () => {
    let roles: string[] = [];
    let status = "ACTIVE";
    const createdAt = "2026-01-01T10:00:00Z";
    const updatedAt = "2026-02-01T10:00:00Z";
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
            availableStatuses: [
              { value: "ACTIVE", label: "Active" },
              { value: "DEACTIVATED", label: "Deactivated" },
              { value: "DELETION_PENDING", label: "Deletion pending" },
            ],
            statistics: [{ role: "DEBUG", userCount: 0 }],
            total: 1,
            limit: 24,
            offset: 0,
            items: [{
              id: "user-1",
              authUserId: "auth-user-1",
              email: "user@example.test",
              roles,
              status,
              createdAt,
              updatedAt,
              deletionRequestedAt: null,
            }],
          }
        : {
            id: "user-1",
            authUserId: "auth-user-1",
            email: "user@example.test",
            roles,
            status,
            createdAt,
            updatedAt,
            deletionRequestedAt: null,
          };
      return { ok: true, status: 200, text: async () => JSON.stringify(payload) };
    });
    vi.stubGlobal("fetch", fetchMock);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={client}>
        <UsersPage />
      </QueryClientProvider>,
    );

    await waitFor(() => expect(screen.getByRole("button", { name: "Assign Debug tools" })).toBeTruthy());
    expect(screen.getByText("user-1")).toBeTruthy();
    expect(screen.getByText("auth-user-1")).toBeTruthy();
    expect(screen.getByText(new Date(createdAt).toLocaleString())).toBeTruthy();
    expect(screen.getByText(new Date(updatedAt).toLocaleString())).toBeTruthy();
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

  it("sends search filters sorting and pagination to the backend", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      text: async () => JSON.stringify({
        availableRoles: [{ value: "DEBUG", label: "Debug tools" }],
        availableStatuses: [
          { value: "ACTIVE", label: "Active" },
          { value: "DEACTIVATED", label: "Deactivated" },
        ],
        statistics: [],
        items: [],
        total: 50,
        limit: 24,
        offset: 0,
      }),
    }));
    vi.stubGlobal("fetch", fetchMock);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={client}>
        <UsersPage />
      </QueryClientProvider>,
    );

    await waitFor(() => expect(screen.getByRole("searchbox", { name: "Search users" })).toBeTruthy());
    fireEvent.change(screen.getByRole("searchbox", { name: "Search users" }), { target: { value: "auth-user" } });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));
    fireEvent.change(screen.getByRole("combobox", { name: "Role" }), { target: { value: "DEBUG" } });
    fireEvent.change(screen.getByRole("combobox", { name: "Status" }), { target: { value: "DEACTIVATED" } });
    fireEvent.change(screen.getByRole("combobox", { name: "Sort by" }), { target: { value: "email" } });
    fireEvent.change(screen.getByRole("combobox", { name: "Sort order" }), { target: { value: "asc" } });

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("q=auth-user"),
      expect.anything(),
    ));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("role=DEBUG"),
      expect.anything(),
    ));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("status=DEACTIVATED"),
      expect.anything(),
    ));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("sortBy=email"),
      expect.anything(),
    ));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("sortOrder=asc"),
      expect.anything(),
    ));

    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("offset=24"),
      expect.anything(),
    ));
  });
});
