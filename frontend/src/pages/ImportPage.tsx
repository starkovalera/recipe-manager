import { useMutation, useQuery } from "@tanstack/react-query";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { createImport, getImportJob } from "../api/client";

export function ImportPage({ onImported }: { onImported?: (recipeId: string) => void }) {
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const reportedRecipeId = useRef<string | null>(null);
  const clientImportId = useMemo(() => `import_${Date.now()}_${Math.random().toString(36).slice(2)}`, [jobId]);

  const mutation = useMutation({
    mutationFn: () => createImport({ clientImportId, text, url, files }),
    onSuccess: (job) => setJobId(job.jobId),
  });
  const jobQuery = useQuery({
    queryKey: ["import-job", jobId],
    queryFn: () => getImportJob(jobId as string),
    enabled: jobId != null,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "succeeded" || status === "failed" ? false : 1000;
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate();
  }

  const job = jobQuery.data ?? mutation.data;

  useEffect(() => {
    if (job?.status === "succeeded" && job.createdRecipeId && reportedRecipeId.current !== job.createdRecipeId) {
      reportedRecipeId.current = job.createdRecipeId;
      onImported?.(job.createdRecipeId);
    }
  }, [job?.createdRecipeId, job?.status, onImported]);

  return (
    <section className="panel">
      <h2>Import</h2>
      <form onSubmit={submit} className="stack">
        <label>
          URL
          <input value={url} onChange={(event) => setUrl(event.target.value)} />
        </label>
        <label>
          Text
          <textarea value={text} onChange={(event) => setText(event.target.value)} rows={5} />
        </label>
        <label>
          Images
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
          />
        </label>
        <button type="submit" disabled={mutation.isPending}>
          Import recipe
        </button>
      </form>
      {mutation.error ? <p role="alert">{mutation.error.message}</p> : null}
      {job ? (
        <div className="status-card">
          <span>Status</span>
          <strong>{job.status}</strong>
          {job.status === "succeeded" && job.createdRecipeId ? <small>Created recipe: {job.createdRecipeId}</small> : null}
          {job.status === "failed" ? <small role="alert">{job.errorMessage ?? job.errorCode}</small> : null}
        </div>
      ) : null}
    </section>
  );
}
