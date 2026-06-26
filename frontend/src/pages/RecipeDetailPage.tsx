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
  removeRecipeFromCollection,
} from "../api/client";
import type { RecipeDetail } from "../api/types";

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
            <section className="flag-strip" aria-label="Open review flags">
              {openFlags.map((flag) => (
                <div className="flag-card" key={flag.id}>
                  <strong>{flag.reasonCode}</strong>
                  <span>{flag.message}</span>
                </div>
              ))}
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

            <fieldset className="cover-picker">
              <legend>Cover image</legend>
              {recipe.coverOptions.map((option) => {
                const value = option.image ? option.image.id : "DEFAULT";
                const checked = coverChoice.kind === "DEFAULT" ? value === "DEFAULT" : coverChoice.imageId === value;
                return (
                  <label className="cover-option" key={value}>
                    <input
                      type="radio"
                      name="cover"
                      checked={checked}
                      onChange={() =>
                        setCoverChoice(option.image ? { kind: "IMAGE", imageId: option.image.id } : { kind: "DEFAULT" })
                      }
                    />
                    <img src={option.image ? mediaUrl(option.image.mediaUrl) : defaultRecipeImage} alt={option.label} />
                    <span>{option.label}</span>
                  </label>
                );
              })}
            </fieldset>

            <button type="button" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
              Save
            </button>
          </section>

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
            <h3>Sources</h3>
            <ul>
              {recipe.sources.map((source) => (
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
