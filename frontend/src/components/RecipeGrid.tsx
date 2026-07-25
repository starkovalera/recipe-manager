import { useMemo } from "react";

import defaultRecipeImage from "../assets/default-recipe.svg";
import type { MediaReference, RecipeList } from "../api/types";
import { useMediaAccess } from "../media/useMediaAccess";
import { MediaImage } from "./MediaImage";

type RecipeListItem = RecipeList["items"][number];

export function RecipeGrid({ recipes, onSelect }: { recipes: RecipeListItem[]; onSelect: (recipeId: string) => void }) {
  const references = useMemo(
    () => recipes.flatMap((recipe) => recipe.coverImage ? [{ type: "recipe_image", id: recipe.coverImage.id } satisfies MediaReference] : []),
    [recipes],
  );
  const mediaAccess = useMediaAccess(references);
  if (recipes.length === 0) {
    return <p>No recipes yet.</p>;
  }

  return (
    <div className="recipe-grid">
      {recipes.map((recipe) => (
        <button className="recipe-card" key={recipe.id} type="button" onClick={() => onSelect(recipe.id)}>
          {recipe.hasOpenReviewFlags ? (
            <span className="recipe-card-flag" aria-label={`${recipe.title} requires review`}>
              !
            </span>
          ) : null}
          <MediaImage
            grant={recipe.coverImage ? mediaAccess.grantFor({ type: "recipe_image", id: recipe.coverImage.id }) : undefined}
            fallbackSrc={defaultRecipeImage}
            alt={`${recipe.title} cover`}
          />
          <span>{recipe.title}</span>
        </button>
      ))}
    </div>
  );
}
