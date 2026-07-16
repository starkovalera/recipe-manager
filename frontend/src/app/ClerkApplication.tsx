import { SignInButton, SignUp, UserButton, useAuth, useClerk } from "@clerk/react";
import { useEffect, useRef, useState } from "react";

import { ApiError, deleteCurrentAccount, provisionCurrentUser, setApiTokenProvider } from "../api/client";
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
  const { signOut } = useClerk();
  const [deletionRequested, setDeletionRequested] = useState(false);

  if (deletionRequested) return <AccountStateError heading="Account deletion requested" message="Your account is being deleted." />;
  if (!isLoaded) return <main className="auth-shell">Loading account...</main>;
  if (!isSignedIn || !sessionId || !userId) return <SignedOutShell />;
  return (
    <SignedInApplication
      key={`${userId}:${sessionId}`}
      getToken={getToken}
      userId={userId}
      signOut={signOut}
      onDeletionRequested={() => setDeletionRequested(true)}
    />
  );
}

function SignedInApplication({
  getToken,
  userId,
  signOut,
  onDeletionRequested,
}: {
  getToken: () => Promise<string | null>;
  userId: string;
  signOut: () => Promise<unknown>;
  onDeletionRequested: () => void;
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
  async function deleteAccount() {
    await deleteCurrentAccount();
    setApiTokenProvider(null);
    queryClient.clear();
    onDeletionRequested();
    await signOut();
  }

  return (
    <App
      key={userId}
      accountControl={(
        <div className="account-actions">
          <UserButton />
          <AccountDeletionControl onDelete={deleteAccount} />
        </div>
      )}
    />
  );
}

function AccountDeletionControl({ onDelete }: { onDelete: () => Promise<void> }) {
  const [confirming, setConfirming] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function confirmDeletion() {
    setPending(true);
    setError(null);
    try {
      await onDelete();
    } catch (nextError) {
      setError(nextError);
      setPending(false);
    }
  }

  if (!confirming) {
    return <button type="button" className="danger-button" onClick={() => setConfirming(true)}>Delete account</button>;
  }
  return (
    <div className="modal-backdrop" role="presentation">
      <section className="danger-zone account-deletion-dialog" role="dialog" aria-modal="true" aria-labelledby="delete-account-heading">
        <h2 id="delete-account-heading">Delete account?</h2>
        <p>This permanently removes your recipes and account data.</p>
        <div className="button-row">
          <button type="button" disabled={pending} onClick={() => void confirmDeletion()}>Confirm delete account</button>
          <button type="button" disabled={pending} onClick={() => setConfirming(false)}>Cancel</button>
        </div>
        {error ? <p role="alert">Account deletion could not be started.</p> : null}
      </section>
    </div>
  );
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
