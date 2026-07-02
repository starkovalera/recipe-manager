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
};

export type TagUsage = {
  recipeCount: number;
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
