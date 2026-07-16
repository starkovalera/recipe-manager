from app.ai.schemas import ExtractionQuality
from app.imports.job_stages.recipe_resource_building import build_recipe_resources
from app.models import (
    Recipe,
    RecipeResource,
    RecipeResourceOrigin,
    RecipeResourceStatus,
    SourceName,
    SourceType,
)


def quality(*, primary: list[str], ignored: list[str], confidence: float = 0.9) -> ExtractionQuality:
    return ExtractionQuality(
        confidence=confidence,
        has_conflicts=False,
        has_ignored=bool(ignored),
        primary_source_refs=primary,
        ignored_source_refs=ignored,
    )


def resource(
    type: SourceType,
    *,
    source: RecipeResourceOrigin,
    url: str | None = None,
    parent: RecipeResource | None = None,
) -> RecipeResource:
    return RecipeResource(
        owner_id="user-1",
        type=type,
        source=source,
        url=url,
        parent=parent,
        position=0,
    )


def test_build_recipe_resources_maps_final_statuses_and_aggregates_url_parent():
    recipe = Recipe(owner_id="user-1")
    url = resource(SourceType.URL, source=RecipeResourceOrigin.MANUAL, url="https://www.instagram.com/p/recipe")
    used_text = resource(SourceType.TEXT, source=RecipeResourceOrigin.URL, parent=url)
    ignored_image = resource(SourceType.IMAGE, source=RecipeResourceOrigin.URL, parent=url)
    resources = [url, used_text, ignored_image]

    has_ignored_primary = build_recipe_resources(
        recipe,
        resources,
        [used_text, ignored_image],
        {used_text: "source_1", ignored_image: "source_2"},
        quality(primary=["source_1"], ignored=["source_2"]),
    )

    assert used_text.status == RecipeResourceStatus.USED
    assert ignored_image.status == RecipeResourceStatus.IGNORED
    assert url.status == RecipeResourceStatus.USED
    assert recipe.source_name == SourceName.INSTAGRAM
    assert has_ignored_primary is False


def test_build_recipe_resources_marks_url_ignored_only_when_all_children_are_ignored():
    recipe = Recipe(owner_id="user-1")
    url = resource(SourceType.URL, source=RecipeResourceOrigin.MANUAL, url="https://example.com/recipe")
    ignored_text = resource(SourceType.TEXT, source=RecipeResourceOrigin.URL, parent=url)

    has_ignored_primary = build_recipe_resources(
        recipe,
        [url, ignored_text],
        [ignored_text],
        {ignored_text: "source_1"},
        quality(primary=[], ignored=["source_1"]),
    )

    assert url.status == RecipeResourceStatus.IGNORED
    assert recipe.source_name == SourceName.OTHER
    assert has_ignored_primary is True


def test_build_recipe_resources_keeps_childless_url_unknown():
    recipe = Recipe(owner_id="user-1")
    url = resource(SourceType.URL, source=RecipeResourceOrigin.MANUAL, url="https://example.com/recipe")

    has_ignored_primary = build_recipe_resources(
        recipe,
        [url],
        [],
        {},
        quality(primary=[], ignored=[]),
    )

    assert url.status == RecipeResourceStatus.UNKNOWN
    assert url.assessment_reason is None
    assert url.assessment_confidence is None
    assert has_ignored_primary is False


def test_build_recipe_resources_uses_manual_source_name_for_active_manual_text():
    recipe = Recipe(owner_id="user-1")
    manual_text = resource(SourceType.TEXT, source=RecipeResourceOrigin.MANUAL)

    build_recipe_resources(
        recipe,
        [manual_text],
        [manual_text],
        {manual_text: "source_1"},
        quality(primary=["source_1"], ignored=[]),
    )

    assert recipe.source_name == SourceName.MANUAL
