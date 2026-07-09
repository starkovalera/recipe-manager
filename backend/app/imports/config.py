from app.core.config import Settings


class ImportConfig:
    max_import_images: int
    max_import_videos: int
    max_upload_bytes: int
    max_video_bytes: int
    max_recipe_ingredients: int
    max_recipe_instruction_chars: int
    import_min_confidence: float

    def __init__(
        self,
        max_import_images: int,
        max_import_videos: int,
        max_upload_bytes: int,
        max_video_bytes: int,
        max_recipe_ingredients: int,
        max_recipe_instruction_chars: int,
        import_min_confidence: float,
    ) -> None:
        self.max_import_images = max_import_images
        self.max_import_videos = max_import_videos
        self.max_upload_bytes = max_upload_bytes
        self.max_video_bytes = max_video_bytes
        self.max_recipe_ingredients = max_recipe_ingredients
        self.max_recipe_instruction_chars = max_recipe_instruction_chars
        self.import_min_confidence = import_min_confidence

    @classmethod
    def from_settings(cls, settings: Settings) -> "ImportConfig":
        return cls(
            settings.max_import_images,
            settings.max_import_videos,
            settings.max_upload_bytes,
            settings.max_video_bytes,
            settings.max_recipe_ingredients,
            settings.max_recipe_instruction_chars,
            settings.import_min_confidence,
        )
