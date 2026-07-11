import { QueryClientProvider, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { queryClient } from "./queryClient";
import { listNotifications } from "../api/client";
import { isCurrentUserAdmin } from "../auth/admin";
import { CollectionDetailPage } from "../pages/CollectionDetailPage";
import { CollectionsPage } from "../pages/CollectionsPage";
import { ImportPage } from "../pages/ImportPage";
import { ImportJobDetailPage } from "../pages/ImportJobDetailPage";
import { InternalEmbeddingsPage } from "../pages/InternalEmbeddingsPage";
import { InternalImportJobsPage } from "../pages/InternalImportJobsPage";
import { InternalSearchDebugPage } from "../pages/InternalSearchDebugPage";
import { NotificationsPage } from "../pages/NotificationsPage";
import { RecipeDetailPage } from "../pages/RecipeDetailPage";
import { RecipeListPage } from "../pages/RecipeListPage";
import { TagsPage } from "../pages/TagsPage";

type Page =
  | { name: "recipes" }
  | { name: "import" }
  | { name: "import-job"; jobId: string }
  | { name: "recipe"; recipeId: string }
  | { name: "collections" }
  | { name: "collection"; collectionId: string }
  | { name: "notifications" }
  | { name: "internal-import-jobs" }
  | { name: "internal-embeddings" }
  | { name: "internal-search-debug" }
  | { name: "tags" };

function AppContent() {
  const [page, setPage] = useState<Page>({ name: "recipes" });
  const activeSection = page.name === "recipe" ? "recipes" : page.name === "collection" ? "collections" : page.name === "import-job" ? "notifications" : page.name;
  const notificationsQuery = useQuery({
    queryKey: ["notifications"],
    queryFn: listNotifications,
    refetchInterval: 5000,
  });
  const notifications = notificationsQuery.data?.items ?? [];
  const latestUnreadNotification = notifications.find((notification) => notification.status === "unread");
  const isAdmin = isCurrentUserAdmin();

  return (
    <main className="app-shell">
      <header className="app-header">
        <h1>Recipe Manager</h1>
        <nav className="top-nav" aria-label="Main">
            <button
              type="button"
              className={activeSection === "recipes" ? "is-active" : undefined}
              onClick={() => setPage({ name: "recipes" })}
            >
              Recipes
            </button>
            <button
              type="button"
              className={activeSection === "import" ? "is-active" : undefined}
              onClick={() => setPage({ name: "import" })}
            >
              Import
            </button>
            <button
              type="button"
              className={activeSection === "collections" ? "is-active" : undefined}
              onClick={() => setPage({ name: "collections" })}
            >
              Collections
            </button>
            <button
              type="button"
              className={activeSection === "notifications" ? "is-active" : undefined}
              onClick={() => setPage({ name: "notifications" })}
            >
              Notifications
            </button>
            <button
              type="button"
              className={activeSection === "tags" ? "is-active" : undefined}
              onClick={() => setPage({ name: "tags" })}
            >
              Tags
            </button>
            {isAdmin ? (
              <>
                <button
                  type="button"
                  className={activeSection === "internal-import-jobs" ? "is-active" : undefined}
                  onClick={() => setPage({ name: "internal-import-jobs" })}
                >
                  Import jobs
                </button>
                <button
                  type="button"
                  className={activeSection === "internal-embeddings" ? "is-active" : undefined}
                  onClick={() => setPage({ name: "internal-embeddings" })}
                >
                  Embeddings
                </button>
                <button
                  type="button"
                  className={activeSection === "internal-search-debug" ? "is-active" : undefined}
                  onClick={() => setPage({ name: "internal-search-debug" })}
                >
                  Search Debug
                </button>
              </>
            ) : null}
        </nav>
      </header>
      {latestUnreadNotification ? (
        <div className="notification-toast" role="status">
          <strong>{latestUnreadNotification.title}</strong>
          <span>{latestUnreadNotification.message}</span>
        </div>
      ) : null}
      <div className="layout">
        {page.name === "recipes" ? <RecipeListPage onSelect={(recipeId) => setPage({ name: "recipe", recipeId })} /> : null}
        {page.name === "import" ? <ImportPage /> : null}
        {page.name === "import-job" ? <ImportJobDetailPage jobId={page.jobId} onOpenRecipe={(recipeId) => setPage({ name: "recipe", recipeId })} /> : null}
        {page.name === "recipe" ? <RecipeDetailPage recipeId={page.recipeId} onDeleted={() => setPage({ name: "recipes" })} /> : null}
        {page.name === "collections" ? (
          <CollectionsPage onSelect={(collectionId) => setPage({ name: "collection", collectionId })} />
        ) : null}
        {page.name === "collection" ? (
          <CollectionDetailPage
            collectionId={page.collectionId}
            onSelectRecipe={(recipeId) => setPage({ name: "recipe", recipeId })}
            onDeleted={() => setPage({ name: "collections" })}
          />
        ) : null}
        {page.name === "notifications" ? (
          <NotificationsPage
            notifications={notifications}
            onOpenRecipe={(recipeId) => setPage({ name: "recipe", recipeId })}
            onOpenImport={(jobId) => setPage({ name: "import-job", jobId })}
          />
        ) : null}
        {page.name === "tags" ? <TagsPage /> : null}
        {page.name === "internal-import-jobs" && isAdmin ? <InternalImportJobsPage onOpenRecipe={(recipeId) => setPage({ name: "recipe", recipeId })} /> : null}
        {page.name === "internal-embeddings" && isAdmin ? <InternalEmbeddingsPage /> : null}
        {page.name === "internal-search-debug" && isAdmin ? <InternalSearchDebugPage onOpenRecipe={(recipeId) => setPage({ name: "recipe", recipeId })} /> : null}
      </div>
    </main>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
}
