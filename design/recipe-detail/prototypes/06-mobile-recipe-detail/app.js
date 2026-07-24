const state = {
  scenario: 'normal', context: 'default', role: 'user', deleteResult: 'success',
  layer: null, layerTrigger: null, defaultScroll: 0, focusTab: 'ingredients',
  expanded: { ingredients: false, instructions: false, notes: false },
  selectedMedia: 0, reviewed: new Set(), removedIds: new Set(), removedItems: [],
  pending: null, panelScroll: { media: 0, import: 0 }, sheetGesture: null,
  destination: null
};

const prototypeRoot = document.querySelector('#prototype-root');
const layerRoot = document.querySelector('#layer-root');
const scenarioSelect = document.querySelector('#scenario-select');
const contextSelect = document.querySelector('#context-select');
const roleSelect = document.querySelector('#role-select');
const deleteResultSelect = document.querySelector('#delete-result-select');

function currentScenario() { return window.mobileRecipeScenarios[state.scenario]; }
function renderLayer() { layerRoot.replaceChildren(); }

function renderHeader(recipe) {
  const cover = recipe.cover
    ? `<img class="recipe-cover" src="${recipe.coverImage}" alt="${recipe.title}">`
    : '<div class="recipe-cover recipe-cover--empty" role="img" aria-label="No cover image available"><span>No cover image</span></div>';
  const sourceIdentity = recipe.source || recipe.author
    ? `<p class="source-identity">${[recipe.source, recipe.author].filter(Boolean).join(' <span aria-hidden="true">·</span> ')}</p>`
    : '';

  return `<header class="recipe-header">
    <div class="recipe-summary">
      ${cover}
      <div class="recipe-title-block">
        <h1>${recipe.title}</h1>
        ${sourceIdentity}
        <p class="cooking-facts"><span>${recipe.time}</span><span aria-hidden="true">·</span><span>Serves ${recipe.servings}</span></p>
      </div>
    </div>
  </header>`;
}

function renderMainActions(activeContext) {
  const scenario = currentScenario();
  const mediaAction = scenario.mediaAvailable
    ? `<button type="button" data-action="media">Media · ${scenario.media.length}</button>`
    : '';
  const importAction = scenario.importInfo
    ? '<button type="button" data-action="import">Import info</button>'
    : '';

  return `<div class="recipe-actions">
    <nav class="mode-actions" aria-label="Recipe mode">
      <button type="button" data-context="default"${activeContext === 'default' ? ' aria-current="page"' : ''}>View</button>
      <button type="button" data-context="focus"${activeContext === 'focus' ? ' aria-current="page"' : ''}>Focus</button>
      <button type="button" data-action="edit-status">Edit</button>
    </nav>
    <div class="resource-actions" aria-label="Recipe resources">
      ${mediaAction}
      ${importAction}
      <button type="button" data-action="overflow" aria-label="More recipe actions">…</button>
    </div>
  </div>`;
}

function visibleMetadata(values, key, limit = 2) {
  if (!values.length) return '';
  const visible = values.slice(0, limit).map(value => `<span>${value}</span>`).join('');
  const remaining = values.length - limit;
  const disclosure = remaining > 0
    ? `<button type="button" data-disclosure="${key}" aria-label="Show all ${values.length} ${key}">+${remaining}</button>`
    : '';
  return `<div class="metadata-values">${visible}${disclosure}</div>`;
}

function renderMetadata(recipe) {
  return `<section class="secondary-metadata" aria-label="Recipe metadata">
    <div class="metadata-row" data-metadata="difficulty-rating">
      <span class="metadata-label">Difficulty</span>
      <div class="metadata-values"><span>${recipe.difficulty}</span><span>Personal rating ${recipe.rating}</span></div>
    </div>
    <div class="metadata-row" data-metadata="collections">
      <span class="metadata-label">Collections</span>
      ${visibleMetadata(recipe.collections, 'collections')}
    </div>
    <div class="metadata-row" data-metadata="tags">
      <span class="metadata-label">Tags</span>
      ${visibleMetadata(recipe.tags, 'tags')}
    </div>
  </section>`;
}

function renderReviewStatus(recipe) {
  if (!recipe.flags || state.reviewed.has(state.scenario)) return '';
  const count = recipe.flags.length;
  return `<aside class="review-status" aria-label="Import review status">
    <span>${count} messages need review</span>
    <button type="button" data-action="import">Review import</button>
  </aside>`;
}

function renderExpandableSection({ key, title, items, threshold, ordered = false, itemTemplate, forceToggle = false, collapseCount = threshold }) {
  const expanded = state.expanded[key];
  const visibleItems = expanded ? items : items.slice(0, threshold);
  const listTag = ordered ? 'ol' : 'ul';
  const list = visibleItems.length
    ? `<${listTag} class="section-list">${visibleItems.map(itemTemplate).join('')}</${listTag}>`
    : '';
  const shouldToggle = forceToggle || items.length > threshold;
  const control = shouldToggle
    ? `<button type="button" class="section-toggle" data-expand="${key}">${expanded ? `Show first ${collapseCount}` : `Show all ${items.length}`}</button>`
    : '';
  return `<section class="recipe-section" data-section="${key}">
    <div class="section-heading"><h2>${title}</h2>${control}</div>
    ${list}
  </section>`;
}

