import { useQuery } from "@tanstack/react-query";

import { listInternalRecipeEmbeddings } from "../api/client";

function formatDate(value?: string | null) {
  return value ? new Date(value).toLocaleString() : "-";
}

function shortHash(value?: string | null) {
  return value ? `${value.slice(0, 12)}...` : "-";
}

export function InternalEmbeddingsPage() {
  const query = useQuery({ queryKey: ["internal-embeddings"], queryFn: listInternalRecipeEmbeddings });

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
            </article>
          ))
        ) : (
          <p>No recipe embeddings yet.</p>
        )}
      </div>
    </section>
  );
}
