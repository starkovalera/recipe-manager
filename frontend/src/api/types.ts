export type RecipeImage = { id: string; mediaUrl: string };

export type ImportJob = {
  jobId: string;
  status: "pending" | "processing" | "succeeded" | "failed";
  createdRecipeId?: string | null;
  errorCode?: string | null;
  errorMessage?: string | null;
};

export type RecipeList = {
  items: Array<{
    id: string;
    title: string;
    coverImage?: RecipeImage | null;
    note?: string | null;
    updatedAt?: string | null;
    hasOpenReviewFlags?: boolean;
  }>;
};

export type RecipeResource = {
  id: string;
  type: string;
  source: string;
  role: string;
  parentResourceId?: string | null;
  status: string;
  imageId?: string | null;
  text?: string | null;
  url?: string | null;
};

export type ReviewFlag = {
  id: string;
  type?: string;
  status: string;
  reasonCode: string;
  message: string;
  details?: Record<string, unknown> | null;
  resolvedAt?: string | null;
};

export type RecipeDetail = RecipeList["items"][number] & {
  servings?: number | null;
  cookTimeMinutes?: number | null;
  nutritionEstimate?: Record<string, number | null> | null;
  authorName?: string | null;
  sourceName: string;
  tags: string[];
  instructions: string[];
  ingredients: Array<{ id: string; name: string; quantity?: string | null; unit?: string | null; note?: string | null; position: number }>;
  images: RecipeImage[];
  coverImage?: RecipeImage | null;
  coverOptions: Array<{ kind: string; image?: RecipeImage | null; label: string; selected: boolean }>;
  collections: Array<{ id: string; name: string }>;
  resources: RecipeResource[];
  sources: RecipeResource[];
  debugResources?: RecipeResource[];
  debugSources?: RecipeResource[];
  reviewFlags: ReviewFlag[];
};

export type RecipePatch = {
  title?: string;
  cookTimeMinutes?: number | null;
  nutritionEstimate?: Record<string, number | null> | null;
  ingredients?: Array<{ name: string; quantity?: string | null; unit?: string | null; note?: string | null }>;
  instructions?: string[];
  tags?: string[];
  note?: string;
  coverSelection?: { kind: "DEFAULT" | "IMAGE"; imageId?: string | null };
};

export type CollectionList = {
  items: Array<{ id: string; name: string; description?: string | null; recipeCount: number }>;
};

export type CollectionDetail = CollectionList["items"][number] & {
  recipes: RecipeList["items"];
};
