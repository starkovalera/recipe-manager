import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useRef, useState } from "react";

import { createImport } from "../api/client";

function createClientImportId() {
  return `import_${Date.now()}_${Math.random().toString(36).slice(2)}`;
}

export function ImportPage() {
  const queryClient = useQueryClient();
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const mutation = useMutation({
    mutationFn: createImport,
    onSuccess: () => {
      setText("");
      setUrl("");
      setFiles([]);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate({ clientImportId: createClientImportId(), text, url, files });
  }

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
            ref={fileInputRef}
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
    </section>
  );
}
