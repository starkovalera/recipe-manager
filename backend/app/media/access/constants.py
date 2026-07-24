from enum import StrEnum


class MediaReferenceType(StrEnum):
    RECIPE_IMAGE = "recipe_image"
    IMPORT_SOURCE_IMAGE = "import_source_image"


class DownloadAccessMode(StrEnum):
    # The browser may assign the grant URL directly to src/href. This does not imply a public resource or provider.
    DIRECT = "direct"
    # The browser must fetch with the authenticated API client. This does not imply a LOCAL provider or private resource.
    AUTHENTICATED_FETCH = "authenticated_fetch"


class MediaItemErrorCode(StrEnum):
    MEDIA_NOT_FOUND = "MEDIA_NOT_FOUND"


PRESIGNED_MEDIA_TTL_SECONDS = 60
