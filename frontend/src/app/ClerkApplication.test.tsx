import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  lifecycle: [] as string[],
  setApiTokenProvider: vi.fn((provider: unknown) => {
    mocks.lifecycle.push(provider ? "token-provider" : "token-provider-cleared");
  }),
}));

vi.mock("@clerk/react", () => ({
  SignInButton: ({ children }: { children: React.ReactNode }) => children,
  SignUp: () => null,
  UserButton: () => null,
  useAuth: () => ({
    getToken: vi.fn().mockResolvedValue("token"),
    isLoaded: true,
    isSignedIn: true,
    userId: "auth-user-1",
  }),
}));

vi.mock("../api/client", () => ({
  setApiTokenProvider: mocks.setApiTokenProvider,
}));

vi.mock("./App", () => ({
  App: () => {
    mocks.lifecycle.push("app-rendered");
    return <div>Application ready</div>;
  },
}));

vi.mock("./queryClient", () => ({
  queryClient: { clear: vi.fn() },
}));

import { ClerkApplication } from "./ClerkApplication";

describe("ClerkApplication", () => {
  beforeEach(() => {
    mocks.lifecycle.length = 0;
    mocks.setApiTokenProvider.mockClear();
  });

  it("registers the token provider before rendering the signed-in application", async () => {
    render(<ClerkApplication />);

    await screen.findByText("Application ready");
    await waitFor(() => expect(mocks.setApiTokenProvider).toHaveBeenCalled());

    expect(mocks.lifecycle.indexOf("token-provider")).toBeLessThan(mocks.lifecycle.indexOf("app-rendered"));
  });
});
