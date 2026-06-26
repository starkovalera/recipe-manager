import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { deleteCollection, getCollection } from "../api/client";
import { RecipeGrid } from "../components/RecipeGrid";

export function CollectionDetailPage({
  collectionId,
  onSelectRecipe,
  onDeleted,
}: {
  collectionId: string;
  onSelectRecipe: (recipeId: string) => void;
  onDeleted: () => void;
}) {
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["collection", collectionId], queryFn: () => getCollection(collectionId) });
  const deleteMutation = useMutation({
    mutationFn: () => deleteCollection(collectionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["collections"] });
      onDeleted();
    },
  });

  return (
    <section className="panel">
      <div className="section-heading">
        <h2>{query.data?.name ?? "Collection"}</h2>
        <button className="danger-link" type="button" onClick={() => deleteMutation.mutate()}>
          Delete collection
        </button>
      </div>
      {query.error ? <p role="alert">{query.error.message}</p> : null}
      {query.data?.description ? <p>{query.data.description}</p> : null}
      {query.data ? <RecipeGrid recipes={query.data.recipes} onSelect={onSelectRecipe} /> : null}
    </section>
  );
}
