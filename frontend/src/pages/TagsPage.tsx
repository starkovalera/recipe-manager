import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { createTag, deleteTag, getTagUsage, listTags, patchTag } from "../api/client";
import type { Tag } from "../api/types";

type TagDraft = {
  name: string;
  description: string;
};

function draftFromTag(tag: Tag): TagDraft {
  return { name: tag.name, description: tag.description ?? "" };
}

export function TagsPage() {
  const queryClient = useQueryClient();
  const tagsQuery = useQuery({ queryKey: ["tags"], queryFn: listTags });
  const tags = tagsQuery.data?.items ?? [];
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [drafts, setDrafts] = useState<Record<string, TagDraft>>({});

  useEffect(() => {
    setDrafts((current) => {
      const next = { ...current };
      let changed = false;
      for (const tag of tags) {
        if (!next[tag.id]) {
          next[tag.id] = draftFromTag(tag);
          changed = true;
        }
      }
      return changed ? next : current;
    });
  }, [tags]);

  const invalidateTags = () => {
    queryClient.invalidateQueries({ queryKey: ["tags"] });
  };

  const createMutation = useMutation({
    mutationFn: () => createTag({ name: newName, description: newDescription || null }),
    onSuccess: () => {
      setNewName("");
      setNewDescription("");
      invalidateTags();
    },
  });

  const patchMutation = useMutation({
    mutationFn: (tag: Tag) => {
      const draft = drafts[tag.id] ?? draftFromTag(tag);
      return patchTag(tag.id, { name: draft.name, description: draft.description || null });
    },
    onSuccess: invalidateTags,
  });

  const deleteMutation = useMutation({
    mutationFn: async (tag: Tag) => {
      const usage = await getTagUsage(tag.id);
      if (!window.confirm(`This tag is used by ${usage.recipeCount} recipes.`)) return null;
      return deleteTag(tag.id);
    },
    onSuccess: invalidateTags,
  });

  return (
    <section className="panel">
      <h2>Tags ({tags.length})</h2>
      <div className="tag-form-card">
        <input
          aria-label="New tag name"
          placeholder="Name"
          value={newName}
          onChange={(event) => setNewName(event.target.value)}
        />
        <input
          aria-label="New tag description"
          placeholder="Description"
          value={newDescription}
          onChange={(event) => setNewDescription(event.target.value)}
        />
        <button
          type="button"
          className="primary-button"
          onClick={() => createMutation.mutate()}
          disabled={!newName.trim() || createMutation.isPending}
        >
          Create tag
        </button>
      </div>

      <div className="stack">
        {tagsQuery.isLoading ? <p>Loading...</p> : null}
        {tags.map((tag) => {
          const draft = drafts[tag.id] ?? draftFromTag(tag);
          return (
            <article key={tag.id} className="tag-card">
              <input
                aria-label={`Name for ${tag.name}`}
                placeholder="Name"
                value={draft.name}
                onChange={(event) => setDrafts((current) => ({ ...current, [tag.id]: { ...draft, name: event.target.value } }))}
              />
              <input
                aria-label={`Description for ${tag.name}`}
                placeholder="Description"
                value={draft.description}
                onChange={(event) => setDrafts((current) => ({ ...current, [tag.id]: { ...draft, description: event.target.value } }))}
              />
              <button
                type="button"
                className="primary-button"
                onClick={() => patchMutation.mutate(tag)}
                disabled={patchMutation.isPending || !draft.name.trim()}
              >
                Save
              </button>
              <button type="button" className="danger-button" onClick={() => deleteMutation.mutate(tag)} disabled={deleteMutation.isPending}>
                Delete
              </button>
            </article>
          );
        })}
        {!tagsQuery.isLoading && tags.length === 0 ? <p>No tags yet.</p> : null}
      </div>
    </section>
  );
}
