const state = {
  scenario: 'normal', context: 'default', role: 'user', deleteResult: 'success',
  layer: null, layerTrigger: null, defaultScroll: 0, focusTab: 'ingredients',
  headerCompact: false,
  expanded: { ingredients: false, instructions: false, notes: false },
  selectedMedia: 0, reviewed: new Set(), removedIds: new Set(), removedItems: [],
  pending: null, panelScroll: { media: 0, import: 0, disclosure: 0 }, sheetGesture: null,
  destination: null, deleteError: false
};

const prototypeRoot = document.querySelector('#prototype-root');
const globalNavRoot = document.querySelector('#global-nav-root');
const layerRoot = document.querySelector('#layer-root');
const scenarioSelect = document.querySelector('#scenario-select');
const contextSelect = document.querySelector('#context-select');
const roleSelect = document.querySelector('#role-select');
const deleteResultSelect = document.querySelector('#delete-result-select');
const NOTES_PREVIEW_LINES = 4;
const ESTIMATED_WORDS_PER_LINE = 8;
const NOTES_PREVIEW_WORD_LIMIT = NOTES_PREVIEW_LINES * ESTIMATED_WORDS_PER_LINE;

function currentScenario() { return window.mobileRecipeScenarios[state.scenario]; }
function announce(message) { document.querySelector('#live-region').textContent = message; }
function hasUnreviewedFlags() {
  const flags = currentScenario().recipe?.flags || [];
  return flags.length > 0 && !state.reviewed.has(state.scenario);
}

function buttonLabelForResource(resource) { return `Remove ${resource.label}`; }

function renderSheetFrame(title, body, type) {
  return `<div class="sheet-backdrop" data-action="close-layer"></div>
    <section class="bottom-sheet" role="dialog" aria-modal="true" aria-labelledby="sheet-title" data-layer="${type}">
      <div class="sheet-handle" aria-hidden="true"></div>
      <header class="sheet-heading"><h2 id="sheet-title">${title}</h2><button type="button" data-action="close-layer" aria-label="Close">&times;</button></header>
      <div class="sheet-body" tabindex="-1">${body}</div>
    </section>`;
}

function renderAddSheet() {
  return renderSheetFrame('Add recipe', `<div class="add-choices">
    <button type="button" data-action="start-import"><span class="choice-icon" aria-hidden="true">&#8681;</span><span><strong>Import recipe</strong><small>Use a link, images, or text</small></span></button>
    <button type="button" data-action="start-manual"><span class="choice-icon" aria-hidden="true">+</span><span><strong>Create manually</strong><small>Start with an empty recipe</small></span></button>
  </div>`, 'add');
}

function renderMediaSheet() {
  const scenario = currentScenario();
  const media = scenario.media || [];
  const selected = media[state.selectedMedia] || media[0];
  if (!selected) return renderSheetFrame('Media', '<section class="empty-media"><h3>No media yet</h3><p>Add recipe images when storage capacity is available.</p><button type="button" data-action="manage-media-status">Manage media</button></section>', 'media');
  const thumbnails = media.map((item, index) => `<button type="button" class="media-thumbnail${index === state.selectedMedia ? ' is-selected' : ''}" data-action="select-media" data-media-index="${index}" aria-label="View ${item.title}" aria-pressed="${index === state.selectedMedia}"><img src="${item.preview}" alt=""></button>`).join('');
  const links = (scenario.mediaLinks || []).map(link => `<a class="external-media-link" href="${link.href}" target="_blank" rel="noreferrer">${link.title}</a>`).join('');
  return renderSheetFrame(`Media (${media.length})`, `<figure class="media-preview"><img src="${selected.preview}" alt="${selected.title}"><figcaption><strong>${selected.title}</strong><span>${selected.origin} · ${selected.author}</span>${selected.current ? '<em>Current cover</em>' : ''}</figcaption></figure><div class="media-thumbnails" aria-label="Media choices">${thumbnails}</div><div class="external-media-links">${links}</div>`, 'media');
}

function renderDisclosureSheet(key) {
  const recipe = currentScenario().recipe;
  const values = recipe[key] || [];
  const title = key === 'tags' ? 'All tags' : 'All collections';
  return renderSheetFrame(title, `<ul class="disclosure-list">${values.map(value => `<li>${value}</li>`).join('')}</ul>`, 'disclosure');
}

