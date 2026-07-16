import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { listRecipes, listSearchSuggestions, searchRecipes } from "../api/client";
import type { RecipeList, RecipeListParams, SearchRequest, SearchResponse, SearchSuggestion } from "../api/types";
import { PaginationControls } from "../components/PaginationControls";
import { RecipeGrid } from "../components/RecipeGrid";

const PAGE_LIMIT = 24;
const SUGGESTION_LIMIT = 10;

function paramsForChips(chips: SearchSuggestion[], limit: number, offset: number): RecipeListParams {
  const params: RecipeListParams = { limit, offset };
  for (const chip of chips) {
    if (chip.type === "tag" && chip.id) params.tag = chip.id;
    if (chip.type === "ingredient_query" && chip.value) params.ingredientQuery = [...(params.ingredientQuery ?? []), chip.value];
    if (chip.type === "source_name" && chip.value) params.sourceName = chip.value;
    if (chip.type === "author_name" && chip.value) params.authorName = chip.value;
    if (chip.type === "title" && chip.recipeId) params.title = chip.recipeId;
  }
  return params;
}

function chipKey(chip: SearchSuggestion): string {
  return `${chip.type}:${chip.id ?? chip.recipeId ?? chip.value ?? chip.label}`;
}

export function RecipeListPage({ onSelect }: { onSelect: (recipeId: string) => void }) {
  const [offset, setOffset] = useState(0);
  const [searchText, setSearchText] = useState("");
  const [chips, setChips] = useState<SearchSuggestion[]>([]);
  const normalizedSearchText = searchText.trim();
  const recipeParams = paramsForChips(chips, PAGE_LIMIT, offset);
  const shouldUseSearch = normalizedSearchText.length > 0 || chips.length > 0;
  const searchRequest: SearchRequest = {
    text: normalizedSearchText || null,
    selected: chips,
    limit: PAGE_LIMIT,
    offset,
  };
  const query = useQuery<RecipeList | SearchResponse>({
    queryKey: shouldUseSearch ? ["recipeSearch", searchRequest] : ["recipes", recipeParams],
    queryFn: () => (shouldUseSearch ? searchRecipes(searchRequest) : listRecipes(recipeParams)),
  });
  const suggestionsQuery = useQuery({
    queryKey: ["searchSuggestions", normalizedSearchText],
    queryFn: () => listSearchSuggestions({ q: normalizedSearchText, limit: SUGGESTION_LIMIT }),
    enabled: normalizedSearchText.length > 0,
  });
  const data = query.data;
  const hasMore = data && "hasMore" in data ? data.hasMore : false;
  const total = data && "total" in data ? data.total : offset + (data?.items.length ?? 0) + (hasMore ? 1 : 0);
  const limit = query.data?.limit ?? PAGE_LIMIT;

  function addChip(chip: SearchSuggestion) {
    setChips((current) => {
      if (current.some((item) => chipKey(item) === chipKey(chip))) return current;
      return [...current, chip];
    });
    setOffset(0);
    setSearchText("");
  }

  function removeChip(chip: SearchSuggestion) {
    setChips((current) => current.filter((item) => chipKey(item) !== chipKey(chip)));
    setOffset(0);
  }

  return (
    <section className="panel">
      <h2>Recipes</h2>
      <div className="search-panel">
        <label>
          Search recipes
          <input
            value={searchText}
            onChange={(event) => {
              setSearchText(event.target.value);
              setOffset(0);
            }}
          />
        </label>
        {suggestionsQuery.data && suggestionsQuery.data.items.length > 0 ? (
          <div className="suggestion-list">
            {suggestionsQuery.data.items.map((suggestion) => (
              <button key={chipKey(suggestion)} type="button" onClick={() => addChip(suggestion)}>
                {suggestion.label}
              </button>
            ))}
          </div>
        ) : null}
        {chips.length > 0 ? (
          <div className="selected-chips">
            {chips.map((chip) => (
              <button key={chipKey(chip)} type="button" onClick={() => removeChip(chip)} aria-label={`Remove ${chip.label} filter`}>
                {chip.label}
              </button>
            ))}
          </div>
        ) : null}
      </div>
      {query.isLoading ? <p>Loading...</p> : null}
      {query.error ? <p role="alert">{query.error.message}</p> : null}
      {query.data ? <RecipeGrid recipes={query.data.items} onSelect={onSelect} /> : null}
      {query.data ? <PaginationControls total={total} limit={limit} offset={query.data.offset ?? offset} onPage={setOffset} /> : null}
    </section>
  );
}
