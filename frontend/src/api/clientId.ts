const STORAGE_KEY = "recipe-manager-client-id";

function createClientId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `local_${crypto.randomUUID()}`;
  }
  return `local_${Date.now()}_${Math.random().toString(36).slice(2)}`;
}

export function getClientId(): string {
  const existing = localStorage.getItem(STORAGE_KEY);
  if (existing) return existing;
  const created = createClientId();
  localStorage.setItem(STORAGE_KEY, created);
  return created;
}
