import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";

import { createCollection, deleteCollection, listCollections } from "../api/client";
import { PaginationControls } from "../components/PaginationControls";

const PAGE_LIMIT = 24;

export function CollectionsPage({ onSelect }: { onSelect: (collectionId: string) => void }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [offset, setOffset] = useState(0);
  const query = useQuery({
    queryKey: ["collections", { limit: PAGE_LIMIT, offset }],
    queryFn: () => listCollections({ limit: PAGE_LIMIT, offset }),
  });
  const total = query.data?.total ?? query.data?.items.length ?? 0;
  const limit = query.data?.limit ?? PAGE_LIMIT;
  const createMutation = useMutation({
    mutationFn: () => createCollection({ name, description }),
    onSuccess: (collection) => {
      setName("");
      setDescription("");
      queryClient.invalidateQueries({ queryKey: ["collections"] });
      onSelect(collection.id);
    },
  });
  const deleteMutation = useMutation({
    mutationFn: deleteCollection,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["collections"] }),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (name.trim()) {
      createMutation.mutate();
    }
  }

  return (
    <section className="panel">
      <h2>Collections</h2>
      <form className="inline-form" onSubmit={submit}>
        <label>
          Name
          <input value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <label>
          Description
          <input value={description} onChange={(event) => setDescription(event.target.value)} />
        </label>
        <button type="submit" disabled={createMutation.isPending}>
          Create collection
        </button>
      </form>
      {query.error ? <p role="alert">{query.error.message}</p> : null}
      <div className="collection-list">
        {query.data?.items.map((collection) => (
          <div className="collection-row" key={collection.id}>
            <button type="button" onClick={() => onSelect(collection.id)}>
              {collection.name} ({collection.recipeCount})
            </button>
            <button className="danger-link" type="button" onClick={() => deleteMutation.mutate(collection.id)}>
              Delete
            </button>
          </div>
        ))}
      </div>
      {query.data ? <PaginationControls total={total} limit={limit} offset={query.data.offset ?? offset} onPage={setOffset} /> : null}
    </section>
  );
}
