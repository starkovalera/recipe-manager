import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import defaultRecipeImage from "../assets/default-recipe.svg";
import {
  ApiError,
  addRecipeToCollection,
  deleteRecipe,
  getRecipe,
  listCollections,
  listTags,
  mediaUrl,
  patchRecipe,
  patchRecipeResource,
  patchReviewFlag,
  removeRecipeFromCollection,
} from "../api/client";
import type { RecipeDetail, RecipeImage, RecipeResource, ReviewFlag, Tag } from "../api/types";

type CoverChoice = { kind: "DEFAULT" | "IMAGE"; imageId?: string | null };
type EditableIngredient = { id?: string; name: string; quantity: string; unit: string; note: string };

const SOURCE_NAME_OPTIONS = ["MANUAL", "INSTAGRAM", "THREADS", "TT", "OTHER"] as const;
const MAX_RECIPE_INGREDIENTS = Number(import.meta.env.VITE_MAX_RECIPE_INGREDIENTS ?? 50);
const MAX_RECIPE_INSTRUCTION_CHARS = Number(import.meta.env.VITE_MAX_RECIPE_INSTRUCTION_CHARS ?? 1000);
const MAX_RECIPE_NOTE_CHARS = Number(import.meta.env.VITE_MAX_RECIPE_NOTE_CHARS ?? 500);

