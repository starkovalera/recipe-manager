import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { StrictMode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { CurrentUser } from "../api/types";

const currentUser: CurrentUser = {
  id: "internal-user-1",
  email: "user@example.test",
  features: { showAdminPages: false, showRoleManagement: false, showRecipeDebug: false },
};

const mocks = vi.hoisted(() => ({
  lifecycle: [] as string[],
  provisionCurrentUser: vi.fn(),
  getToken: vi.fn().mockResolvedValue("token"),
  sessionId: "session-1",
  userId: "auth-user-1",
  setApiTokenProvider: vi.fn((provider: unknown) => {
    mocks.lifecycle.push(provider ? "token-provider" : "token-provider-cleared");
  }),
  queryClient: {
    clear: vi.fn(() => mocks.lifecycle.push("query-cache-cleared")),
    setQueryData: vi.fn(() => mocks.lifecycle.push("current-user-cached")),
  },
}));

vi.mock("@clerk/react", () => ({
  SignInButton: ({ children }: { children: React.ReactNode }) => children,
  SignUp: () => null,
  UserButton: () => null,
  useAuth: () => ({
    getToken: mocks.getToken,
    isLoaded: true,
    isSignedIn: true,
    sessionId: mocks.sessionId,
    userId: mocks.userId,
  }),
}));

vi.mock("../api/client", () => {
  class ApiError extends Error {
    constructor(
      public errorCode: string,
      message: string,
      public status: number,
    ) {
      super(message);
    }
  }

  return {
    ApiError,
    provisionCurrentUser: mocks.provisionCurrentUser,
    setApiTokenProvider: mocks.setApiTokenProvider,
  };
});

vi.mock("./App", () => ({
  App: () => {
    mocks.lifecycle.push("app-rendered");
    return <div>Application ready</div>;
  },
}));

vi.mock("./queryClient", () => ({ queryClient: mocks.queryClient }));

import { ApiError } from "../api/client";
import { ClerkApplication } from "./ClerkApplication";

describe("ClerkApplication", () => {
  beforeEach(() => {
    mocks.lifecycle.length = 0;
    mocks.provisionCurrentUser.mockReset().mockResolvedValue(currentUser);
    mocks.getToken.mockClear();
    mocks.sessionId = "session-1";
    mocks.userId = "auth-user-1";
    mocks.setApiTokenProvider.mockClear();
    mocks.queryClient.clear.mockClear();
    mocks.queryClient.setQueryData.mockClear();
  });

  afterEach(() => cleanup());

  it("provisions and seeds the current-user cache before rendering the application", async () => {
    mocks.provisionCurrentUser.mockImplementation(async () => {
      mocks.lifecycle.push("user-provisioned");
      return currentUser;
    });

    render(<ClerkApplication />);

    await screen.findByText("Application ready");

    expect(mocks.queryClient.setQueryData).toHaveBeenCalledWith(["current-user"], currentUser);
    expect(mocks.lifecycle.indexOf("token-provider")).toBeLessThan(mocks.lifecycle.indexOf("user-provisioned"));
    expect(mocks.lifecycle.indexOf("user-provisioned")).toBeLessThan(mocks.lifecycle.indexOf("current-user-cached"));
    expect(mocks.lifecycle.indexOf("current-user-cached")).toBeLessThan(mocks.lifecycle.indexOf("app-rendered"));
  });

  it("does not render the application while provisioning is pending", async () => {
    let resolveProvisioning: (user: CurrentUser) => void = () => undefined;
    mocks.provisionCurrentUser.mockReturnValue(
      new Promise<CurrentUser>((resolve) => {
        resolveProvisioning = resolve;
      }),
    );

    render(<ClerkApplication />);

    expect(await screen.findByText("Setting up account...")).toBeTruthy();
    expect(screen.queryByText("Application ready")).toBeNull();

    await act(async () => {
      resolveProvisioning(currentUser);
    });
    await screen.findByText("Application ready");
  });

  it("does not duplicate provisioning during Strict Mode effect replay", async () => {
    render(
      <StrictMode>
        <ClerkApplication />
      </StrictMode>,
    );

    await screen.findByText("Application ready");

    expect(mocks.provisionCurrentUser).toHaveBeenCalledTimes(1);
  });

  it.each([
    ["ACCOUNT_DEACTIVATED", "Account deactivated"],
    ["ACCOUNT_DELETION_PENDING", "Account deletion in progress"],
    ["EMAIL_ALREADY_LINKED", "Account identity conflict"],
  ])("shows %s without entering the application", async (errorCode, heading) => {
    mocks.provisionCurrentUser.mockRejectedValue(new ApiError(errorCode, "Account unavailable.", 403));

    render(<ClerkApplication />);

    expect(await screen.findByRole("heading", { name: heading })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Retry" })).toBeNull();
    expect(screen.queryByText("Application ready")).toBeNull();
  });

  it("retries provisioning only after an explicit user action", async () => {
    mocks.provisionCurrentUser
      .mockRejectedValueOnce(new ApiError("AUTH_USER_LOOKUP_FAILED", "Unable to resolve the authenticated user.", 502))
      .mockResolvedValueOnce(currentUser);

    render(<ClerkApplication />);

    expect(await screen.findByRole("heading", { name: "Account setup unavailable" })).toBeTruthy();
    expect(mocks.provisionCurrentUser).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    await screen.findByText("Application ready");
    expect(mocks.provisionCurrentUser).toHaveBeenCalledTimes(2);
  });

  it("clears authentication and query state when the signed-in application unmounts", async () => {
    const view = render(<ClerkApplication />);
    await screen.findByText("Application ready");

    view.unmount();

    await waitFor(() => expect(mocks.setApiTokenProvider).toHaveBeenLastCalledWith(null));
    expect(mocks.queryClient.clear).toHaveBeenCalled();
  });

  it("clears cached state and provisions again when the Clerk identity changes", async () => {
    const view = render(<ClerkApplication />);
    await screen.findByText("Application ready");

    mocks.userId = "auth-user-2";
    view.rerender(<ClerkApplication />);

    await waitFor(() => expect(mocks.provisionCurrentUser).toHaveBeenCalledTimes(2));
    expect(mocks.setApiTokenProvider).toHaveBeenCalledWith(null);
    expect(mocks.queryClient.clear).toHaveBeenCalled();
  });

  it("clears cached state and provisions again when the Clerk session changes", async () => {
    const view = render(<ClerkApplication />);
    await screen.findByText("Application ready");

    mocks.sessionId = "session-2";
    view.rerender(<ClerkApplication />);

    await waitFor(() => expect(mocks.provisionCurrentUser).toHaveBeenCalledTimes(2));
    expect(mocks.setApiTokenProvider).toHaveBeenCalledWith(null);
    expect(mocks.queryClient.clear).toHaveBeenCalled();
  });
});
