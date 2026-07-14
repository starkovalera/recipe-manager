import { ClerkProvider } from "@clerk/react";
import React from "react";
import ReactDOM from "react-dom/client";

import { ClerkApplication } from "./app/ClerkApplication";
import "./styles/app.css";

const publishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;
if (!publishableKey && import.meta.env.MODE !== "test") {
  throw new Error("VITE_CLERK_PUBLISHABLE_KEY is required.");
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ClerkProvider>
      <ClerkApplication />
    </ClerkProvider>
  </React.StrictMode>
);
