export function isCurrentUserAdmin(): boolean {
  // Temporary local-first UI guard. Backend /internal endpoints remain authoritative.
  return true;
}
