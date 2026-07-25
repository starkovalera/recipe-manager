import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";

import { requestMediaAccess } from "../api/client";
import type { DownloadGrant, MediaReference } from "../api/types";

const EXPIRY_REFRESH_MARGIN_MS = 5_000;
const MAX_BROWSER_TIMER_MS = 2_147_000_000;

export function mediaReferenceKey(reference: MediaReference): string {
  return `${reference.type}:${reference.id}`;
}

export function useMediaAccess(references: MediaReference[]) {
  const uniqueReferences = useMemo(() => {
    const unique = new Map<string, MediaReference>();
    for (const reference of references) unique.set(mediaReferenceKey(reference), reference);
    return [...unique.values()];
  }, [references]);
  const referenceKeys = uniqueReferences.map(mediaReferenceKey);
  const query = useQuery({
    queryKey: ["media-access", referenceKeys],
    queryFn: () => requestMediaAccess(uniqueReferences),
    enabled: uniqueReferences.length > 0,
    staleTime: (currentQuery) => {
      const delay = grantRefreshDelay(currentQuery.state.data?.items.flatMap((item) => item.grant ?? []));
      return delay === false ? Infinity : delay;
    },
    refetchInterval: (currentQuery) => grantRefreshDelay(currentQuery.state.data?.items.flatMap((item) => item.grant ?? [])),
  });
  const grants = useMemo<Map<string, DownloadGrant>>(
    () => new Map<string, DownloadGrant>(
      query.data?.items.flatMap((item) => item.grant ? [[mediaReferenceKey(item), item.grant] as const] : []) ?? [],
    ),
    [query.data],
  );
  return { ...query, grantFor: (reference: MediaReference) => grants.get(mediaReferenceKey(reference)) };
}

export function grantRefreshDelay(grants: DownloadGrant[] | undefined): number | false {
  const expiries = (grants ?? [])
    .flatMap((grant) => grant.expiresAt ? [new Date(grant.expiresAt).getTime()] : [])
    .filter(Number.isFinite);
  if (!expiries.length) return false;
  return Math.min(MAX_BROWSER_TIMER_MS, Math.max(1, Math.min(...expiries) - Date.now() - EXPIRY_REFRESH_MARGIN_MS));
}