function resourceRow(resource, groupId) {
  if (state.removedIds.has(resource.id)) return '';
  if (state.pending && state.pending.type === 'resource' && state.pending.id === resource.id) {
    return `<div class="resource-confirmation" data-resource-id="${resource.id}"><strong>Remove this resource?</strong><p>This resource cannot be restored. Your saved recipe will not change.</p><div><button type="button" data-action="cancel-pending">Cancel</button><button type="button" class="destructive" data-action="confirm-resource" data-resource-id="${resource.id}" data-group-id="${groupId}">Remove resource</button></div></div>`;
  }
  const preview = resource.preview ? `<img class="resource-thumbnail" src="${resource.preview}" alt="">` : '';
  return `<div class="resource-row${preview ? '' : ' resource-row--no-preview'}" data-resource-id="${resource.id}">${preview}<div><small>${resource.type}</small><strong>${resource.label}</strong><span>${resource.currentCover ? 'Kept as cover' : resource.status}</span></div><button type="button" class="icon-button destructive-icon" data-action="remove-resource" data-resource-id="${resource.id}" data-group-id="${groupId}" aria-label="${buttonLabelForResource(resource)}">&#128465;</button></div>`;
}

function renderResourceGroup(group) {
  const children = (group.children || []).filter(child => !state.removedIds.has(child.id));
  const currentCover = children.find(child => child.currentCover);
  if (state.removedIds.has(group.id)) return currentCover ? `<section class="resource-group resource-group--retained"><h3>Current cover retained</h3>${resourceRow(currentCover, group.id)}</section>` : '';
  if (state.pending && state.pending.type === 'primary' && state.pending.id === group.id) {
    const affected = children.filter(child => !child.currentCover);
    const summary = affected.reduce((acc, child) => { acc[child.type] = (acc[child.type] || 0) + 1; return acc; }, {});
    const types = Object.entries(summary).map(([type, count]) => `${count} ${type.toLowerCase()}${count === 1 ? '' : 's'}`).join(' · ');
    return `<section class="resource-group primary-confirmation" data-resource-id="${group.id}"><strong>Remove this source?</strong><p>The source and ${affected.length} derived resources will be removed: ${types || 'no derived resources'}.</p>${currentCover ? '<p><strong>The current cover will be kept.</strong></p>' : ''}<p>Your saved recipe will not change.</p><div><button type="button" data-action="cancel-pending">Cancel</button><button type="button" class="destructive" data-action="confirm-primary" data-resource-id="${group.id}">Remove resources</button></div></section>`;
  }
  const used = children.filter(child => child.status !== 'Ignored').map(child => resourceRow(child, group.id)).join('');
  const ignored = children.filter(child => child.status === 'Ignored').map(child => resourceRow(child, group.id)).join('');
  return `<section class="resource-group" data-resource-group="${group.id}"><header><div><small>${group.type}</small><h3>${group.label}</h3><span>${group.status}</span></div><button type="button" class="icon-button destructive-icon" data-action="remove-primary" data-resource-id="${group.id}" aria-label="${buttonLabelForResource(group)}">&#128465;</button></header>${used ? `<div class="resource-children">${used}</div>` : ''}${ignored ? `<section class="ignored-resources"><h4>Ignored resources</h4>${ignored}</section>` : ''}</section>`;
}

function renderImportSheet() {
  const scenario = currentScenario();
  const info = scenario.importInfo;
  if (!info) return renderSheetFrame('Import info', '<p>There is no import information for this recipe.</p>', 'import');
  const flags = !state.reviewed.has(state.scenario) ? `<section class="import-flags"><h3>Review needed</h3>${info.flags.map(flag => `<p>${flag}</p>`).join('')}${state.pending && state.pending.type === 'flags' ? '<div class="inline-confirmation"><p>Mark all import messages as reviewed?</p><button type="button" data-action="cancel-pending">Cancel</button><button type="button" data-action="confirm-reviewed">Mark all reviewed</button></div>' : '<button type="button" data-action="mark-reviewed">Mark all reviewed</button>'}</section>` : '<p class="reviewed-copy">All import messages have been reviewed.</p>';
  const groups = info.groups.map(renderResourceGroup).join('');
  const removedCounts = state.removedItems.reduce((counts, item) => { counts[item.type] = (counts[item.type] || 0) + 1; return counts; }, {});
  const removedSummary = state.removedItems.length ? `<section class="removed-summary"><h3>Removed resources</h3><p>${Object.entries(removedCounts).map(([type, count]) => `${count} ${type.toLowerCase()}${count === 1 ? '' : 's'}`).join(' · ')}</p></section>` : '';
  const debug = state.role === 'debug' ? `<details class="debug-details"><summary>Debug details</summary><p>${info.debug}</p></details>` : '';
  return renderSheetFrame('Import info', `${flags}<section class="resource-groups"><h3>Sources</h3>${groups}</section>${removedSummary}${debug}`, 'import');
}

