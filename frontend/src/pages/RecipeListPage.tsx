import { useQuery } from "@tanstack/react-query";

import { listRecipes } from "../api/client";
import { RecipeGrid } from "../components/RecipeGrid";

export function RecipeListPage({ onSelect }: { onSelect: (recipeId: string) => void }) {
  const query = useQuery({ queryKey: ["recipes"], queryFn: listRecipes });

  return (
    <section className="panel">
      <h2>Recipes</h2>
      {query.isLoading ? <p>Loading...</p> : null}
      {query.error ? <p role="alert">{query.error.message}</p> : null}
      {query.data ? <RecipeGrid recipes={query.data.items} onSelect={onSelect} /> : null}
    </section>
  );
}
