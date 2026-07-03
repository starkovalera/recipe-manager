import { useMutation, useQuery } from "@tanstack/react-query";

import { listInternalRecipeEmbeddings, retryInternalRecipeEmbedding } from "../api/client";
import { queryClient } from "../app/queryClient";

function formatDate(value?: string | null) {
  return value ? new Date(value).toLocaleString() : "-";
}

function shortHash(value?: string | null) {
  return value ? `${value.slice(0, 12)}...` : "-";
}

export function InternalEmbeddingsPage() {
  const query = useQuery({ queryKey: ["internal-embeddings"], queryFn: listInternalRecipeEmbeddings });
  const retryMutation = useMutation({
    mutationFn: retryInternalRecipeEmbedding,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["internal-embeddings"] }),
  });

  if (query.isLoading) return <section className="panel">Loading embeddings...</section>;
  if (query.error) return <section className="panel" role="alert">{query.error.message}</section>;

  return (
    <section className="panel">
      <h2>Recipe embeddings</h2>
      <div className="stack">
        {query.data?.items.length ? (
          query.data.items.map((embedding) => (
            <article key={embedding.recipeId} className="debug-card">
              <header className="debug-card__header">
                <div>
                  <h3>{embedding.recipeTitle ?? embedding.recipeId}</h3>
                  <p>
                    {embedding.status} - user {embedding.ownerId ?? "-"} - recipe {embedding.recipeId}
                  </p>
                </div>
                <div>
                  <span>Updated {formatDate(embedding.updatedAt)}</span>
                  <span>Last attempt {formatDate(embedding.lastAttemptAt)}</span>
                </div>
              </header>
              <div className="actions-row">
                <button type="button" onClick={() => retryMutation.mutate(embedding.recipeId)} disabled={retryMutation.isPending}>
                  Retry
                </button>
              </div>
              <dl className="debug-grid">
                <div>
                  <dt>Model</dt>
                  <dd>{embedding.model}</dd>
                </div>
                <div>
                  <dt>Input hash</dt>
                  <dd title={embedding.inputHash ?? undefined}>{shortHash(embedding.inputHash)}</dd>
                </div>
                <div>
                  <dt>Failed attempts</dt>
                  <dd>{embedding.failedAttempts}</dd>
                </div>
                <div>
                  <dt>Last error</dt>
                  <dd>{embedding.errorMessage ? `${formatDate(embedding.lastErrorAt)} - ${embedding.errorMessage}` : "-"}</dd>
                </div>
              </dl>
              <details className="debug-events">
                <summary>Events ({embedding.events.length})</summary>
                {embedding.events.length ? (
                  <ul>
                    {embedding.events.map((event) => (
                      <li key={event.id}>
                        <strong>{event.eventType}</strong>
                        <span> {event.statusAfter ?? "-"} </span>
                        <span>{formatDate(event.createdAt)}</span>
                        {event.payload ? <pre>{JSON.stringify(event.payload, null, 2)}</pre> : null}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>No embedding events yet.</p>
                )}
              </details>
            </article>
          ))
        ) : (
          <p>No recipe embeddings yet.</p>
        )}
      </div>
    </section>
  );
}