function renderDeleteRecipeSheet() {
  const recipe = currentScenario().recipe;
  return `<div class="sheet-backdrop"></div><section class="bottom-sheet delete-recipe-sheet" role="dialog" aria-modal="true" aria-labelledby="delete-recipe-title" data-layer="delete-recipe"><div class="sheet-handle" aria-hidden="true"></div><header class="sheet-heading"><h2 id="delete-recipe-title">Delete ${recipe.title}?</h2><button type="button" data-action="close-layer" aria-label="Close">&times;</button></header><div class="sheet-body"><p>This cannot be undone. Associated imported files, images, and links will also be deleted.</p>${state.deleteError ? '<p class="delete-error" role="alert">Recipe couldn’t be deleted. Try again.</p>' : ''}<div class="sheet-actions"><button type="button" data-action="close-layer">Cancel</button><button type="button" class="destructive" data-action="confirm-delete-recipe">Delete recipe</button></div></div></section>`;
}

// Approved mobile navigation: modes lead the overflow sheet, Import Info is a
// separate administrative destination, and the persistent icon means Media only.
function renderOverflow() {
  const reviewNeeded = hasUnreviewedFlags();
  const importAction = currentScenario().importInfo
    ? `<button type="button" role="menuitem" data-action="import" aria-label="${reviewNeeded ? 'Import info, review needed' : 'Import info'}"><span>Import info</span>${reviewNeeded ? '<span class="notification-dot notification-dot--menu" aria-hidden="true"></span>' : ''}</button>`
    : '';
  return renderSheetFrame('Recipe actions', `<nav class="overflow-modes" aria-label="Recipe mode">
      <button type="button" data-context="default"${state.context === 'default' ? ' aria-current="page"' : ''}>View</button>
      <button type="button" data-context="focus"${state.context === 'focus' ? ' aria-current="page"' : ''}>Focus</button>
      <button type="button" data-action="edit-status">Edit</button>
    </nav>
    <div class="overflow-menu" role="menu">
      ${importAction}
      <button type="button" role="menuitem">Export recipe</button>
      <div class="menu-separator"></div>
      <button type="button" role="menuitem" class="destructive" data-action="delete-recipe">Delete recipe…</button>
    </div>`, 'overflow');
}

function renderLayer() {
  if (!state.layer) { layerRoot.replaceChildren(); return; }
  const type = state.layer.type;
  layerRoot.innerHTML = type === 'media' ? renderMediaSheet() : type === 'import' ? renderImportSheet() : type === 'disclosure' ? renderDisclosureSheet(state.layer.details) : type === 'overflow' ? renderOverflow() : type === 'add' ? renderAddSheet() : renderDeleteRecipeSheet();
}

function openLayer(type, trigger, details) {
  if (state.layer) closeLayer(false);
  state.layer = { type, details };
  state.layerTrigger = trigger || null;
  state.deleteError = false;
  globalNavRoot.inert = true;
  globalNavRoot.querySelector('nav')?.setAttribute('aria-hidden', 'true');
  if (type === 'delete-recipe') prototypeRoot.inert = true;
  renderLayer();
  requestAnimationFrame(() => {
    const body = layerRoot.querySelector('.sheet-body');
    if (body && type in state.panelScroll) body.scrollTop = state.panelScroll[type];
    const focusTarget = layerRoot.querySelector(type === 'delete-recipe' ? '.delete-recipe-sheet [data-action="confirm-delete-recipe"]' : '.bottom-sheet [data-action="close-layer"]') || layerRoot.querySelector('.bottom-sheet');
    if (focusTarget) focusTarget.focus();
  });
}

