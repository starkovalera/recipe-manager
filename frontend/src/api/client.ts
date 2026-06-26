import { getClientId } from "./clientId";
import type { ImportJob, RecipeDetail, RecipeList } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export function mediaUrl(url: string): string {
  return url.startsWith("http://") || url.startsWith("https://") ? url : `${API_BASE_URL}${url}`;
}

export class ApiError extends Error {
  constructor(
    public errorCode: string,
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = await response.json();
  if (!response.ok) {
    throw new ApiError(payload.errorCode ?? "API_ERROR", payload.message ?? "Request failed.", response.status);
  }
  return payload as T;
}

export async function listRecipes(): Promise<RecipeList> {
  return parseResponse<RecipeList>(await fetch(`${API_BASE_URL}/recipes`));
}

export async function getRecipe(recipeId: string): Promise<RecipeDetail> {
  return parseResponse<RecipeDetail>(await fetch(`${API_BASE_URL}/recipes/${recipeId}`));
}

export async function patchRecipe(recipeId: string, patch: Partial<Pick<RecipeDetail, "title" | "note" | "instructions">>): Promise<RecipeDetail> {
  return parseResponse<RecipeDetail>(
    await fetch(`${API_BASE_URL}/recipes/${recipeId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    }),
  );
}

export async function createImport(input: { clientImportId: string; text?: string; url?: string; files?: File[] }): Promise<ImportJob> {
  const body = new FormData();
  body.set("clientImportId", input.clientImportId);
  if (input.text) body.set("text", input.text);
  if (input.url) body.set("url", input.url);
  for (const file of input.files ?? []) {
    body.append("files", file);
  }
  return parseResponse<ImportJob>(
    await fetch(`${API_BASE_URL}/imports`, {
      method: "POST",
      headers: { "X-Client-Id": getClientId() },
      body,
    }),
  );
}

export async function getImportJob(jobId: string): Promise<ImportJob> {
  return parseResponse<ImportJob>(await fetch(`${API_BASE_URL}/imports/${jobId}`));
}
