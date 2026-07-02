---
name: python-backend-style
---

# Python Backend Style

Use this skill when editing Python backend code in this project.

## General Python Style

* Follow official Python style conventions for formatting, naming, imports, readability, and code organization.

* Prefer readable, explicit code over clever shortcuts.

* Use clear names for variables, functions, classes, modules, and constants.

* Keep formatting compatible with standard Python tooling, for example Ruff/Black-style formatting.

* Avoid unnecessary abstractions, but extract repeated or conceptually independent logic.

## Function Size and Flow

* Avoid very long functions, especially functions hundreds of lines long.

* Split long functionality into meaningful logical blocks.

* Each extracted function should represent a clear conceptual step, not just wrap one line or one trivial call.

* Do not create one-line / one-call helper functions by default.

* Exception: one-line or one/two-call helpers are acceptable for utilities or when the underlying expression/call sequence is confusing enough that a named function makes the code significantly clearer.

* The main function should read as a visually understandable scenario of meaningful calls.

* Prefer logical extraction over mechanical extraction.

Good:

```python

def import_recipe(...) -> Recipe:

    context = build_import_context(...)

    sources = collect_ready_sources(context)

    extracted = extract_recipe_data(context, sources)

    recipe = persist_extracted_recipe(context, extracted)

    schedule_embedding_retry_if_needed(context, recipe)

    return recipe

```

Avoid extracting meaningless wrappers:

```python

def get_owner_id(job: ImportJob) -> UUID:

    return job.owner_id

```

unless the name captures non-obvious domain meaning.

* The goal is not to maximize the number of functions.

* The goal is to keep code organized into understandable logical blocks.

## Application Layers

* Do not mix unrelated application layers.

* Keep API layer, business logic, persistence logic, schemas, background jobs, and utilities separated.

* FastAPI routers should be thin.

* Business decisions should live in service/use-case code, not in routers.

* Database access should live in repositories, persistence modules, or clearly separated database helper functions.

* Do not hide database writes inside Pydantic validators, serializers, or response-building code.

## Database Query Patterns

* If repeated database query patterns appear in different places, extract them.

* Examples of repeated patterns:

  * filtering entities by owner

  * creating common domain records

  * getting active records

  * checking existence

  * fetching by id with ownership checks

* Put reusable database operations into a dedicated module close to the relevant domain.

* Call these functions from business logic instead of duplicating query code.

Example:

```python

# recipes/db_queries.py

def get_recipe_by_id_for_owner(

    session: Session,

    *,

    recipe_id: UUID,

    owner_id: UUID,

) -> Recipe | None:

    ...

```

```python

# recipes/service.py

recipe = get_recipe_by_id_for_owner(

    session,

    recipe_id=recipe_id,

    owner_id=owner_id,

)

```

## Pydantic Schemas and Serialization

* Use Pydantic v2 schemas as the primary place for validation, deserialization, and serialization rules.

* Prefer schema-level tools instead of ad-hoc `serialize_something()` / `deserialize_something()` functions.

* Use Pydantic features deliberately:

  * `model_validate`

  * `model_dump`

  * `validation_alias`

  * `serialization_alias`

  * `alias`

  * `model_validator`

  * `model_serializer`

  * `computed_field`

  * `field_serializer`

* Keep serialization/deserialization logic as much as possible inside the schema layer.

* Avoid mixing serialization logic with services, routers, repositories, or database models.

* Use mixins, common base classes to store and reuse the same fields / functionality among schemas

## Two Schema Flows

Keep two schema flows mentally and structurally separate.

### 1. External input → internal validated data

This is validation/deserialization.

Use this flow for:

* request bodies

* external provider responses

* imported data

* raw JSON

* untrusted dictionaries

Relevant tools:

* `model_validate`

* `validation_alias`

* `alias`

* `model_validator`

* field validators

Example:

```python

class RecipeImportInput(BaseModel):

    source_url: str = Field(validation_alias="sourceUrl")

```

### 2. Internal data → external representation

This is serialization/output.

Use this flow for:

* API responses

* JSON output

* response models

* client-facing DTOs

Relevant tools:

* `model_dump`

* `serialization_alias`

* `alias`

* `computed_field`

* `field_serializer`

* `model_serializer`

Example:

```python

class RecipeOut(BaseModel):

    id: UUID

    title: str

    @computed_field

    @property

    def display_title(self) -> str:

        return self.title.strip()

```

* Do not make one schema do conflicting jobs if the input shape and output shape are meaningfully different.

* Prefer separate schemas for input and output when it improves clarity.

## FastAPI

* Use `APIRouter` for route organization.

* Keep routes grouped by domain or feature.

* Use `response_model` explicitly for endpoints.

* Use FastAPI dependency aliases consistently for reuse.

* Prefer `typing.Annotated` for dependencies.

Example:

```python

SessionDep = Annotated[Session, Depends(get_session)]

CurrentUserDep = Annotated[User, Depends(get_current_user)]

```

```python

router = APIRouter(prefix="/recipes", tags=["recipes"])

@router.get("/{recipe_id}", response_model=RecipeOut)

def get_recipe(

    recipe_id: UUID,

    session: SessionDep,

    current_user: CurrentUserDep,

) -> RecipeOut:

    ...

```

* If the internal return type differs from the external API schema, keep `response_model` explicit.

* Do not rely on implicit response model inference when it makes the API contract less clear.

