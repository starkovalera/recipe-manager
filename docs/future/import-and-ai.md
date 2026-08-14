# Import and AI Evolution

Stage: Captured

First-version scope: excluded unless separately promoted

## AI schema, prompts, and extraction rules

- Remove `sourcePosition` and `crop` from the Pydantic AI response schema for `coverCandidate`. They are currently `None`-only legacy compatibility fields after the OpenAI response schema was narrowed to `sourceRef` and `confidence`.
- Consider generated covers when extraction cannot select a sufficiently convincing source image. Define quality thresholds, cost controls, user visibility, storage lifecycle, and provenance before implementation.
- Align the extraction prompt with the configured ingredient-count and instruction-length limits. Any prompt change still requires explicit review and approval; backend validation remains authoritative.
- Require every returned tag to be copied verbatim from the supplied allowlist. Explicitly prohibit inflection, rewriting, translation, normalization, and synonym substitution; for example, changing `простое` to `простой` makes the tag invalid and causes it to be discarded. The prompt change still requires explicit review and approval.
- Consider extracting additional recipe recommendations into `Recipe.note`. This requires an explicitly approved prompt change, an AI output-schema migration, and rules for distinguishing source-authored recommendations from generated content.

## Platforms, sources, and evidence

- Preserve an author profile URL when `author_name` is derived from a supported platform URL. Build it from the platform's canonical profile prefix and account name, expose it separately from the display name, and render it as a link on recipe detail. Manually entered names without a URL remain plain text. Coordinate the import behavior with the owner-scoped Author capability in [`product-expansion.md`](product-expansion.md).
- Add Telegram import support after defining supported Telegram URL/content types and access constraints.
- Verify and harden import behavior for Instagram Reels and YouTube Shorts, including captions, images/posters, video download, and transcript behavior. YouTube video import is tracked separately in [`youtube-video-import.md`](youtube-video-import.md).
- Validate import URLs by platform prefix before creating an import job. Accept only explicitly supported platform URLs; reject all other URL platforms with a dedicated user-facing `platform not supported` error.

## Video and secondary resources

- Distinguish silent video from genuine transcription failure. The preferred option is to inspect downloaded media for an audio stream with PyAV before calling the transcription provider. A lower-confidence fallback is to classify known provider errors such as `Audio file processing failed`. Until then, both cases are recorded as failed transcript resources while the staged loader continues with any usable content.
- Add an environment-backed maximum duration for video audio tracks. When an audio track exceeds the configured limit, do not send it for transcription; record and handle the corresponding secondary resource as failed through the existing staged secondary-resource failure flow.
- Define the review behavior for a URL that was not the sole primary source but produced no successfully loaded secondary resources. The extractor receives no child evidence for that URL, so it cannot mark the primary URL as ignored through `ignoredSourceRefs`. Consider explicitly marking the URL resource as `IGNORED` from the staged loading result so the recipe receives a review flag.

## Refinement boundary

Split the list into independent capabilities before promotion. Each promoted capability must define product value, provider and policy constraints, source/resource semantics, failure behavior, observability, and the affected Design and Development tracks. Prompt and schema changes require explicit approval and a deterministic acceptance boundary.
