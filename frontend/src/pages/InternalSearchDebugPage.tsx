import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { explainInternalSearch } from "../api/client";
import type { SearchSuggestion } from "../api/types";

function parseSelectedChips(value: string): SearchSuggestion[] {
  if (!value.trim()) return [];
  const parsed = JSON.parse(value);
  if (!Array.isArray(parsed)) {
    throw new Error("Selected chips JSON must be an array.");
  }
  return parsed as SearchSuggestion[];
}

function shortHash(value?: string | null) {
  return value ? `${value.slice(0, 12)}...` : "-";
}

function formatNumber(value?: number | null) {
  return value === null || value === undefined ? "-" : String(value);
}

export function InternalSearchDebugPage({ onOpenRecipe }: { onOpenRecipe: (recipeId: string) => void }) {
  const [text, setText] = useState("");
  const [selectedJson, setSelectedJson] = useState("");
  const [submitted, setSubmitted] = useState<{ text: string; selected: SearchSuggestion[] } | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);

  const explainQuery = useQuery({
    queryKey: ["internal-search-explain", submitted],
    queryFn: () => explainInternalSearch({ text: submitted?.text ?? "", selected: submitted?.selected ?? [], limit: 20, offset: 0 }),
    enabled: submitted !== null,
  });

  function runExplain() {
    try {
      const selected = parseSelectedChips(selectedJson);
      setParseError(null);
      setSubmitted({ text, selected });
    } catch (error) {
      setParseError(error instanceof Error ? error.message : "Invalid selected chips JSON.");
    }
  }

  return (
    <section className="panel">
      <h2>Search Debug</h2>
      <div className="stack">
        <label>
          Search text
          <input value={text} onChange={(event) => setText(event.target.value)} placeholder="free text query" />
        </label>
        <label>
          Selected chips JSON
          <textarea
            value={selectedJson}
            onChange={(event) => setSelectedJson(event.target.value)}
            rows={5}
            placeholder='[{"type":"ingredient_query","value":"cottage cheese"}]'
          />
        </label>
        {parseError ? <p role="alert" className="form-error">{parseError}</p> : null}
        <button type="button" onClick={runExplain}>
          Explain search
        </button>

        {explainQuery.isLoading ? <p>Loading search explanation...</p> : null}
        {explainQuery.error ? <p role="alert">{explainQuery.error.message}</p> : null}
        {explainQuery.data ? (
          <article className="debug-card">
            <header className="debug-card__header">
              <div>
                <h3>Search explanation</h3>
                <p>
                  query provider {explainQuery.data.provider ?? "-"} - query model {explainQuery.data.model ?? "-"}
                </p>
              </div>
              <div>
                <span>candidates {explainQuery.data.candidateCount}</span>
                <span>returned {explainQuery.data.returnedCount}</span>
              </div>
            </header>
            <dl className="debug-grid">
              <div>
                <dt>Text present</dt>
                <dd>{String(explainQuery.data.textPresent)}</dd>
              </div>
              <div>
                <dt>Distance metric</dt>
                <dd>{explainQuery.data.distanceMetric}</dd>
              </div>
              <div>
                <dt>Filters</dt>
                <dd>{JSON.stringify(explainQuery.data.filters)}</dd>
              </div>
            </dl>
            <div className="stack">
              {explainQuery.data.items.map((item) => (
                <article key={item.id} className="debug-card search-candidate-card">
                  <header className="debug-card__header search-candidate-card__header">
                    <div className="search-candidate-card__title">
                      <h4>{item.title}</h4>
                    </div>
                    <div className="actions-row">
                      {item.canOpenRecipe ? (
                        <button type="button" onClick={() => onOpenRecipe(item.id)}>
                          Open recipe
                        </button>
                      ) : null}
                    </div>
                  </header>
                  <div className="search-candidate-card__body">
                    <dl className="debug-grid">
                      <div>
                        <dt>rank</dt>
                        <dd>{formatNumber(item.debug.rank)}</dd>
                      </div>
                      <div>
                        <dt>recipe_id</dt>
                        <dd>{item.id}</dd>
                      </div>
                      <div>
                        <dt>distance</dt>
                        <dd>{formatNumber(item.debug.distance)}</dd>
                      </div>
                      <div>
                        <dt>similarity</dt>
                        <dd>{formatNumber(item.debug.similarity)}</dd>
                      </div>
                      <div>
                        <dt>embedding_status</dt>
                        <dd>{item.debug.embeddingStatus ?? "-"}</dd>
                      </div>
                      <div>
                        <dt>embedding_model</dt>
                        <dd>{item.debug.embeddingModel ?? "-"}</dd>
                      </div>
                      <div>
                        <dt>input_hash</dt>
                        <dd>{shortHash(item.debug.inputHash)}</dd>
                      </div>
                    </dl>
                    <h5>match_reasons</h5>
                    <pre>{JSON.stringify(item.matchReasons, null, 2)}</pre>
                    <h5>embedding_input preview</h5>
                    <pre>{item.debug.embeddingInputPreview ?? "-"}</pre>
                  </div>
                </article>
              ))}
            </div>
          </article>
        ) : null}

      </div>
    </section>
  );
}
