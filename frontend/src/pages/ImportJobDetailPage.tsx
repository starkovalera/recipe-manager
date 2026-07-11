import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getImportJob, mediaUrl, retryImportJob } from "../api/client";
import type { ImportJob } from "../api/types";

const ACTIVE_STATUSES = new Set<ImportJob["status"]>(["queued", "running"]);

const STATUS_LABELS: Record<ImportJob["status"], string> = {
  queued: "Queued",
  running: "In progress",
  succeeded: "Completed",
  succeeded_with_flags: "Completed with warning",
  failed: "Failed",
  cancelled: "Cancelled",
};

const ERROR_MESSAGES: Record<string, string> = {
  SECONDARY_RESOURCE_UPLOADING_FAILED: "Some media from the provided link could not be loaded.",
  RESULT_PARSE_FAILED: "The recipe extraction result could not be processed.",
  INVALID_EXTRACTION_RESULT: "The provided sources could not be converted into a valid recipe.",
  NOT_A_RECIPE: "No recipe could be found in the provided sources.",
  EXTRACTOR_UNAVAILABLE: "Recipe extraction is temporarily unavailable.",
  RECIPE_TOO_LONG: "The extracted recipe exceeds the supported size limits.",
};

function formatDate(value?: string | null) {
  return value ? new Date(value).toLocaleString() : "Not available";
}

export function importErrorMessage(code?: string | null) {
  return code ? (ERROR_MESSAGES[code] ?? "Unexpected error.") : "Unexpected error.";
}

export function ImportJobDetailPage({
  jobId,
  onOpenRecipe,
}: {
  jobId: string;
  onOpenRecipe: (recipeId: string) => void;
}) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["import-job", jobId],
    queryFn: () => getImportJob(jobId),
    refetchInterval: (currentQuery) => (ACTIVE_STATUSES.has(currentQuery.state.data?.status as ImportJob["status"]) ? 1000 : false),
  });
  const retryMutation = useMutation({
    mutationFn: () => retryImportJob(jobId),
    onSuccess: (job) => {
      queryClient.setQueryData(["import-job", jobId], job);
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      queryClient.invalidateQueries({ queryKey: ["internal-import-jobs"] });
    },
  });

  if (query.isLoading) return <section className="panel">Loading import...</section>;
  if (query.error) return <section className="panel" role="alert">{query.error.message}</section>;
  const job = query.data;
  if (!job) return null;

  const canRetry = job.status === "failed" && job.attemptCount < job.maxAttempts && !retryMutation.isPending;

  return (
    <section className="panel import-job-detail">
      <div className="section-heading">
        <div>
          <h2>Import details</h2>
          <p className={`import-status import-status--${job.status}`}>{STATUS_LABELS[job.status]}</p>
        </div>
        <div className="button-row">
          {canRetry ? <button type="button" onClick={() => retryMutation.mutate()}>Retry import</button> : null}
          {job.createdRecipeId ? <button type="button" onClick={() => onOpenRecipe(job.createdRecipeId as string)}>Open recipe</button> : null}
        </div>
      </div>

      {job.status === "failed" ? <p className="import-error" role="alert">{importErrorMessage(job.errorMessage)}</p> : null}
      {retryMutation.error ? <p className="import-error" role="alert">{retryMutation.error.message}</p> : null}

      <dl className="debug-grid import-summary">
        <div><dt>Attempts</dt><dd>Attempt {job.attemptCount} of {job.maxAttempts}</dd></div>
        <div><dt>Created</dt><dd>{formatDate(job.createdAt)}</dd></div>
        <div><dt>Started</dt><dd>{formatDate(job.startedAt)}</dd></div>
        <div><dt>Finished</dt><dd>{formatDate(job.finishedAt)}</dd></div>
      </dl>

      <h3>Submitted sources</h3>
      <div className="import-source-list">
        {job.sources.length ? job.sources.map((source, index) => {
          if (source.type === "IMAGE" && source.mediaUrl) {
            const label = source.originalName || `Image ${index + 1}`;
            return <figure key={`${source.type}-${index}`} className="import-source"><img src={mediaUrl(source.mediaUrl)} alt={label} /><figcaption>{label}</figcaption></figure>;
          }
          if (source.type === "URL" && source.url) {
            return <div key={`${source.type}-${index}`} className="import-source"><strong>Link</strong><a href={source.url} target="_blank" rel="noreferrer">{source.url}</a></div>;
          }
          if (source.type === "TEXT" && source.text) {
            return <details key={`${source.type}-${index}`} className="import-source" open><summary>Submitted text</summary><p>{source.text}</p></details>;
          }
          return null;
        }) : <p>No submitted sources.</p>}
      </div>
    </section>
  );
}
