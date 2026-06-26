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
    note?: string | null;
    updatedAt?: string | null;
  }>;
};

export type RecipeDetail = RecipeList["items"][number] & {
  instructions: string[];
  ingredients: Array<{ id: string; name: string; quantity?: string | null; unit?: string | null; position: number }>;
  images: Array<{ id: string; role: string; mediaUrl: string; sourceImageId?: string | null }>;
  coverImage?: { id: string; role: string; mediaUrl: string; sourceImageId?: string | null } | null;
  sources: Array<{ id: string; type: string; status: string; text?: string | null; url?: string | null }>;
  reviewFlags: Array<{ id: string; status: string; reasonCode: string; message: string; resolvedAt?: string | null }>;
};
