import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { listInternalImportJobs, retryInternalImportJob } from "../api/client";

const SUCCESS_STATUSES = new Set(["succeeded", "succeeded_with_flags"]);

function formatDate(value?: string | null) {
  return value ? new Date(value).toLocaleString() : "-";
}

export function InternalImportJobsPage({ onOpenRecipe }: { onOpenRecipe: (recipeId: string) => void }) {
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["internal-import-jobs"], queryFn: listInternalImportJobs });
  const retryMutation = useMutation({
    mutationFn: retryInternalImportJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["internal-import-jobs"] });
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  if (query.isLoading) return <section className="panel">Loading import jobs...</section>;
  if (query.error) return <section className="panel" role="alert">{query.error.message}</section>;

  return (
    <section className="panel">
      <h2>Import jobs / Job events</h2>
      <div className="stack">
        {query.data?.items.length ? (
          query.data.items.map((job) => (
            <article key={job.id} className="debug-card">
              <header className="debug-card__header">
                <div>
                  <h3>{job.id}</h3>
                  <p>
                    {job.status} - user {job.ownerId} - client {job.clientId}
                  </p>
                </div>
                <div>
                  <span>Started {formatDate(job.startedAt)}</span>
                  <span>Finished {formatDate(job.finishedAt)}</span>
                </div>
              </header>
              <dl className="debug-grid">
                <div>
                  <dt>Client import id</dt>
                  <dd>{job.clientImportId ?? "-"}</dd>
                </div>
                <div>
                  <dt>Recipe</dt>
                  <dd>{job.createdRecipeId ?? (SUCCESS_STATUSES.has(job.status) ? "Recipe not found. It may have been deleted." : "-")}</dd>
                </div>
                <div>
                  <dt>Error</dt>
                  <dd>{job.errorCode ? `${job.errorCode}: ${job.errorMessage ?? ""}` : "-"}</dd>
                </div>
                <div>
                  <dt>Attempts</dt>
                  <dd>Attempt {job.attemptCount} of {job.maxAttempts}</dd>
                </div>
              </dl>
              <div className="button-row">
                {job.createdRecipeId ? <button type="button" onClick={() => onOpenRecipe(job.createdRecipeId as string)}>Open recipe</button> : null}
                {job.status === "failed" && job.attemptCount < job.maxAttempts ? (
                  <button type="button" onClick={() => retryMutation.mutate(job.id)} disabled={retryMutation.isPending}>Retry import</button>
                ) : null}
              </div>
              <h4>Status history</h4>
              <ul>
                {job.statusHistory.map((entry, index) => (
                  <li key={`${entry.status}-${index}`}>
                    {entry.status} - {formatDate(entry.changedAt)}
                  </li>
                ))}
              </ul>
              <h4>Sources</h4>
              <ul>
                {job.sources.map((source) => (
                  <li key={source.id}>
                    {source.position}. {source.type}: {source.status} {source.url ?? source.originalName ?? ""}
                  </li>
                ))}
              </ul>
              <h4>Events</h4>
              <div className="stack">
                {[...job.events]
                  .sort((left, right) => {
                    const leftTimestamp = left.createdAt ? new Date(left.createdAt).getTime() : 0;
                    const rightTimestamp = right.createdAt ? new Date(right.createdAt).getTime() : 0;
                    return rightTimestamp - leftTimestamp;
                  })
                  .map((event) => (
                  <details key={event.id} className="debug-event">
                    <summary>{event.eventType} - {formatDate(event.createdAt)}</summary>
                    <pre>{JSON.stringify(event.payload ?? {}, null, 2)}</pre>
                  </details>
                  ))}
              </div>
            </article>
          ))
        ) : (
          <p>No import jobs yet.</p>
        )}
      </div>
    </section>
  );
}
