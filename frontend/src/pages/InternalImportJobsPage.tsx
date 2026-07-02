import { useQuery } from "@tanstack/react-query";

import { listInternalImportJobs } from "../api/client";

function formatDate(value?: string | null) {
  return value ? new Date(value).toLocaleString() : "-";
}

export function InternalImportJobsPage() {
  const query = useQuery({ queryKey: ["internal-import-jobs"], queryFn: listInternalImportJobs });

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
                  <dd>{job.createdRecipeId ?? "-"}</dd>
                </div>
                <div>
                  <dt>Error</dt>
                  <dd>{job.errorCode ? `${job.errorCode}: ${job.errorMessage ?? ""}` : "-"}</dd>
                </div>
              </dl>
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
              <ul>
                {job.events.map((event) => (
                  <li key={event.id}>
                    {event.eventType} - {formatDate(event.createdAt)}
                  </li>
                ))}
              </ul>
            </article>
          ))
        ) : (
          <p>No import jobs yet.</p>
        )}
      </div>
    </section>
  );
}
