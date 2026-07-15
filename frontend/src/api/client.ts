import { getClientId } from "./clientId";
import type {
  CollectionDetail,
  CollectionList,
  AccessUser,
  AccessUserList,
  AccountDeletionResult,
  CurrentUser,
  ImportJob,
  Invitation,
  InvitationList,
  InternalImportJobList,
  InternalRecipeEmbeddingList,
  Notification,
  NotificationList,
  NotificationsMarkAllReadResult,
  RecipeDetail,
  RecipeList,
  RecipeListParams,
  RecipePatch,
  SearchRequest,
  SearchExplainResponse,
  SearchResponse,
  SearchSuggestionList,
  Tag,
  TagList,
  TagListParams,
  TagUsage,
  UserStatus,
} from "./types";

export const DEFAULT_API_BASE_URL = "http://127.0.0.1:8081";
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;
let debugApiLogging = import.meta.env.VITE_DEBUG_API === "true";
export type ApiTokenProvider = () => Promise<string | null>;
let apiTokenProvider: ApiTokenProvider | null = null;

export function setApiTokenProvider(provider: ApiTokenProvider | null) {
  apiTokenProvider = provider;
}

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

export function isApiMediaUrl(url: string): boolean {
  return url.startsWith("/media/") || url.startsWith(`${API_BASE_URL}/media/`);
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

async function performRequest<T>(
  path: string,
  init: RequestInit,
  readResponse: (response: Response) => Promise<T>,
): Promise<T> {
  const method = init.method ?? "GET";
  const startedAt = performance.now();
  const url = `${API_BASE_URL}${path}`;
  if (debugApiLogging) {
    writeApiLog("info", "[recipes.frontend.api] request", { method, path, baseUrl: API_BASE_URL, url });
  }
  try {
    const headers = new Headers(init.headers);
    const token = apiTokenProvider ? await apiTokenProvider() : null;
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const response = await fetch(url, { ...init, headers });
    if (debugApiLogging) {
      writeApiLog("info", "[recipes.frontend.api] response", {
        method,
        path,
        baseUrl: API_BASE_URL,
        url,
        status: response.status,
        durationMs: Math.round(performance.now() - startedAt),
      });
    }
    return readResponse(response);
  } catch (error) {
    if (debugApiLogging) {
      writeApiLog("error", "[recipes.frontend.api] error", {
        method,
        path,
        baseUrl: API_BASE_URL,
        url,
        durationMs: Math.round(performance.now() - startedAt),
        error,
      });
    }
    throw error;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  return performRequest(path, init, parseResponse<T>);
}

export async function getMediaBlob(url: string): Promise<Blob> {
  const path = url.startsWith(API_BASE_URL) ? url.slice(API_BASE_URL.length) : url;
  return performRequest(path, {}, async (response) => {
    if (!response.ok) {
      return parseResponse<never>(response);
    }
    return response.blob();
  });
}

function withQuery(path: string, params?: Record<string, string | number | string[] | undefined>): string {
  if (!params) return path;
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (Array.isArray(value)) {
      for (const item of value) {
        search.append(key, item);
      }
    } else if (value !== undefined) {
      search.set(key, String(value));
    }
  }
  const query = search.toString();
  return query ? `${path}?${query}` : path;
}

export async function listRecipes(params?: RecipeListParams): Promise<RecipeList> {
  return request<RecipeList>(withQuery("/recipes", params));
}

export async function listSearchSuggestions(params: { q: string; limit?: number }): Promise<SearchSuggestionList> {
  return request<SearchSuggestionList>(withQuery("/search/suggestions", params));
}

export async function searchRecipes(input: SearchRequest): Promise<SearchResponse> {
  return request<SearchResponse>("/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export async function explainInternalSearch(input: SearchRequest): Promise<SearchExplainResponse> {
  return request<SearchExplainResponse>("/internal/search/explain", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export async function getCurrentUser(): Promise<CurrentUser> {
  return request<CurrentUser>("/me");
}

export async function provisionCurrentUser(): Promise<CurrentUser> {
  return request<CurrentUser>("/me/provision", { method: "POST" });
}

export async function deleteCurrentAccount(): Promise<AccountDeletionResult> {
  return request<AccountDeletionResult>("/me/deletion", { method: "POST" });
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

export async function patchReviewFlag(recipeId: string, flagId: string, status: "open" | "resolved"): Promise<RecipeDetail["reviewFlags"][number]> {
  return request<RecipeDetail["reviewFlags"][number]>(
    `/recipes/${recipeId}/review-flags/${flagId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    },
  );
}

export async function patchRecipeResource(recipeId: string, resourceId: string, status: "used" | "deleted"): Promise<RecipeDetail> {
  return request<RecipeDetail>(
    `/recipes/${recipeId}/resources/${resourceId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
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

export async function retryImportJob(jobId: string): Promise<ImportJob> {
  return request<ImportJob>(`/imports/${jobId}/retry`, { method: "POST" });
}

export async function retryInternalImportJob(jobId: string): Promise<ImportJob> {
  return request<ImportJob>(`/internal/import-jobs/${encodeURIComponent(jobId)}/retry`, { method: "POST" });
}

export async function listNotifications(): Promise<NotificationList> {
  return request<NotificationList>("/notifications");
}

export async function patchNotification(notificationId: string, status: "read" | "unread"): Promise<Notification> {
  return request<Notification>(
    `/notifications/${notificationId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    },
  );
}

export async function markAllNotificationsRead(lastNotificationId: string): Promise<NotificationsMarkAllReadResult> {
  return request<NotificationsMarkAllReadResult>(
    "/notifications/read-all",
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lastNotificationId }),
    },
  );
}

export async function listInternalImportJobs(): Promise<InternalImportJobList> {
  return request<InternalImportJobList>("/internal/import-jobs");
}

export async function listInternalRecipeEmbeddings(): Promise<InternalRecipeEmbeddingList> {
  return request<InternalRecipeEmbeddingList>("/internal/embeddings");
}

export async function retryInternalRecipeEmbedding(recipeId: string): Promise<void> {
  await request<void>(`/internal/embeddings/${recipeId}/retry`, { method: "POST" });
}

export async function listAccessUsers(): Promise<AccessUserList> {
  return request<AccessUserList>("/internal/access/users");
}

export async function assignUserRole(userId: string, role: string): Promise<AccessUser> {
  return request<AccessUser>(`/internal/access/users/${encodeURIComponent(userId)}/roles/${encodeURIComponent(role)}`, { method: "PUT" });
}

export async function revokeUserRole(userId: string, role: string): Promise<AccessUser> {
  return request<AccessUser>(`/internal/access/users/${encodeURIComponent(userId)}/roles/${encodeURIComponent(role)}`, { method: "DELETE" });
}

export async function updateAccessUserStatus(userId: string, status: Exclude<UserStatus, "DELETION_PENDING">): Promise<AccessUser> {
  return request<AccessUser>(`/internal/access/users/${encodeURIComponent(userId)}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status }),
  });
}

export async function listInvitations(): Promise<InvitationList> {
  return request<InvitationList>("/internal/invitations");
}

export async function createInvitation(email: string): Promise<Invitation> {
  return request<Invitation>("/internal/invitations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
}

export async function revokeInvitation(invitationId: string): Promise<Invitation> {
  return request<Invitation>(`/internal/invitations/${encodeURIComponent(invitationId)}/revoke`, { method: "POST" });
}

export async function listTags(params?: TagListParams): Promise<TagList> {
  return request<TagList>(withQuery("/tags", params));
}

export async function createTag(input: { name: string; description?: string | null }): Promise<Tag> {
  return request<Tag>("/tags", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export async function patchTag(tagId: string, input: { name: string; description?: string | null }): Promise<Tag> {
  return request<Tag>(`/tags/${tagId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export async function getTagUsage(tagId: string): Promise<TagUsage> {
  return request<TagUsage>(`/tags/${tagId}/usage`);
}

export async function deleteTag(tagId: string): Promise<Tag> {
  return request<Tag>(`/tags/${tagId}`, { method: "DELETE" });
}

export async function deleteRecipe(recipeId: string): Promise<void> {
  await request<void>(`/recipes/${recipeId}`, { method: "DELETE" });
}

export async function listCollections(params?: { limit?: number; offset?: number }): Promise<CollectionList> {
  return request<CollectionList>(withQuery("/collections", params));
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
