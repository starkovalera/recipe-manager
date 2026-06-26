from app.ai.prompt import recipe_extraction_prompt


def test_recipe_extraction_prompt_keeps_reference_import_rules():
    assert "Translate faithfully when needed" in recipe_extraction_prompt
    assert "cannot extract enough useful information" in recipe_extraction_prompt
    assert "When sources describe different recipes" in recipe_extraction_prompt
    assert "If you ignore any resources, and only in that case" in recipe_extraction_prompt
    assert "choose one best coverCandidate" in recipe_extraction_prompt
    assert "Do not duplicate steps when the same instruction appears in both caption text and transcript" in recipe_extraction_prompt
