import { useQuery } from "@tanstack/react-query";

import { listRecipes } from "../api/client";

export function RecipeListPage({ onSelect }: { onSelect: (recipeId: string) => void }) {
  const query = useQuery({ queryKey: ["recipes"], queryFn: listRecipes });

  return (
    <section className="panel">
      <h2>Recipes</h2>
      {query.isLoading ? <p>Loading...</p> : null}
      {query.error ? <p role="alert">{query.error.message}</p> : null}
      <ul>
        {query.data?.items.map((recipe) => (
          <li key={recipe.id}>
            <button type="button" onClick={() => onSelect(recipe.id)}>
              {recipe.title}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