function closeLayer(returnFocus = true) {
  const sheet = layerRoot.querySelector('.bottom-sheet');
  if (sheet && state.layer && state.layer.type in state.panelScroll) state.panelScroll[state.layer.type] = sheet.querySelector('.sheet-body').scrollTop;
  state.pending = null;
  state.layer = null;
  state.deleteError = false;
  prototypeRoot.inert = false;
  globalNavRoot.inert = false;
  globalNavRoot.querySelector('nav')?.removeAttribute('aria-hidden');
  renderLayer();
  const returnTarget = state.layerTrigger;
  if (returnFocus && returnTarget) requestAnimationFrame(() => {
    if (returnTarget.isConnected) returnTarget.focus();
  });
}

function startSheetGesture(event) {
  const sheet = event.target.closest('.bottom-sheet');
  if (!sheet || state.layer?.type === 'delete-recipe' || !event.target.closest('.sheet-handle')) return;
  state.sheetGesture = { y: event.clientY, time: performance.now(), pointerId: event.pointerId };
}

function finishSheetGesture(event) {
  if (!state.sheetGesture) return;
  const gesture = state.sheetGesture;
  state.sheetGesture = null;
  const distance = event.clientY - gesture.y;
  const velocity = distance / Math.max(performance.now() - gesture.time, 1);
  if (distance >= 96 || velocity >= .65) closeLayer();
}

function setContext(context) {
  if (!['default', 'focus'].includes(context) || context === state.context) return;
  if (context === 'focus') state.defaultScroll = window.scrollY;
  state.context = context;
  contextSelect.value = context;
  render();
  if (context === 'focus') requestAnimationFrame(() => window.scrollTo(0, 0));
  if (context === 'default') requestAnimationFrame(() => window.scrollTo(0, state.defaultScroll));
}

function renderHeader(recipe, activeContext = 'default', focus = false) {
  const cover = focus ? '' : recipe.cover
    ? `<img class="recipe-cover" src="${recipe.coverImage}" alt="${recipe.title}">`
    : '<div class="recipe-cover recipe-cover--empty" role="img" aria-label="No cover image available"><span>No cover image</span></div>';
  const sourceIdentity = recipe.source || recipe.author
    ? `<p class="source-identity">${[recipe.source, recipe.author].filter(Boolean).join(' <span aria-hidden="true">·</span> ')}</p>`
    : '';

  const mediaAction = currentScenario().mediaAvailable
    ? `<button type="button" class="header-icon media-trigger" data-action="media" aria-label="Media, ${currentScenario().media.length} items"><span aria-hidden="true">▧</span><span class="media-count" aria-hidden="true">${currentScenario().media.length}</span></button>`
    : '';
  const reviewNeeded = hasUnreviewedFlags();

  return `<header class="mobile-header-shell${focus ? ' focus-mobile-header' : ''}${state.headerCompact ? ' is-compact' : ''}" data-mobile-header>
    <div class="mobile-utility-row">
      <button type="button" class="header-icon" data-action="back" aria-label="Back to recipes">←</button>
      <strong class="compact-recipe-title">${recipe.title}</strong>
      <div class="header-tools">${mediaAction}<button type="button" class="header-icon" data-action="overflow" aria-label="${reviewNeeded ? 'More recipe actions, import review needed' : 'More recipe actions'}">…${reviewNeeded ? '<span class="notification-dot notification-dot--header" aria-hidden="true"></span>' : ''}</button></div>
    </div>
    <div class="recipe-summary">
      ${cover}
      <div class="recipe-title-block">
        <h1>${recipe.title}</h1>
        ${focus ? '' : sourceIdentity}
        <p class="cooking-facts"><span>${recipe.time}</span><span aria-hidden="true">·</span><span>Serves ${recipe.servings}</span></p>
      </div>
    </div>
    <nav class="mode-actions" aria-label="Recipe mode">
      <button type="button" data-context="default"${activeContext === 'default' ? ' aria-current="page"' : ''}>View</button>
      <button type="button" data-context="focus"${activeContext === 'focus' ? ' aria-current="page"' : ''}>Focus</button>
      <button type="button" data-action="edit-status">Edit</button>
    </nav>
  </header>`;
}