## Typing

* Prefer explicit type annotations for public functions, service methods, repositories, and background tasks.

* Use `typing.Annotated` where framework metadata is attached to a type.

* Use `collections.abc` for `Sequence`, `Mapping`, `Callable`, `Iterable`.

* Avoid `Any` unless there is a clear boundary with external or untyped data.

* For decorators, annotate the original function return type in the function body; type the decorator to express the transformed external callable type.

## Parameters and Context Objects

* If many parameters must be passed through a chain of function calls, create a dedicated Parameters or Context object.

* Build this object once near the beginning of the flow.

* Pass and update the context object in subsequent calls.

* Use this for coherent operational context, not as a dumping ground for unrelated state.

Example:

```python

@dataclass

class RecipeImportContext:

    session: Session

    owner_id: UUID

    import_job_id: UUID

    source_count: int

```

```python

context = build_recipe_import_context(session, job, ready_sources)

extracted = extract_recipe(context)

recipe = persist_recipe(context, extracted)

```

* Prefer immutable or carefully controlled context objects when possible.

* Do not use context objects to hide unclear dependencies.

## Constants, Statuses, and Enums

* Store constants in dedicated files or modules.

* Store statuses and enums in dedicated files or modules as well.

* Do not scatter magic strings, numeric thresholds, status names, queue names, enum values, or repeated config values across the codebase.

* Keep constants close to the domain if they are domain-specific.

* Use a shared constants module only for genuinely cross-domain constants.

* If constants, statuses, or enums become too numerous, organize them hierarchically instead of keeping one large flat file.

* Add comments for constants, describing their purpose

Example for a small domain:

```python

# recipes/constants.py

MAX_IMPORT_SOURCE_COUNT = 10

RECIPE_IMPORT_QUEUE_NAME = "recipe-import"

```

Example when constants grow:

```text

recipes/

    constants/

        __init__.py

        import_jobs.py

        embeddings.py

        parsing.py

        queues.py

```

Example:

```python

# recipes/constants/import_jobs.py

from enum import StrEnum

class RecipeImportStatus(StrEnum):

    PENDING = "pending"

    PROCESSING = "processing"

    FAILED = "failed"

    COMPLETED = "completed"

MAX_IMPORT_SOURCE_COUNT = 10

```

* Prefer enum/status imports from the constants module over duplicating raw strings in services, routers, workers, tests, or schemas.

## Utilities

* Extract common utility functions when they are used in more than one place or are not tied to a specific domain model.

* Examples:

  * `normalize_str`

  * `parse_date`

  * `handle_date`

  * `slugify`

  * `safe_strip`

* Put shared utilities into a dedicated utilities module.

* Prefer domain-local utilities when the logic is only meaningful inside one domain.

* Do not create a global utility function for logic that actually belongs to a domain/service/schema.

## File and Module Organization

* Do not mix distant, independent data and logic in one file/module.

* Split modules hierarchically by domain, feature, or technical responsibility.

* Keep related concepts near each other.

* Preserve a reasonable balance: do not create one file per function.

* A module should usually have a clear reason to exist and a coherent theme.

Use this as guidance, not as a mandatory structure for every domain.

## SQLAlchemy

* Use sync SQLAlchemy consistently in this project.

* Keep database access in repositories, query modules, or clearly separated persistence functions.

* Avoid mixing SQLAlchemy models with API response-shaping logic.

* Avoid performing database operations from Pydantic validators or serializers.

* Keep transaction boundaries explicit and easy to reason about.

## Background Jobs

* Put business logic in services that can be called from both API routes and background jobs.

* Avoid duplicating business logic between request handlers and workers.

## Logging

* Prefer structured logging.

* Bind repeated context once per operation.

* Do not repeat large logging context in every log call.

* Use stable event messages and structured fields.

* If many log calls share fields such as `owner_id`, `job_id`, `source_count`, or `component`, create a bound logger or context object.

* Do not let debug logging obscure the main business flow.

Preferred style:

```python

log = bind_logger(

    logger,

    component="recipes.import",

    owner_id=job.owner_id,

    import_job_id=job.id,

    source_count=len(ready_sources),

)

log.info("AI extraction started")

log.error("AI extraction provider threw", error=repr(error))

```

## Error Handling

* Raise domain-specific exceptions from service code.

* Translate domain errors to HTTP errors at API boundaries.

* Preserve original exceptions where useful with exception chaining.

* Do not swallow exceptions silently.

* Keep retryable and non-retryable errors distinguishable when working with background jobs.

* Store custon errors / error statuses / exceptions in a separate module

## Tests

* Test-specific functionality, fake data, monkeypatching helpers, and call substitutions should live outside production code.

* Put test fixtures, fake providers, test builders, and override helpers into test modules.

* Do not add test-only branches to the main application code unless there is a clear and justified seam.

* Use fixtures for dependency overrides and reusable test data.

* Prefer focused unit tests for service logic.

* Use integration tests for API + DB boundaries.

* Add regression tests for bug fixes.

Example:

```text

tests/

    fixtures/

        recipes.py

        users.py

    fakes/

        ai_provider.py

    test_recipe_import.py

```

## Maintainability Rule

When changing code, preserve or improve:

* clear layering

* explicit data flow

* predictable serialization/deserialization

* small readable functions

* reusable database query abstractions

* consistent FastAPI dependency style

* clean separation between production code and test helpers
