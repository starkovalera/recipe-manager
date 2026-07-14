import { SignInButton, SignUp, UserButton, useAuth } from "@clerk/react";
import { useEffect, useState } from "react";

import { setApiTokenProvider } from "../api/client";
import { App } from "./App";
import { queryClient } from "./queryClient";

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
  const { getToken, isLoaded, isSignedIn, userId } = useAuth();

  if (!isLoaded) return <main className="auth-shell">Loading account...</main>;
  if (!isSignedIn || !userId) return <SignedOutShell />;
  return <SignedInApplication key={userId} getToken={getToken} userId={userId} />;
}

function SignedInApplication({
  getToken,
  userId,
}: {
  getToken: () => Promise<string | null>;
  userId: string;
}) {
  const [tokenProviderReady, setTokenProviderReady] = useState(false);

  useEffect(() => {
    setApiTokenProvider(() => getToken());
    setTokenProviderReady(true);
    return () => {
      setApiTokenProvider(null);
      queryClient.clear();
    };
  }, [getToken]);

  if (!tokenProviderReady) return <main className="auth-shell">Loading account...</main>;
  return <App key={userId} accountControl={<UserButton />} />;
}
