"""add recipe search text

Revision ID: 20260629_0008
Revises: 20260629_0007
Create Date: 2026-06-29
"""

import hashlib
import json
import re

import sqlalchemy as sa

from alembic import op

revision = "20260629_0008"
down_revision = "20260629_0007"
branch_labels = None
depends_on = None


_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_search_text(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value.strip()).casefold()


def _json_value(value) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _backfill_existing_recipes() -> None:
    connection = op.get_bind()
    recipe_rows = connection.execute(
        sa.text(
            """
            SELECT id, title, source_name, author_name, instructions, nutrition_estimate, cook_time_minutes
            FROM recipes
            """
        )
    ).mappings()
    ingredient_rows = connection.execute(sa.text("SELECT recipe_id, search_name FROM ingredients ORDER BY position, id")).mappings()
    ingredients_by_recipe: dict[str, list[str]] = {}
    for ingredient in ingredient_rows:
        ingredients_by_recipe.setdefault(ingredient["recipe_id"], []).append(ingredient["search_name"] or "")

    for recipe in recipe_rows:
        instructions = _json_value(recipe["instructions"])
        nutrition_estimate = _json_value(recipe["nutrition_estimate"])
        parts = [
            recipe["title"] or "",
            recipe["source_name"] or "",
            recipe["author_name"] or "",
            *ingredients_by_recipe.get(recipe["id"], []),
            instructions,
            nutrition_estimate,
            str(recipe["cook_time_minutes"]) if recipe["cook_time_minutes"] is not None else "",
        ]
        search_text = _normalize_search_text(" ".join(part for part in parts if part))
        search_hash = hashlib.sha256(search_text.encode("utf-8")).hexdigest()
        connection.execute(
            sa.text("UPDATE recipes SET search_text = :search_text, search_text_hash = :search_hash WHERE id = :recipe_id"),
            {"search_text": search_text, "search_hash": search_hash, "recipe_id": recipe["id"]},
        )


def upgrade() -> None:
    op.add_column("recipes", sa.Column("search_text", sa.Text(), nullable=True))
    op.add_column("recipes", sa.Column("search_text_hash", sa.String(), nullable=True))
    _backfill_existing_recipes()


def downgrade() -> None:
    with op.batch_alter_table("recipes") as batch_op:
        batch_op.drop_column("search_text_hash")
        batch_op.drop_column("search_text")