function editableIngredientsFromRecipe(recipe: RecipeDetail): EditableIngredient[] {
  return recipe.ingredients
    .sort((left, right) => left.position - right.position)
    .map((ingredient) => ({
      id: ingredient.id,
      name: ingredient.name,
      quantity: ingredient.quantity ?? "",
      unit: ingredient.unit ?? "",
      note: ingredient.note ?? "",
    }));
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

function sourceImageForOption(resources: RecipeResource[], imageId: string | null | undefined): RecipeResource | undefined {
  if (!imageId) return undefined;
  return resources.find((resource) => resource.type === "IMAGE" && resource.imageId === imageId);
}

function selectedCoverChoice(recipe: RecipeDetail | null | undefined): CoverChoice {
  const selectedCover = recipe?.coverOptions.find((option) => option.selected);
  return selectedCover?.image ? { kind: "IMAGE", imageId: selectedCover.image.id } : { kind: "DEFAULT" };
}

function confirmDeleteResource(kind: "source" | "image"): boolean {
  return window.confirm(`Are you sure you want to delete this ${kind}?`);
}

function instructionsLength(value: string): number {
  return parseLines(value).join("\n").length;
}

function optionalText(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function validateEditableRecipe(ingredients: EditableIngredient[], instructions: string, note: string): string | null {
  if (ingredients.length > MAX_RECIPE_INGREDIENTS) {
    return "Recipe is too long.";
  }
  if (ingredients.some((ingredient) => !ingredient.name.trim())) {
    return "Ingredient name is required.";
  }
  if (instructionsLength(instructions) > MAX_RECIPE_INSTRUCTION_CHARS) {
    return "Recipe is too long.";
  }
  if (note.trim().length > MAX_RECIPE_NOTE_CHARS) {
    return "Recipe note is too long.";
  }
  return null;
}

export function RecipeDetailPage({ recipeId, onDeleted }: { recipeId: string; onDeleted: () => void }) {
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["recipe", recipeId], queryFn: () => getRecipe(recipeId) });
  const collectionsQuery = useQuery({ queryKey: ["collections"], queryFn: () => listCollections() });
  const tagsQuery = useQuery({ queryKey: ["tags", { limit: 100, offset: 0 }], queryFn: () => listTags({ limit: 100, offset: 0 }) });
  const recipeNotFound = query.error instanceof ApiError && query.error.errorCode === "RECIPE_NOT_FOUND";
  const recipe = recipeNotFound ? undefined : query.data;

  const [title, setTitle] = useState("");
  const [sourceName, setSourceName] = useState("MANUAL");
  const [authorName, setAuthorName] = useState("");
  const [cookTimeMinutes, setCookTimeMinutes] = useState("");
  const [calories, setCalories] = useState("");
  const [proteinGrams, setProteinGrams] = useState("");
  const [fatGrams, setFatGrams] = useState("");
  const [carbsGrams, setCarbsGrams] = useState("");
  const [selectedTagIds, setSelectedTagIds] = useState<string[]>([]);
  const [ingredients, setIngredients] = useState<EditableIngredient[]>([]);
  const [newIngredient, setNewIngredient] = useState<EditableIngredient>({ name: "", quantity: "", unit: "", note: "" });
  const [instructions, setInstructions] = useState("");
  const [note, setNote] = useState("");
  const [coverChoice, setCoverChoice] = useState<CoverChoice | null>(null);
  const [previewImage, setPreviewImage] = useState<{ label: string; url: string } | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (!recipe) return;
    setTitle(recipe.title);
    setSourceName(recipe.sourceName);
    setAuthorName(recipe.authorName ?? "");
    setCookTimeMinutes(recipe.cookTimeMinutes?.toString() ?? "");
    setCalories(recipe.nutritionEstimate?.calories?.toString() ?? "");
    setProteinGrams(recipe.nutritionEstimate?.proteinGrams?.toString() ?? "");
    setFatGrams(recipe.nutritionEstimate?.fatGrams?.toString() ?? "");
    setCarbsGrams(recipe.nutritionEstimate?.carbsGrams?.toString() ?? "");
    setSelectedTagIds(recipe.tags.map((tag) => tag.id));
    setIngredients(editableIngredientsFromRecipe(recipe));
    setNewIngredient({ name: "", quantity: "", unit: "", note: "" });
    setInstructions(recipe.instructions.join("\n"));
    setNote(recipe.note ?? "");
    setCoverChoice(selectedCoverChoice(recipe));
  }, [recipe]);

  const openFlags = useMemo(() => (recipe?.reviewFlags ?? []).filter((flag) => flag.status === "open"), [recipe]);
  const recipeCollectionIds = useMemo(() => new Set(recipe?.collections?.map((collection) => collection.id) ?? []), [recipe]);
  const availableCollections = collectionsQuery.data?.items ?? [];
  const availableTags = tagsQuery.data?.items ?? [];
  const openFlagMessages = useMemo(() => reviewMessages(openFlags), [openFlags]);
  const primaryUrlSource = useMemo(
    () => recipe?.resources.find((source) => source.type === "URL" && !source.parentResourceId) ?? null,
    [recipe],
  );

  const saveMutation = useMutation({
    mutationFn: () => {
      const error = validateEditableRecipe(ingredients, instructions, note);
      if (error) {
        setValidationError(error);
        return Promise.reject(new Error(error));
      }
      setValidationError(null);
      return patchRecipe(recipeId, {
        title,
        sourceName,
        authorName: optionalText(authorName),
        cookTimeMinutes: numberOrNull(cookTimeMinutes),
        nutritionEstimate: {
          calories: numberOrNull(calories),
          proteinGrams: numberOrNull(proteinGrams),
          fatGrams: numberOrNull(fatGrams),
          carbsGrams: numberOrNull(carbsGrams),
        },
        tagIds: selectedTagIds,
        ingredients: ingredients.map((ingredient) => ({
          ...(ingredient.id ? { id: ingredient.id } : {}),
          name: ingredient.name.trim(),
          quantity: optionalText(ingredient.quantity),
          unit: optionalText(ingredient.unit),
          note: optionalText(ingredient.note),
        })),
        instructions: parseLines(instructions),
        note,
        coverSelection: coverChoice ?? selectedCoverChoice(recipe),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recipe", recipeId] });
      queryClient.invalidateQueries({ queryKey: ["recipes"] });
      queryClient.invalidateQueries({ queryKey: ["collections"] });
    },
  });
  const deleteMutation = useMutation({
    mutationFn: () => deleteRecipe(recipeId),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: ["recipe", recipeId], exact: true });
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
    mutationFn: ({ sourceId, status }: { sourceId: string; status: "used" | "deleted" }) => patchRecipeResource(recipeId, sourceId, status),
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

  function toggleTag(tag: Tag): void {
    setSelectedTagIds((current) =>
      current.includes(tag.id) ? current.filter((tagId) => tagId !== tag.id) : [...current, tag.id],
    );
  }

  function updateIngredient(index: number, field: keyof EditableIngredient, value: string): void {
    setIngredients((current) => current.map((ingredient, ingredientIndex) =>
      ingredientIndex === index ? { ...ingredient, [field]: value } : ingredient,
    ));
  }

  function deleteIngredient(index: number): void {
    setIngredients((current) => current.filter((_, ingredientIndex) => ingredientIndex !== index));
  }

  function updateNewIngredient(field: keyof EditableIngredient, value: string): void {
    setNewIngredient((current) => ({ ...current, [field]: value }));
  }

  function addIngredient(): void {
    if (!newIngredient.name.trim()) return;
    setIngredients((current) => [...current, newIngredient]);
    setNewIngredient({ name: "", quantity: "", unit: "", note: "" });
  }

  return (
    <section className="panel">
      {query.isLoading ? <p>Loading...</p> : null}
      {query.error ? (
        <p role="alert">
          {recipeNotFound
            ? "Recipe not found. It may have been deleted."
            : query.error.message}
        </p>
      ) : null}
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
            <div className="form-grid">
              <label>
                Source type
                <select value={sourceName} onChange={(event) => setSourceName(event.target.value)}>
                  {SOURCE_NAME_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Author name
                <input value={authorName} onChange={(event) => setAuthorName(event.target.value)} />
              </label>
            </div>
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
            <div className="recipe-tag-selector" aria-label="Recipe tags">
              <span className="field-label">Tags</span>
              <div className="recipe-tag-chips">
                {availableTags.map((tag) => {
                  const selected = selectedTagIds.includes(tag.id);
                  return (
                    <button
                      key={tag.id}
                      type="button"
                      className={`recipe-tag-chip ${selected ? "is-selected" : ""}`}
                      aria-pressed={selected}
                      onClick={() => toggleTag(tag)}
                    >
                      {tag.name}
                    </button>
                  );
                })}
              </div>
              {tagsQuery.isLoading ? <p className="muted">Loading tags...</p> : null}
              {!tagsQuery.isLoading && availableTags.length === 0 ? <p className="muted">No tags yet.</p> : null}
            </div>
            <div className="ingredient-editor">
              <span className="field-label">Ingredients</span>
              <div className="ingredient-card ingredient-card-new">
                <h4>Add ingredient</h4>
                <div className="ingredient-grid">
                  <label>
                    New ingredient name
                    <input value={newIngredient.name} onChange={(event) => updateNewIngredient("name", event.target.value)} />
                  </label>
                  <label>
                    New ingredient quantity
                    <input value={newIngredient.quantity} onChange={(event) => updateNewIngredient("quantity", event.target.value)} />
                  </label>
                  <label>
                    New ingredient unit
                    <input value={newIngredient.unit} onChange={(event) => updateNewIngredient("unit", event.target.value)} />
                  </label>
                  <label>
                    New ingredient note
                    <input value={newIngredient.note} onChange={(event) => updateNewIngredient("note", event.target.value)} />
                  </label>
                </div>
                <button type="button" onClick={addIngredient} disabled={!newIngredient.name.trim()}>
                  Add ingredient
                </button>
              </div>
              <div className="ingredient-list">
                {ingredients.map((ingredient, index) => (
                  <div className="ingredient-card ingredient-row" key={index}>
                    <div className="ingredient-grid">
                      <label>
                        {`Ingredient ${index + 1} name`}
                        <input value={ingredient.name} onChange={(event) => updateIngredient(index, "name", event.target.value)} />
                      </label>
                      <label>
                        {`Ingredient ${index + 1} quantity`}
                        <input value={ingredient.quantity} onChange={(event) => updateIngredient(index, "quantity", event.target.value)} />
                      </label>
                      <label>
                        {`Ingredient ${index + 1} unit`}
                        <input value={ingredient.unit} onChange={(event) => updateIngredient(index, "unit", event.target.value)} />
                      </label>
                      <label>
                        {`Ingredient ${index + 1} note`}
                        <input value={ingredient.note} onChange={(event) => updateIngredient(index, "note", event.target.value)} />
                      </label>
                    </div>
                    <button
                      type="button"
                      className="ingredient-delete-button"
                      aria-label={`Delete ingredient ${index + 1}`}
                      onClick={() => deleteIngredient(index)}
                    >
                      x
                    </button>
                  </div>
                ))}
              </div>
            </div>
            <label>
              Instructions
              <textarea value={instructions} onChange={(event) => setInstructions(event.target.value)} rows={6} />
            </label>
            <label>
              Note
              <textarea value={note} onChange={(event) => setNote(event.target.value)} rows={4} />
            </label>
            {validationError ? <p role="alert" className="form-error">{validationError}</p> : null}

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
                    onClick={() => {
                      if (confirmDeleteResource("source")) {
                        sourceMutation.mutate({ sourceId: primaryUrlSource.id, status: "deleted" });
                      }
                    }}
                    disabled={sourceMutation.isPending}
                  >
                    Delete source
                  </button>
                  <button
                    type="button"
                    className="source-info-icon"
                    aria-label="Source deletion details"
                    title="Delete the link and all related media files."
                  >
                    i
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
                const relatedSource = sourceImageForOption(recipe.resources, optionImage?.id);
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
                          onClick={() => {
                            if (confirmDeleteResource("image")) {
                              sourceMutation.mutate({ sourceId: relatedSource.id, status: "deleted" });
                            }
                          }}
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

          {recipe.debug?.resources.length ? (
            <section>
              <h3>Debug resources</h3>
              <ul>
                {recipe.debug.resources.map((source) => (
                  <li key={source.id}>
                    {source.source}/{source.type}: {source.status}
                    {source.parentResourceId ? " (from URL)" : ""}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {recipe.debug?.embedding ? (
            <section className="debug-card">
              <h3>Embedding</h3>
              <p>Status: {recipe.debug.embedding.status}</p>
              <p>Model: {recipe.debug.embedding.model}</p>
            </section>
          ) : null}

          {recipe.debug?.embeddingInput ? (
            <section className="debug-card">
              <h3>Embedding input preview</h3>
              <p>Hash {recipe.debug.embeddingInput.inputHash}</p>
              <pre>{recipe.debug.embeddingInput.input}</pre>
            </section>
          ) : null}

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
