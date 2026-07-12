import { useState } from "react";

import type { CurrentUser } from "../api/types";
import { InternalEmbeddingsPage } from "./InternalEmbeddingsPage";
import { InternalImportJobsPage } from "./InternalImportJobsPage";
import { InternalSearchDebugPage } from "./InternalSearchDebugPage";
import { RoleManagementPage } from "./RoleManagementPage";

type AdminTab = "imports" | "embeddings" | "search" | "roles";

export function AdminPage({ currentUser, onOpenRecipe }: { currentUser: CurrentUser; onOpenRecipe: (recipeId: string) => void }) {
  const [tab, setTab] = useState<AdminTab>("imports");
  return (
    <section className="panel stack">
      <h2>Admin</h2>
      <nav className="button-row" aria-label="Admin">
        <button type="button" onClick={() => setTab("imports")}>Import Jobs</button>
        <button type="button" onClick={() => setTab("embeddings")}>Embeddings</button>
        <button type="button" onClick={() => setTab("search")}>Search Debug</button>
        {currentUser.features.showRoleManagement ? <button type="button" onClick={() => setTab("roles")}>Roles</button> : null}
      </nav>
      {tab === "imports" ? <InternalImportJobsPage onOpenRecipe={onOpenRecipe} /> : null}
      {tab === "embeddings" ? <InternalEmbeddingsPage /> : null}
      {tab === "search" ? <InternalSearchDebugPage onOpenRecipe={onOpenRecipe} /> : null}
      {tab === "roles" && currentUser.features.showRoleManagement ? <RoleManagementPage /> : null}
    </section>
  );
}