function renderNutrition(nutrition) {
  const values = nutrition.values.length
    ? `<ul>${nutrition.values.map(value => `<li>${value}</li>`).join('')}</ul>`
    : '';
  return `<section class="recipe-section nutrition" data-section="nutrition">
    <h2>Estimated Nutrition</h2>
    <p>${nutrition.label}</p>
    ${values}
  </section>`;
}

function renderDefault(recipe) {
  const noteLineEstimate = Math.max(5, recipe.notes.split(/\s+/).length / 8 | 0);
  const ingredients = renderExpandableSection({
    key: 'ingredients', title: 'Ingredients', items: recipe.ingredients, threshold: 12,
    itemTemplate: item => `<li>${item}</li>`
  });
  const instructions = renderExpandableSection({
    key: 'instructions', title: 'Instructions', items: recipe.steps, threshold: 8, ordered: true,
    itemTemplate: item => `<li>${item}</li>`
  });
  const notes = renderExpandableSection({
    key: 'notes', title: 'Cooking Notes', items: [recipe.notes], threshold: 1, forceToggle: true, collapseCount: 4,
    itemTemplate: note => `<li class="section-preview${state.expanded.notes ? ' is-expanded' : ''}">${note.split('\n\n').map(paragraph => `<p>${paragraph}</p>`).join('')}</li>`
  }).replace(`Show all 1`, `Show all ${noteLineEstimate}`);

  return `<article class="product-surface recipe-detail" data-product-surface>
    ${renderHeader(recipe)}
    ${renderMainActions('default')}
    ${renderReviewStatus(recipe)}
    ${renderMetadata(recipe)}
    <main class="recipe-reading-content">
      ${ingredients}
      ${instructions}
      ${renderNutrition(recipe.nutrition)}
      ${notes}
    </main>
  </article>`;
}

function renderDestination() {
  return `<section class="product-surface state-panel recipes-destination" data-product-surface>
    <p class="eyebrow">Recipe library</p><h1>Recipes</h1><p>You are back at the mock Recipes destination.</p>
  </section>`;
}

function renderStatePanel(scenario) {
  if (scenario.state === 'loading') {
    return '<section class="product-surface state-panel" data-product-surface aria-busy="true"><h1>Loading recipe</h1><p>Your recipe is being prepared.</p></section>';
  }
  if (scenario.state === 'missing') {
    return `<section class="product-surface state-panel" data-product-surface role="alert"><h1>Recipe not found</h1><p>${scenario.message}</p><button type="button" data-action="return-recipes">Return to recipes</button></section>`;
  }
  return `<section class="product-surface state-panel" data-product-surface role="alert"><h1>Recipe failed to load</h1><p>${scenario.message}</p><button type="button" data-action="try-again">Try again</button></section>`;
}

function render() {
  const scenario = currentScenario();
  prototypeRoot.innerHTML = state.destination === 'recipes'
    ? renderDestination()
    : scenario.state === 'ready'
      ? renderDefault(scenario.recipe)
      : renderStatePanel(scenario);
  renderLayer();
}

Object.entries(window.mobileRecipeScenarios).forEach(([key, scenario]) => {
  const option = document.createElement('option');
  option.value = key;
  option.textContent = key === 'noCover' ? 'No cover' : key[0].toUpperCase() + key.slice(1);
  option.dataset.state = scenario.state;
  scenarioSelect.append(option);
});
scenarioSelect.value = state.scenario;
contextSelect.value = state.context;
roleSelect.value = state.role;
deleteResultSelect.value = state.deleteResult;
scenarioSelect.addEventListener('change', event => {
  state.scenario = event.target.value;
  state.destination = null;
  state.expanded = { ingredients: false, instructions: false, notes: false };
  render();
});
contextSelect.addEventListener('change', event => { state.context = event.target.value; render(); });
roleSelect.addEventListener('change', event => { state.role = event.target.value; render(); });
deleteResultSelect.addEventListener('change', event => { state.deleteResult = event.target.value; });
prototypeRoot.addEventListener('click', event => {
  const action = event.target.closest('[data-action], [data-expand]');
  if (!action) return;
  if (action.dataset.expand) {
    const key = action.dataset.expand;
    state.expanded[key] = !state.expanded[key];
    render();
  } else if (action.dataset.action === 'try-again') {
    state.scenario = 'normal';
    scenarioSelect.value = state.scenario;
    render();
  } else if (action.dataset.action === 'return-recipes') {
    state.destination = 'recipes';
    render();
  }
});

window.mobileRecipePrototype = { getState: () => state };
render();