function renderMainActions(activeContext) {
  const scenario = currentScenario();
  const mediaAction = scenario.mediaAvailable
    ? `<button type="button" class="utility-icon" data-action="media" aria-label="Media, ${scenario.media.length} items">▧<span class="media-count" aria-hidden="true">${scenario.media.length}</span></button>`
    : '';

  return `<div class="recipe-actions">
    <nav class="mode-actions" aria-label="Recipe mode">
      <button type="button" data-context="default"${activeContext === 'default' ? ' aria-current="page"' : ''}>View</button>
      <button type="button" data-context="focus"${activeContext === 'focus' ? ' aria-current="page"' : ''}>Focus</button>
      <button type="button" data-action="edit-status">Edit</button>
    </nav>
    <div class="resource-actions" aria-label="Recipe tools">
      ${mediaAction}
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
      <span class="metadata-label">Difficulty · rating</span>
      <div class="metadata-values"><span>${recipe.difficulty} · ${recipe.rating}</span></div>
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

function renderExpandableSection({ key, title, items, threshold, ordered = false, itemTemplate, forceToggle = false, collapseCount = threshold, disclosureCount = items.length }) {
  const expanded = state.expanded[key];
  const visibleItems = expanded ? items : items.slice(0, threshold);
  const listTag = ordered ? 'ol' : 'ul';
  const list = visibleItems.length
    ? `<${listTag} class="section-list">${visibleItems.map(itemTemplate).join('')}</${listTag}>`
    : '';
  const shouldToggle = forceToggle || items.length > threshold;
  const control = shouldToggle
    ? `<button type="button" class="section-toggle" data-expand="${key}">${expanded ? `Show first ${collapseCount}` : `Show all ${disclosureCount}`}</button>`
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
  const noteWordCount = recipe.notes.trim().split(/\s+/).length;
  const noteLineEstimate = Math.ceil(noteWordCount / ESTIMATED_WORDS_PER_LINE);
  const ingredients = renderExpandableSection({
    key: 'ingredients', title: 'Ingredients', items: recipe.ingredients, threshold: 12,
    itemTemplate: item => `<li>${item}</li>`
  });
  const instructions = renderExpandableSection({
    key: 'instructions', title: 'Instructions', items: recipe.steps, threshold: 8, ordered: true,
    itemTemplate: item => `<li>${item}</li>`
  });
  const notes = renderExpandableSection({
    key: 'notes', title: 'Cooking Notes', items: [recipe.notes], threshold: 1,
    forceToggle: noteWordCount > NOTES_PREVIEW_WORD_LIMIT, collapseCount: NOTES_PREVIEW_LINES, disclosureCount: noteLineEstimate,
    itemTemplate: note => `<li class="section-preview${state.expanded.notes ? ' is-expanded' : ''}">${note.split('\n\n').map(paragraph => `<p>${paragraph}</p>`).join('')}</li>`
  });

  return `<article class="product-surface recipe-detail" data-product-surface>
    ${renderHeader(recipe, 'default')}
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

function renderFocus(recipe) {
  const ingredientsSelected = state.focusTab === 'ingredients';
  const focusContent = ingredientsSelected
    ? `<section class="focus-content" data-focus-content="ingredients" role="tabpanel" id="focus-ingredients-panel" aria-labelledby="focus-ingredients-tab">
        <h2>Ingredients</h2>
        <ul class="section-list">${recipe.ingredients.map(item => `<li>${item}</li>`).join('')}</ul>
      </section>`
    : `<section class="focus-content" data-focus-content="instructions" role="tabpanel" id="focus-instructions-panel" aria-labelledby="focus-instructions-tab">
        <h2>Instructions</h2>
        <ol class="section-list">${recipe.steps.map(step => `<li>${step}</li>`).join('')}</ol>
        <section class="recipe-section focus-notes" data-section="notes"><h2>Cooking Notes</h2><p>${recipe.notes}</p></section>
      </section>`;

  return `<article class="product-surface recipe-detail focus-recipe" data-product-surface>
    ${renderHeader(recipe, 'focus', true)}
    <main class="focus-reading-content">
      <div class="focus-switch" role="tablist" aria-label="Focus section">
        <button type="button" role="tab" id="focus-ingredients-tab" data-focus-tab="ingredients" aria-controls="focus-ingredients-panel" aria-selected="${ingredientsSelected}">Ingredients</button>
        <button type="button" role="tab" id="focus-instructions-tab" data-focus-tab="instructions" aria-controls="focus-instructions-panel" aria-selected="${!ingredientsSelected}">Instructions</button>
      </div>
      ${focusContent}
    </main>
  </article>`;
}

function renderDestination() {
  if (state.destination === 'collections') return `<section class="product-surface state-panel" data-product-surface><p class="eyebrow">Recipe library</p><h1>Collections</h1><p>Browse and organize recipe collections.</p></section>`;
  if (state.destination === 'notifications') return `<section class="product-surface state-panel" data-product-surface><p class="eyebrow">Updates</p><h1>Notifications</h1><p>Import progress and recipe activity appear here.</p></section>`;
  if (state.destination === 'profile') return `<section class="product-surface state-panel profile-destination" data-product-surface><p class="eyebrow">Account</p><h1>Profile</h1><p>Account and application preferences.</p><div class="profile-actions"><button type="button">Preferences</button>${state.role === 'admin' ? '<button type="button" data-action="administration">Administration</button>' : ''}</div></section>`;
  if (state.destination === 'import-create' || state.destination === 'manual-create') {
    const importing = state.destination === 'import-create';
    return `<section class="product-surface state-panel creation-destination" data-product-surface><p class="eyebrow">Focused creation flow</p><h1>${importing ? 'Import recipe' : 'Create recipe manually'}</h1><p>${importing ? 'Choose a link, images, or text in the complete import flow.' : 'Begin with an empty recipe draft in the complete manual flow.'}</p><button type="button" data-action="close-create-flow">Cancel</button></section>`;
  }
  return `<section class="product-surface state-panel recipes-destination" data-product-surface><p class="eyebrow">Recipe library</p><h1>Recipes</h1><p>You are back at the mock Recipes destination.</p></section>`;
}

function renderGlobalNavigation() {
  if (state.destination === 'import-create' || state.destination === 'manual-create') {
    globalNavRoot.replaceChildren();
    return;
  }
  const current = ['collections', 'notifications', 'profile'].includes(state.destination) ? state.destination : 'recipes';
  globalNavRoot.innerHTML = `<nav class="global-navigation" aria-label="Main navigation">
    <button type="button" data-destination="recipes"${current === 'recipes' ? ' aria-current="page"' : ''}><span aria-hidden="true">&#9776;</span><span>Recipes</span></button>
    <button type="button" data-destination="collections"${current === 'collections' ? ' aria-current="page"' : ''}><span aria-hidden="true">&#9638;</span><span>Collections</span></button>
    <button type="button" class="global-add" data-action="add-recipe" aria-label="Add recipe"><span aria-hidden="true">+</span></button>
    <button type="button" data-destination="notifications"${current === 'notifications' ? ' aria-current="page"' : ''}><span class="nav-icon-with-badge" aria-hidden="true">&#9679;<small>3</small></span><span>Notifications</span></button>
    <button type="button" data-destination="profile"${current === 'profile' ? ' aria-current="page"' : ''}><span aria-hidden="true">&#9675;</span><span>Profile</span></button>
  </nav>`;
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

function syncMobileHeader() {
  const header = prototypeRoot.querySelector('[data-mobile-header]');
  if (!header) return;
  state.headerCompact = window.scrollY > 96;
  header.classList.toggle('is-compact', state.headerCompact);
}

function render() {
  const scenario = currentScenario();
  prototypeRoot.innerHTML = state.destination
    ? renderDestination()
    : scenario.state === 'ready'
      ? state.context === 'focus' ? renderFocus(scenario.recipe) : renderDefault(scenario.recipe)
      : renderStatePanel(scenario);
  renderGlobalNavigation();
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
  state.pending = null;
  closeLayer(false);
  render();
});
contextSelect.addEventListener('change', event => { setContext(event.target.value); });
roleSelect.addEventListener('change', event => { state.role = event.target.value; render(); });
deleteResultSelect.addEventListener('change', event => { state.deleteResult = event.target.value; });
prototypeRoot.addEventListener('click', event => {
  const action = event.target.closest('[data-action], [data-expand], [data-context], [data-focus-tab], [data-disclosure]');
  if (!action) return;
  if (action.dataset.context) {
    setContext(action.dataset.context);
  } else if (action.dataset.focusTab) {
    state.focusTab = action.dataset.focusTab;
    render();
  } else if (action.dataset.expand) {
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
  } else if (action.dataset.action === 'back') {
    state.destination = 'recipes';
    render();
    announce('Returned to recipes.');
  } else if (action.dataset.action === 'edit-status') {
    announce('Edit Mode is being designed.');
  } else if (action.dataset.action === 'media') {
    openLayer('media', action);
  } else if (action.dataset.action === 'import') {
    openLayer('import', action);
  } else if (action.dataset.action === 'overflow') {
    openLayer('overflow', action);
  } else if (action.dataset.action === 'close-create-flow') {
    state.destination = null;
    render();
  } else if (action.dataset.disclosure) {
    openLayer('disclosure', action, action.dataset.disclosure);
  }
});

globalNavRoot.addEventListener('click', event => {
  const control = event.target.closest('[data-destination], [data-action]');
  if (!control) return;
  if (control.dataset.action === 'add-recipe') {
    openLayer('add', control);
    return;
  }
  state.destination = control.dataset.destination === 'recipes' ? null : control.dataset.destination;
  window.scrollTo(0, 0);
  render();
});

layerRoot.addEventListener('click', event => {
  const action = event.target.closest('[data-action], [data-context]');
  if (!action) return;
  const type = state.layer?.type;
  if (action.dataset.context) {
    closeLayer(false);
    setContext(action.dataset.context);
  } else if (action.dataset.action === 'edit-status') {
    closeLayer();
    announce('Edit Mode is being designed.');
  } else if (action.dataset.action === 'import') {
    const trigger = state.layerTrigger;
    closeLayer(false);
    openLayer('import', trigger);
  } else if (action.dataset.action === 'close-layer') {
    closeLayer();
  } else if (action.dataset.action === 'start-import' || action.dataset.action === 'start-manual') {
    state.destination = action.dataset.action === 'start-import' ? 'import-create' : 'manual-create';
    closeLayer(false);
    render();
  } else if (action.dataset.action === 'select-media') {
    state.selectedMedia = Number(action.dataset.mediaIndex);
    renderLayer();
  } else if (action.dataset.action === 'manage-media-status') {
    announce('Manage Media is a separate editing workspace.');
  } else if (action.dataset.action === 'mark-reviewed') {
    state.pending = { type: 'flags' };
    renderLayer();
  } else if (action.dataset.action === 'confirm-reviewed') {
    state.reviewed.add(state.scenario);
    state.pending = null;
    render();
    announce('All import messages marked as reviewed.');
  } else if (action.dataset.action === 'remove-resource') {
    state.pending = { type: 'resource', id: action.dataset.resourceId, groupId: action.dataset.groupId };
    renderLayer();
  } else if (action.dataset.action === 'remove-primary') {
    state.pending = { type: 'primary', id: action.dataset.resourceId };
    renderLayer();
  } else if (action.dataset.action === 'cancel-pending') {
    state.pending = null;
    renderLayer();
  } else if (action.dataset.action === 'confirm-resource') {
    const info = currentScenario().importInfo;
    const group = info.groups.find(item => item.id === action.dataset.groupId);
    const resource = group?.children.find(item => item.id === action.dataset.resourceId);
    if (resource) { state.removedIds.add(resource.id); state.removedItems.push(resource); }
    state.pending = null;
    renderLayer();
    announce('Resource removed. Your saved recipe was not changed.');
  } else if (action.dataset.action === 'confirm-primary') {
    const group = currentScenario().importInfo.groups.find(item => item.id === action.dataset.resourceId);
    if (group) {
      state.removedIds.add(group.id);
      state.removedItems.push(group);
      group.children.filter(child => !child.currentCover).forEach(child => { state.removedIds.add(child.id); state.removedItems.push(child); });
    }
    state.pending = null;
    renderLayer();
    announce('Source resources removed. The saved recipe was not changed.');
  } else if (action.dataset.action === 'delete-recipe') {
    openLayer('delete-recipe', state.layerTrigger);
  } else if (action.dataset.action === 'confirm-delete-recipe') {
    if (state.deleteResult === 'failure') {
      state.deleteError = true;
      renderLayer();
      requestAnimationFrame(() => layerRoot.querySelector('[data-action="confirm-delete-recipe"]')?.focus());
    } else {
      state.destination = 'recipes';
      closeLayer(false);
      render();
      announce('Recipe deleted');
    }
  }
});

layerRoot.addEventListener('pointerdown', startSheetGesture);
layerRoot.addEventListener('pointerup', finishSheetGesture);
window.addEventListener('scroll', syncMobileHeader, { passive: true });
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && state.layer) {
    event.preventDefault();
    if (state.pending) { state.pending = null; renderLayer(); } else closeLayer();
  }
  if (event.key === 'Tab' && state.layer?.type === 'delete-recipe') {
    const focusables = [...layerRoot.querySelectorAll('button:not([disabled]), [href]')];
    if (!focusables.length) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }
});

window.mobileRecipePrototype = { getState: () => state };
render();
