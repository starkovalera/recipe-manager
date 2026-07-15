import { SignInButton, SignUp, UserButton, useAuth } from "@clerk/react";
import { useEffect, useRef, useState } from "react";

import { ApiError, provisionCurrentUser, setApiTokenProvider } from "../api/client";
import type { CurrentUser } from "../api/types";
import { App } from "./App";
import { queryClient } from "./queryClient";

type ProvisioningState =
  | { status: "pending" }
  | { status: "ready" }
  | { status: "error"; error: unknown };

function SignedOutShell() {
  if (window.location.pathname === "/sign-up") {
    return (
      <main className="auth-shell">
        <SignUp routing="path" path="/sign-up" signInUrl="/" />
      </main>
    );
  }
  return (
    <main className="auth-shell">
      <h1>Recipe Manager</h1>
      <SignInButton mode="modal">
        <button type="button">Sign in</button>
      </SignInButton>
      <a href={`/sign-up${window.location.search}`}>Accept invitation</a>
    </main>
  );
}

export function ClerkApplication() {
  const { getToken, isLoaded, isSignedIn, sessionId, userId } = useAuth();

  if (!isLoaded) return <main className="auth-shell">Loading account...</main>;
  if (!isSignedIn || !sessionId || !userId) return <SignedOutShell />;
  return <SignedInApplication key={`${userId}:${sessionId}`} getToken={getToken} userId={userId} />;
}

function SignedInApplication({
  getToken,
  userId,
}: {
  getToken: () => Promise<string | null>;
  userId: string;
}) {
  const [attempt, setAttempt] = useState(0);
  const [provisioning, setProvisioning] = useState<ProvisioningState>({ status: "pending" });
  const provisioningPromise = useRef<Promise<CurrentUser> | null>(null);

  useEffect(() => {
    let active = true;
    setApiTokenProvider(() => getToken());
    setProvisioning({ status: "pending" });
    const request = provisioningPromise.current ?? provisionCurrentUser();
    provisioningPromise.current = request;
    void request.then(
      (currentUser) => {
        if (!active) return;
        queryClient.setQueryData(["current-user"], currentUser);
        setProvisioning({ status: "ready" });
      },
      (error: unknown) => {
        if (!active) return;
        setProvisioning({ status: "error", error });
      },
    );
    return () => {
      active = false;
      setApiTokenProvider(null);
      queryClient.clear();
    };
  }, [attempt, getToken]);

  function retryProvisioning() {
    provisioningPromise.current = null;
    setAttempt((current) => current + 1);
  }

  if (provisioning.status === "pending") return <main className="auth-shell">Setting up account...</main>;
  if (provisioning.status === "error") {
    return <ProvisioningError error={provisioning.error} onRetry={retryProvisioning} />;
  }
  return <App key={userId} accountControl={<UserButton />} />;
}

function ProvisioningError({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const errorCode = error instanceof ApiError ? error.errorCode : null;
  if (errorCode === "ACCOUNT_DEACTIVATED") {
    return <AccountStateError heading="Account deactivated" message="This account is deactivated." />;
  }
  if (errorCode === "ACCOUNT_DELETION_PENDING") {
    return <AccountStateError heading="Account deletion in progress" message="Account deletion is in progress." />;
  }
  if (errorCode === "EMAIL_ALREADY_LINKED") {
    return (
      <AccountStateError
        heading="Account identity conflict"
        message="This email is already linked to another account."
      />
    );
  }
  return (
    <main className="auth-shell">
      <h1>Account setup unavailable</h1>
      <p>Account setup could not be completed.</p>
      <button type="button" onClick={onRetry}>
        Retry
      </button>
    </main>
  );
}

function AccountStateError({ heading, message }: { heading: string; message: string }) {
  return (
    <main className="auth-shell">
      <h1>{heading}</h1>
      <p>{message}</p>
    </main>
  );
}
