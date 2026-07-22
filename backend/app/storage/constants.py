from enum import StrEnum


class StorageLocation(StrEnum):
    # Logical user-owned media storage shared by current persisted resource models.
    USER_MEDIA = "USER_MEDIA"


class StoragePurpose(StrEnum):
    # Original files supplied directly by an import request.
    IMPORT_SOURCE = "IMPORT_SOURCE"
    # Files downloaded or generated while processing an import.
    IMPORT_DERIVED = "IMPORT_DERIVED"
    # Media owned by a persisted recipe, including generated covers.
    RECIPE_MEDIA = "RECIPE_MEDIA"
    # Short-lived operation data without a durable domain owner.
    TEMPORARY = "TEMPORARY"
