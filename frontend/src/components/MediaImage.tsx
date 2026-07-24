import { useQuery } from "@tanstack/react-query";
import type { ImgHTMLAttributes } from "react";
import { useEffect, useState } from "react";

import { fetchAuthenticatedMedia } from "../api/client";
import type { DownloadGrant } from "../api/types";

type MediaImageProps = Omit<ImgHTMLAttributes<HTMLImageElement>, "src"> & {
  grant?: DownloadGrant;
  fallbackSrc: string;
};

export function MediaImage({ grant, fallbackSrc, ...imageProps }: MediaImageProps) {
  const authenticatedGrant = grant?.accessMode === "authenticated_fetch" ? grant : undefined;
  const mediaQuery = useQuery({
    queryKey: ["authenticated-media", authenticatedGrant?.url],
    // A bearer token cannot be attached by a plain <img src>; authenticated_fetch must use the API client.
    queryFn: () => fetchAuthenticatedMedia(authenticatedGrant!.url),
    enabled: Boolean(authenticatedGrant),
    staleTime: Infinity,
  });
  const [objectUrl, setObjectUrl] = useState<string>();

  useEffect(() => {
    if (!mediaQuery.data) {
      setObjectUrl(undefined);
      return;
    }
    const nextObjectUrl = URL.createObjectURL(mediaQuery.data);
    setObjectUrl(nextObjectUrl);
    return () => URL.revokeObjectURL(nextObjectUrl);
  }, [mediaQuery.data]);

  const src = grant?.accessMode === "direct" ? grant.url : objectUrl;
  return <img {...imageProps} src={src ?? fallbackSrc} />;
}
