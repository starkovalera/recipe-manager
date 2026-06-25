import { QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

import { queryClient } from "./queryClient";
import { ImportPage } from "../pages/ImportPage";
import { RecipeDetailPage } from "../pages/RecipeDetailPage";
import { RecipeListPage } from "../pages/RecipeListPage";

export function App() {
  const [selectedRecipeId, setSelectedRecipeId] = useState<string | null>(null);

  return (
    <QueryClientProvider client={queryClient}>
      <main className="app-shell">
        <header>
          <h1>Recipe Manager</h1>
        </header>
        <div className="layout">
          <ImportPage />
          <RecipeListPage onSelect={setSelectedRecipeId} />
          <RecipeDetailPage recipeId={selectedRecipeId} />
        </div>
      </main>
    </QueryClientProvider>
  );
}
