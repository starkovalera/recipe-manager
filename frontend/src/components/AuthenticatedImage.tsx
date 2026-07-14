import { useQuery } from "@tanstack/react-query";
import type { ImgHTMLAttributes } from "react";
import { useEffect, useState } from "react";

import { getMediaBlob, isApiMediaUrl } from "../api/client";

type AuthenticatedImageProps = Omit<ImgHTMLAttributes<HTMLImageElement>, "src"> & {
  src: string;
};

export function AuthenticatedImage({ src, ...imageProps }: AuthenticatedImageProps) {
  const protectedMedia = isApiMediaUrl(src);
  const mediaQuery = useQuery({
    queryKey: ["media", src],
    queryFn: () => getMediaBlob(src),
    enabled: protectedMedia,
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

  return <img {...imageProps} src={protectedMedia ? objectUrl : src} />;
}
