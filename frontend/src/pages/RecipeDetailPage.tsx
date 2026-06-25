import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { getRecipe, patchRecipe } from "../api/client";

export function RecipeDetailPage({ recipeId }: { recipeId: string | null }) {
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["recipe", recipeId], queryFn: () => getRecipe(recipeId as string), enabled: recipeId != null });
  const [note, setNote] = useState("");
  const mutation = useMutation({
    mutationFn: () => patchRecipe(recipeId as string, { note }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recipe", recipeId] });
      queryClient.invalidateQueries({ queryKey: ["recipes"] });
    },
  });

  if (!recipeId) return null;
  const recipe = query.data;

  return (
    <section className="panel">
      <h2>{recipe?.title ?? "Recipe"}</h2>
      {query.isLoading ? <p>Loading...</p> : null}
      {query.error ? <p role="alert">{query.error.message}</p> : null}
      {recipe ? (
        <div className="stack">
          <h3>Ingredients</h3>
          <ul>{recipe.ingredients.map((ingredient) => <li key={ingredient.id}>{ingredient.name}</li>)}</ul>
          <h3>Instructions</h3>
          <ol>{recipe.instructions.map((step, index) => <li key={index}>{step}</li>)}</ol>
          <label>
            Note
            <textarea value={note || recipe.note || ""} onChange={(event) => setNote(event.target.value)} rows={4} />
          </label>
          <button type="button" onClick={() => mutation.mutate()}>
            Save note
          </button>
          <h3>Sources</h3>
          <ul>{recipe.sources.map((source) => <li key={source.id}>{source.type}: {source.status}</li>)}</ul>
          <h3>Warnings</h3>
          <ul>{recipe.reviewFlags.map((flag) => <li key={flag.id}>{flag.reasonCode}: {flag.status}</li>)}</ul>
        </div>
      ) : null}
    </section>
  );
}
