import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import defaultRecipeImage from "../assets/default-recipe.svg";
import {
  addRecipeToCollection,
  deleteRecipe,
  getRecipe,
  listCollections,
  mediaUrl,
  patchRecipe,
  patchRecipeSource,
  patchReviewFlag,
  removeRecipeFromCollection,
} from "../api/client";
import type { RecipeDetail, RecipeImage, RecipeSource, ReviewFlag } from "../api/types";

type CoverChoice = { kind: "DEFAULT" | "IMAGE"; imageId?: string | null };

function joinIngredients(recipe: RecipeDetail): string {
  return recipe.ingredients
    .sort((left, right) => left.position - right.position)
    .map((ingredient) => [ingredient.quantity, ingredient.unit, ingredient.name, ingredient.note].filter(Boolean).join(" "))
    .join("\n");
}

function parseLines(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function numberOrNull(value: string): number | null {
  if (!value.trim()) return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function reviewMessages(flags: ReviewFlag[]): string[] {
  const hasConflicts = flags.some((flag) => flag.details?.hasConflicts === true || flag.reasonCode.includes("CONFLICT"));
  const hasIgnored = flags.some((flag) => flag.details?.hasIgnored === true || flag.reasonCode.includes("IGNORED"));
  const messages: string[] = [];
  if (hasConflicts) messages.push("conflicting information was found in the sources");
  if (hasIgnored) messages.push("some sources were ignored");
  if (messages.length === 0) messages.push("the imported result needs review");
  return messages;
}

function imageUrl(image: RecipeImage | null | undefined): string {
  return image ? mediaUrl(image.mediaUrl) : defaultRecipeImage;
}

function sourceImageForOption(sources: RecipeSource[], imageId: string | null | undefined): RecipeSource | undefined {
  if (!imageId) return undefined;
  return sources.find((source) => source.type === "IMAGE" && source.imageId === imageId);
}

export function RecipeDetailPage({ recipeId, onDeleted }: { recipeId: string; onDeleted: () => void }) {
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["recipe", recipeId], queryFn: () => getRecipe(recipeId) });
  const collectionsQuery = useQuery({ queryKey: ["collections"], queryFn: listCollections });
  const recipe = query.data;

  const [title, setTitle] = useState("");
  const [cookTimeMinutes, setCookTimeMinutes] = useState("");
  const [calories, setCalories] = useState("");
  const [proteinGrams, setProteinGrams] = useState("");
  const [fatGrams, setFatGrams] = useState("");
  const [carbsGrams, setCarbsGrams] = useState("");
  const [tags, setTags] = useState("");
  const [ingredients, setIngredients] = useState("");
  const [instructions, setInstructions] = useState("");
  const [note, setNote] = useState("");
  const [coverChoice, setCoverChoice] = useState<CoverChoice>({ kind: "DEFAULT" });
  const [previewImage, setPreviewImage] = useState<{ label: string; url: string } | null>(null);

  useEffect(() => {
    if (!recipe) return;
    setTitle(recipe.title);
    setCookTimeMinutes(recipe.cookTimeMinutes?.toString() ?? "");
    setCalories(recipe.nutritionEstimate?.calories?.toString() ?? "");
    setProteinGrams(recipe.nutritionEstimate?.proteinGrams?.toString() ?? "");
    setFatGrams(recipe.nutritionEstimate?.fatGrams?.toString() ?? "");
    setCarbsGrams(recipe.nutritionEstimate?.carbsGrams?.toString() ?? "");
    setTags(recipe.tags.join(", "));
    setIngredients(joinIngredients(recipe));
    setInstructions(recipe.instructions.join("\n"));
    setNote(recipe.note ?? "");
    const selectedCover = recipe.coverOptions.find((option) => option.selected);
    setCoverChoice(
      selectedCover?.image
        ? { kind: "IMAGE", imageId: selectedCover.image.id }
        : { kind: "DEFAULT" },
    );
  }, [recipe]);

  const openFlags = useMemo(() => (recipe?.reviewFlags ?? []).filter((flag) => flag.status === "open"), [recipe]);
  const recipeCollectionIds = useMemo(() => new Set(recipe?.collections?.map((collection) => collection.id) ?? []), [recipe]);
  const availableCollections = collectionsQuery.data?.items ?? [];
  const openFlagMessages = useMemo(() => reviewMessages(openFlags), [openFlags]);
  const primaryUrlSource = useMemo(
    () => recipe?.sources.find((source) => source.type === "URL" && !source.parentSourceId) ?? null,
    [recipe],
  );

  const saveMutation = useMutation({
    mutationFn: () =>
      patchRecipe(recipeId, {
        title,
        cookTimeMinutes: numberOrNull(cookTimeMinutes),
        nutritionEstimate: {
          calories: numberOrNull(calories),
          proteinGrams: numberOrNull(proteinGrams),
          fatGrams: numberOrNull(fatGrams),
          carbsGrams: numberOrNull(carbsGrams),
        },
        tags: tags
          .split(",")
          .map((tag) => tag.trim())
          .filter(Boolean),
        ingredients: parseLines(ingredients).map((name) => ({ name })),
        instructions: parseLines(instructions),
        note,
        coverSelection: coverChoice,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recipe", recipeId] });
      queryClient.invalidateQueries({ queryKey: ["recipes"] });
      queryClient.invalidateQueries({ queryKey: ["collections"] });
    },
  });
  const deleteMutation = useMutation({
    mutationFn: () => deleteRecipe(recipeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recipes"] });
      queryClient.invalidateQueries({ queryKey: ["collections"] });
      onDeleted();
    },
  });
  const collectionMutation = useMutation({
    mutationFn: ({ collectionId, selected }: { collectionId: string; selected: boolean }) =>
      selected ? removeRecipeFromCollection(collectionId, recipeId) : addRecipeToCollection(collectionId, recipeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recipe", recipeId] });
      queryClient.invalidateQueries({ queryKey: ["collections"] });
    },
  });
  const resolveFlagMutation = useMutation({
    mutationFn: (flagId: string) => patchReviewFlag(recipeId, flagId, "resolved"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recipe", recipeId] });
      queryClient.invalidateQueries({ queryKey: ["recipes"] });
    },
  });
  const sourceMutation = useMutation({
    mutationFn: ({ sourceId, status }: { sourceId: string; status: "used" | "deleted" }) => patchRecipeSource(recipeId, sourceId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recipe", recipeId] });
      queryClient.invalidateQueries({ queryKey: ["recipes"] });
    },
  });
  const coverMutation = useMutation({
    mutationFn: (selection: CoverChoice) => patchRecipe(recipeId, { coverSelection: selection }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recipe", recipeId] });
      queryClient.invalidateQueries({ queryKey: ["recipes"] });
    },
  });

  return (
    <section className="panel">
      {query.isLoading ? <p>Loading...</p> : null}
      {query.error ? <p role="alert">{query.error.message}</p> : null}
      {recipe ? (
        <div className="stack">
          <div className="recipe-hero">
            <div className="recipe-hero-copy">
              <div className="recipe-meta">
                <span>{recipe.sourceName}</span>
                {recipe.authorName ? <span>{recipe.authorName}</span> : null}
                {recipe.cookTimeMinutes ? <span>{recipe.cookTimeMinutes} min</span> : null}
              </div>
              <h2>{recipe.title}</h2>
            </div>
            <img
              className="hero-cover"
              src={recipe.coverImage ? mediaUrl(recipe.coverImage.mediaUrl) : defaultRecipeImage}
              alt={`${recipe.title} cover`}
            />
          </div>

          {openFlags.length > 0 ? (
            <section className="review-banner" aria-label="Open review flags">
              <div>
                <strong>This recipe requires review</strong>
                <p>This recipe requires review because {openFlagMessages.join(" and ")}.</p>
              </div>
              <button
                type="button"
                onClick={() => openFlags.forEach((flag) => resolveFlagMutation.mutate(flag.id))}
                disabled={resolveFlagMutation.isPending}
              >
                Resolve warning
              </button>
            </section>
          ) : null}

          <div className="two-column">
            <section>
              <h3>Ingredients</h3>
              <ul>{recipe.ingredients.map((ingredient) => <li key={ingredient.id}>{ingredient.name}</li>)}</ul>
            </section>
            <section>
              <h3>Instructions</h3>
              <ol>{recipe.instructions.map((step, index) => <li key={index}>{step}</li>)}</ol>
            </section>
          </div>

          <section className="nutrition-panel">
            <h3>Nutrition estimate</h3>
            <pre>{JSON.stringify(recipe.nutritionEstimate ?? {}, null, 2)}</pre>
          </section>

          <section className="editor-section">
            <h3>Edit recipe</h3>
            <label>
              Title
              <input value={title} onChange={(event) => setTitle(event.target.value)} />
            </label>
            <label>
              Time, min
              <input inputMode="numeric" value={cookTimeMinutes} onChange={(event) => setCookTimeMinutes(event.target.value)} />
            </label>
            <div className="form-grid">
              <label>
                Calories
                <input inputMode="decimal" value={calories} onChange={(event) => setCalories(event.target.value)} />
              </label>
              <label>
                Protein, g
                <input inputMode="decimal" value={proteinGrams} onChange={(event) => setProteinGrams(event.target.value)} />
              </label>
              <label>
                Fat, g
                <input inputMode="decimal" value={fatGrams} onChange={(event) => setFatGrams(event.target.value)} />
              </label>
              <label>
                Carbs, g
                <input inputMode="decimal" value={carbsGrams} onChange={(event) => setCarbsGrams(event.target.value)} />
              </label>
            </div>
            <label>
              Tags
              <input value={tags} onChange={(event) => setTags(event.target.value)} />
            </label>
            <label>
              Ingredients
              <textarea value={ingredients} onChange={(event) => setIngredients(event.target.value)} rows={6} />
            </label>
            <label>
              Instructions
              <textarea value={instructions} onChange={(event) => setInstructions(event.target.value)} rows={6} />
            </label>
            <label>
              Note
              <textarea value={note} onChange={(event) => setNote(event.target.value)} rows={4} />
            </label>

            <button type="button" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
              Save
            </button>
          </section>

          <section className="sources-panel">
            <div className="section-heading">
              <h3>Sources</h3>
            </div>

            {primaryUrlSource ? (
              <div className={`source-url-card ${primaryUrlSource.status === "ignored" ? "is-warning" : ""}`}>
                <div>
                  <strong>Source link</strong>
                  <a href={primaryUrlSource.url ?? "#"} target="_blank" rel="noreferrer">
                    {primaryUrlSource.url}
                  </a>
                  {primaryUrlSource.status === "ignored" ? (
                    <p>This source was ignored when creating the recipe.</p>
                  ) : null}
                </div>
                <div className="source-actions">
                  {primaryUrlSource.status === "ignored" ? (
                    <button
                      type="button"
                      onClick={() => sourceMutation.mutate({ sourceId: primaryUrlSource.id, status: "used" })}
                      disabled={sourceMutation.isPending}
                    >
                      Keep source
                    </button>
                  ) : null}
                  <button
                    type="button"
                    onClick={() => sourceMutation.mutate({ sourceId: primaryUrlSource.id, status: "deleted" })}
                    disabled={sourceMutation.isPending}
                  >
                    Delete source
                  </button>
                </div>
              </div>
            ) : null}

            <div className="source-image-grid">
              {recipe.coverOptions.map((option) => {
                const optionImage = option.image ?? null;
                const optionId = optionImage?.id ?? "DEFAULT";
                const isDefault = option.kind === "DEFAULT";
                const isSelected = option.selected;
                const relatedSource = sourceImageForOption(recipe.sources, optionImage?.id);
                const canSetCover = !isSelected;
                const canDelete = Boolean(relatedSource && !isSelected && !isDefault);
                return (
                  <article className={`source-image-card ${isSelected ? "is-selected" : ""}`} key={optionId}>
                    <button
                      className="source-image-preview"
                      type="button"
                      aria-label={`Open ${option.label}`}
                      onClick={() => setPreviewImage({ label: option.label, url: imageUrl(optionImage) })}
                    >
                      <img src={imageUrl(optionImage)} alt={option.label} />
                    </button>
                    <div className="source-image-meta">
                      <strong>{option.label}</strong>
                      {isSelected ? <span>Current cover</span> : null}
                    </div>
                    <div className="source-image-actions">
                      {canSetCover ? (
                        <button
                          type="button"
                          onClick={() => coverMutation.mutate(optionImage ? { kind: "IMAGE", imageId: optionImage.id } : { kind: "DEFAULT" })}
                          disabled={coverMutation.isPending}
                        >
                          Use {option.label} as cover
                        </button>
                      ) : null}
                      {canDelete && relatedSource ? (
                        <button
                          className="danger-link"
                          type="button"
                          onClick={() => sourceMutation.mutate({ sourceId: relatedSource.id, status: "deleted" })}
                          disabled={sourceMutation.isPending}
                        >
                          Delete image
                        </button>
                      ) : null}
                    </div>
                  </article>
                );
              })}
            </div>
          </section>

          {previewImage ? (
            <div className="image-modal-backdrop" role="presentation" onClick={() => setPreviewImage(null)}>
              <div className="image-modal" role="dialog" aria-label={previewImage.label} onClick={(event) => event.stopPropagation()}>
                <button type="button" onClick={() => setPreviewImage(null)}>Close</button>
                <img src={previewImage.url} alt={previewImage.label} />
              </div>
            </div>
          ) : null}

          <section>
            <h3>Collections</h3>
            {availableCollections.length ? (
              <div className="collection-list">
                {availableCollections.map((collection) => {
                  const selected = recipeCollectionIds.has(collection.id);
                  return (
                    <label className="collection-row" key={collection.id}>
                      <input
                        type="checkbox"
                        checked={selected}
                        onChange={() => collectionMutation.mutate({ collectionId: collection.id, selected })}
                      />
                      {collection.name}
                    </label>
                  );
                })}
              </div>
            ) : (
              <p>No collections yet.</p>
            )}
          </section>

          <section>
            <h3>Debug resources</h3>
            <ul>
              {(recipe.debugSources ?? recipe.sources).map((source) => (
                <li key={source.id}>
                  {source.source}/{source.type}: {source.status}
                  {source.parentSourceId ? " (from URL)" : ""}
                </li>
              ))}
            </ul>
          </section>

          <section className="danger-zone">
            <h3>Delete recipe</h3>
            <button type="button" onClick={() => deleteMutation.mutate()} disabled={deleteMutation.isPending}>
              Delete recipe
            </button>
          </section>
        </div>
      ) : null}
    </section>
  );
}
