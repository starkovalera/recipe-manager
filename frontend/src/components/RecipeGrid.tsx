import defaultRecipeImage from "../assets/default-recipe.svg";
import { mediaUrl } from "../api/client";
import type { RecipeList } from "../api/types";

type RecipeListItem = RecipeList["items"][number];

export function getRecipePreviewUrl(recipe: RecipeListItem): string {
  return recipe.coverImage ? mediaUrl(recipe.coverImage.mediaUrl) : defaultRecipeImage;
}

export function RecipeGrid({ recipes, onSelect }: { recipes: RecipeListItem[]; onSelect: (recipeId: string) => void }) {
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
          <img src={getRecipePreviewUrl(recipe)} alt={`${recipe.title} cover`} />
          <span>{recipe.title}</span>
        </button>
      ))}
    </div>
  );
}
