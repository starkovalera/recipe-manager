import { QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

import { queryClient } from "./queryClient";
import { CollectionDetailPage } from "../pages/CollectionDetailPage";
import { CollectionsPage } from "../pages/CollectionsPage";
import { ImportPage } from "../pages/ImportPage";
import { RecipeDetailPage } from "../pages/RecipeDetailPage";
import { RecipeListPage } from "../pages/RecipeListPage";

type Page =
  | { name: "recipes" }
  | { name: "import" }
  | { name: "recipe"; recipeId: string }
  | { name: "collections" }
  | { name: "collection"; collectionId: string };

export function App() {
  const [page, setPage] = useState<Page>({ name: "recipes" });
  const activeSection = page.name === "recipe" ? "recipes" : page.name === "collection" ? "collections" : page.name;

  return (
    <QueryClientProvider client={queryClient}>
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
          </nav>
        </header>
        <div className="layout">
          {page.name === "recipes" ? <RecipeListPage onSelect={(recipeId) => setPage({ name: "recipe", recipeId })} /> : null}
          {page.name === "import" ? <ImportPage onImported={(recipeId) => setPage({ name: "recipe", recipeId })} /> : null}
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
        </div>
      </main>
    </QueryClientProvider>
  );
}
