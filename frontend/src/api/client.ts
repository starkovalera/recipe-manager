import { getClientId } from "./clientId";
import type { CollectionDetail, CollectionList, ImportJob, RecipeDetail, RecipeList, RecipePatch } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
let debugApiLogging = import.meta.env.VITE_DEBUG_API === "true";

export function setApiDebugLoggingForTests(enabled: boolean) {
  debugApiLogging = enabled;
}

function writeApiLog(level: "info" | "error", message: string, meta: Record<string, unknown>) {
  console[level](message, meta);
  if (import.meta.env.DEV && import.meta.env.MODE !== "test") {
    fetch("/_recipes_client_log", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ level, message, meta }),
    }).catch(() => undefined);
  }
}

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
  const textReader = (response as { text?: () => Promise<string> }).text;
  const payload = textReader ? await textReader.call(response).then((text) => (text ? JSON.parse(text) : undefined)) : await response.json();
  if (!response.ok) {
    throw new ApiError(payload?.errorCode ?? "API_ERROR", payload?.message ?? "Request failed.", response.status);
  }
  return payload as T;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = init.method ?? "GET";
  const startedAt = performance.now();
  if (debugApiLogging) {
    writeApiLog("info", "[recipes.frontend.api] request", { method, path });
  }
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, init);
    if (debugApiLogging) {
      writeApiLog("info", "[recipes.frontend.api] response", {
        method,
        path,
        status: response.status,
        durationMs: Math.round(performance.now() - startedAt),
      });
    }
    return parseResponse<T>(response);
  } catch (error) {
    if (debugApiLogging) {
      writeApiLog("error", "[recipes.frontend.api] error", {
        method,
        path,
        durationMs: Math.round(performance.now() - startedAt),
        error,
      });
    }
    throw error;
  }
}

export async function listRecipes(): Promise<RecipeList> {
  return request<RecipeList>("/recipes");
}

export async function getRecipe(recipeId: string): Promise<RecipeDetail> {
  return request<RecipeDetail>(`/recipes/${recipeId}`);
}

export async function patchRecipe(recipeId: string, patch: RecipePatch): Promise<RecipeDetail> {
  return request<RecipeDetail>(
    `/recipes/${recipeId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    },
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
  return request<ImportJob>(
    "/imports",
    {
      method: "POST",
      headers: { "X-Client-Id": getClientId() },
      body,
    },
  );
}

export async function getImportJob(jobId: string): Promise<ImportJob> {
  return request<ImportJob>(`/imports/${jobId}`);
}

export async function deleteRecipe(recipeId: string): Promise<void> {
  await request<void>(`/recipes/${recipeId}`, { method: "DELETE" });
}

export async function listCollections(): Promise<CollectionList> {
  return request<CollectionList>("/collections");
}

export async function createCollection(input: { name: string; description?: string | null }): Promise<CollectionDetail> {
  return request<CollectionDetail>("/collections", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export async function getCollection(collectionId: string): Promise<CollectionDetail> {
  return request<CollectionDetail>(`/collections/${collectionId}`);
}

export async function deleteCollection(collectionId: string): Promise<void> {
  await request<void>(`/collections/${collectionId}`, { method: "DELETE" });
}

export async function addRecipeToCollection(collectionId: string, recipeId: string): Promise<void> {
  await request<void>(`/collections/${collectionId}/recipes/${recipeId}`, { method: "PUT" });
}

export async function removeRecipeFromCollection(collectionId: string, recipeId: string): Promise<void> {
  await request<void>(`/collections/${collectionId}/recipes/${recipeId}`, { method: "DELETE" });
}
