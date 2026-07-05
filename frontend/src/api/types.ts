export type RecipeImage = { id: string; mediaUrl: string };

export type ImportJob = {
  jobId: string;
  status: "queued" | "running" | "succeeded" | "succeeded_with_flags" | "failed" | "cancelled";
  createdRecipeId?: string | null;
  errorCode?: string | null;
  errorMessage?: string | null;
};

export type Notification = {
  id: string;
  type: string;
  status: "unread" | "read" | string;
  title: string;
  message: string;
  entityType?: string | null;
  entityId?: string | null;
  data?: Record<string, unknown> | null;
  readAt?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
};

export type NotificationList = {
  items: Notification[];
};

export type NotificationsMarkAllReadResult = {
  updatedCount: number;
};

export type Tag = {
  id: string;
  name: string;
  description?: string | null;
  deletedAt?: string | null;
};

export type TagList = {
  items: Tag[];
  total: number;
  limit: number;
  offset: number;
};

export type TagListParams = {
  limit?: number;
  offset?: number;
};

export type TagUsage = {
  recipeCount: number;
};

export type SearchSuggestion = {
  type: "tag" | "ingredient_query" | "source_name" | "author_name" | "title";
  id?: string | null;
  recipeId?: string | null;
  value?: string | null;
  label: string;
};

export type SearchSuggestionList = {
  items: SearchSuggestion[];
};

export type SearchRequest = {
  text?: string | null;
  selected?: SearchSuggestion[];
  limit?: number;
  offset?: number;
};

export type SearchResponse = {
  items: Array<RecipeList["items"][number] & {
    matchReasons: Array<{ type: string; label: string; score?: number | null }>;
  }>;
  limit: number;
  offset: number;
  hasMore: boolean;
};

export type SearchExplainResponse = {
  textPresent: boolean;
  filters: {
    tagId?: string | null;
    ingredientQueries: string[];
    sourceName?: string | null;
    authorName?: string | null;
    titleRecipeId?: string | null;
  };
  provider?: string | null;
  model?: string | null;
  distanceMetric: string;
  candidateCount: number;
  returnedCount: number;
  limit: number;
  offset: number;
  hasMore: boolean;
  snapshotPersisted: boolean;
  items: Array<RecipeList["items"][number] & {
    matchReasons: Array<{ type: string; label: string; score?: number | null }>;
    debug: {
      rank?: number | null;
      distance?: number | null;
      similarity?: number | null;
      embeddingStatus?: string | null;
      embeddingModel?: string | null;
      inputHash?: string | null;
      embeddingInputPreview?: string | null;
    };
  }>;
};

export type EmbeddingInputPreview = {
  recipeId: string;
  input: string;
  inputHash: string;
};

export type InternalImportJobList = {
  items: Array<{
    id: string;
    ownerId: string;
    clientId: string;
    clientImportId?: string | null;
    dedupeKey?: string | null;
    status: string;
    errorCode?: string | null;
    errorMessage?: string | null;
    createdRecipeId?: string | null;
    createdAt?: string | null;
    startedAt?: string | null;
    finishedAt?: string | null;
    statusHistory: Array<{ status: string; changedAt?: string | null }>;
    sources: Array<{ id: string; type: string; status: string; url?: string | null; originalName?: string | null; position: number }>;
    events: Array<{ id: string; eventType: string; payload?: Record<string, unknown> | null; createdAt?: string | null }>;
  }>;
};

export type InternalRecipeEmbeddingList = {
  items: Array<{
    recipeId: string;
    ownerId?: string | null;
    recipeTitle?: string | null;
    status: string;
    model: string;
    inputHash?: string | null;
    failedAttempts: number;
    errorMessage?: string | null;
    lastAttemptAt?: string | null;
    lastErrorAt?: string | null;
    createdAt?: string | null;
    updatedAt?: string | null;
    events: Array<{
      id: string;
      eventType: string;
      statusAfter?: string | null;
      payload?: Record<string, unknown> | null;
      createdAt?: string | null;
    }>;
  }>;
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
  total: number;
  limit: number;
  offset: number;
};

export type RecipeListParams = {
  limit?: number;
  offset?: number;
  tag?: string;
  ingredientQuery?: string[];
  sourceName?: string;
  authorName?: string;
  title?: string;
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
  tags: Tag[];
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
  sourceName?: string;
  authorName?: string | null;
  cookTimeMinutes?: number | null;
  nutritionEstimate?: Record<string, number | null> | null;
  ingredients?: Array<{ id?: string | null; name: string; quantity?: string | null; unit?: string | null; note?: string | null }>;
  instructions?: string[];
  tagIds?: string[];
  note?: string;
  coverSelection?: { kind: "DEFAULT" | "IMAGE"; imageId?: string | null };
};

export type CollectionList = {
  items: Array<{ id: string; name: string; description?: string | null; recipeCount: number }>;
  total: number;
  limit: number;
  offset: number;
};

export type CollectionDetail = CollectionList["items"][number] & {
  recipes: RecipeList["items"];
};
