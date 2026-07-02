import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { listRecipes } from "../api/client";
import { PaginationControls } from "../components/PaginationControls";
import { RecipeGrid } from "../components/RecipeGrid";

const PAGE_LIMIT = 24;

export function RecipeListPage({ onSelect }: { onSelect: (recipeId: string) => void }) {
  const [offset, setOffset] = useState(0);
  const query = useQuery({ queryKey: ["recipes", { limit: PAGE_LIMIT, offset }], queryFn: () => listRecipes({ limit: PAGE_LIMIT, offset }) });
  const total = query.data?.total ?? query.data?.items.length ?? 0;
  const limit = query.data?.limit ?? PAGE_LIMIT;

  return (
    <section className="panel">
      <h2>Recipes</h2>
      {query.isLoading ? <p>Loading...</p> : null}
      {query.error ? <p role="alert">{query.error.message}</p> : null}
      {query.data ? <RecipeGrid recipes={query.data.items} onSelect={onSelect} /> : null}
      {query.data ? <PaginationControls total={total} limit={limit} offset={query.data.offset ?? offset} onPage={setOffset} /> : null}
    </section>
  );
}
