import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { InvitationsPage } from "./InvitationsPage";

describe("InvitationsPage", () => {
  afterEach(() => cleanup());

  it("lists, creates, and revokes invitations through the backend", async () => {
    let invitations = [
      {
        id: "invitation-1",
        email: "first@example.test",
        status: "PENDING",
        authProvider: "CLERK",
        createdAt: "2026-07-15T10:00:00Z",
      },
    ];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = new URL(String(input)).pathname;
      if (path === "/internal/invitations" && init?.method === "POST") {
        const invitation = {
          id: "invitation-2",
          email: JSON.parse(String(init.body)).email,
          status: "PENDING",
          authProvider: "CLERK",
          createdAt: "2026-07-15T11:00:00Z",
        };
        invitations = [invitation, ...invitations];
        return { ok: true, status: 201, text: async () => JSON.stringify(invitation) };
      }
      if (path.endsWith("/revoke")) {
        invitations = invitations.map((item) => item.id === "invitation-1" ? { ...item, status: "REVOKED" } : item);
        return { ok: true, status: 200, text: async () => JSON.stringify(invitations.find((item) => item.id === "invitation-1")) };
      }
      return { ok: true, status: 200, text: async () => JSON.stringify({ items: invitations }) };
    });
    vi.stubGlobal("fetch", fetchMock);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={client}>
        <InvitationsPage />
      </QueryClientProvider>,
    );

    await screen.findByText("first@example.test");
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "new@example.test" } });
    fireEvent.click(screen.getByRole("button", { name: "Send invitation" }));
    await screen.findByText("new@example.test");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/internal/invitations"),
      expect.objectContaining({ method: "POST", body: JSON.stringify({ email: "new@example.test" }) }),
    );

    fireEvent.click(screen.getByRole("button", { name: "Revoke first@example.test" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/internal/invitations/invitation-1/revoke"),
      expect.objectContaining({ method: "POST" }),
    ));
    await screen.findByText("REVOKED");
  });
});
