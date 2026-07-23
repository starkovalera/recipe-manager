(function () {
  const root = document.querySelector('#prototype-root');
  const layerRoot = document.querySelector('#layer-root');
  const live = document.querySelector('#live-region');
  const toolbar = document.querySelector('.prototype-toolbar');
  const scenarioSelect = document.querySelector('#scenario-select');
  const viewSelect = document.querySelector('#view-select');
  const roleSelect = document.querySelector('#role-select');

  const state = {
    scenario: 'normal', view: 'default', role: 'user', layer: null,
    layerTrigger: null, defaultScroll: 0, servingsScale: 1,
    checkedIngredients: new Set(), completedSteps: new Set(), mobileFocusTab: 'ingredients',
    mediaExpanded: false, resourceError: false
  };

  const esc = value => String(value ?? '').replace(/[&<>"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[char]));
  const current = () => window.prototypeScenarios[state.scenario];
  const announce = message => { live.textContent = ''; requestAnimationFrame(() => { live.textContent = message; }); };

  function setView(view, options) {
    if (state.view === 'default') state.defaultScroll = window.scrollY;
    state.view = view;
    viewSelect.value = view;
    closeLayer(false);
    renderCurrentState();
    const restore = options && options.restoreDefault;
    requestAnimationFrame(() => window.scrollTo(0, restore ? state.defaultScroll : 0));
    root.focus({ preventScroll: true });
  }

  function renderStatePanel(scenario) {
    if (scenario.state === 'loading') {
      return `<section class="state-panel" aria-busy="true"><h1>Loading recipe</h1><p>Preparing saved recipe details…</p><div class="loading-line"></div><div class="loading-line"></div><div class="loading-line"></div></section>`;
    }
    const missing = scenario.state === 'missing';
    return `<section class="state-panel" role="alert"><h1>${missing ? 'Recipe not found' : 'Recipe failed to load'}</h1><p>${esc(scenario.message)}</p><button type="button" data-action="retry">${missing ? 'Return to recipes' : 'Try again'}</button></section>`;
  }

  function visibleMeta(kind, values) {
    if (!values || !values.length) return `<span class="empty-inline">None</span>`;
    const visible = values.slice(0, 2).map(value => `<span>${esc(value)}</span>`).join('<span aria-hidden="true">·</span>');
    const remaining = values.length - 2;
    const more = remaining > 0 ? `<button type="button" class="link-button" data-disclosure="${kind}" aria-haspopup="dialog" aria-expanded="false">+${remaining} more ${kind}</button>` : '';
    return `${visible}${more}`;
  }

  function recipeHeaderPrimary(recipe) {
    const importedMeta = recipe.imported ? `${esc(recipe.source)} <span aria-hidden="true">·</span> ${esc(recipe.author)} <span aria-hidden="true">·</span> ` : '';
    const importAction = recipe.imported ? `<button type="button" data-action="import">Import info</button>` : '';
    return `<div class="cover ${recipe.cover ? 'has-cover' : ''}" role="img" aria-label="${recipe.cover ? 'Recipe cover placeholder' : 'No cover available'}">${recipe.cover ? 'Recipe cover' : 'No cover available'}</div>
      <header class="identity">
        <h1>${esc(recipe.title)}</h1>
        <p class="primary-meta">${importedMeta}${esc(recipe.time)} <span aria-hidden="true">·</span> ${esc(recipe.servings)} servings</p>
        <div class="actions" aria-label="Recipe actions">
          <button type="button" class="primary" data-action="cooking">Cook / Focus</button>
          <button type="button" data-action="edit">Edit</button>
          ${importAction}
          <button type="button" aria-label="More recipe actions" data-action="overflow">•••</button>
        </div>
      </header>`;
  }

  function secondaryMetadata(recipe) {
    return `<aside class="secondary-meta" aria-label="Recipe organization metadata">
        <div class="meta-row"><span class="meta-label">Difficulty · Personal rating</span><div class="meta-values"><span>${esc(recipe.difficulty)}</span><span aria-hidden="true">·</span><span>${esc(recipe.rating)}</span></div></div>
        <div class="meta-row"><span class="meta-label">Collections</span><div class="meta-values">${visibleMeta('collections', recipe.collections)}</div></div>
        <div class="meta-row"><span class="meta-label">Tags</span><div class="meta-values">${visibleMeta('tags', recipe.tags)}</div></div>
      </aside>`;
  }

  function reviewStatus(recipe) {
    if (!recipe.flags || !recipe.flags.length) return '';
    return `<section class="review-status" aria-labelledby="review-status-title">
      <div><strong id="review-status-title">${recipe.flags.length} imported details need review</strong><span>Some details may be uncertain; the recipe remains available.</span></div>
      <button type="button" class="link-button" data-action="import">Review import</button>
    </section>`;
  }

  function nutrition(recipe) {
    const nutrition = recipe.nutrition;
    return `<section class="recipe-section" aria-labelledby="nutrition-title"><h2 id="nutrition-title">Estimated nutrition</h2><p class="meta-label">${esc(nutrition.label)}</p>${nutrition.values.length ? `<div class="nutrition-values">${nutrition.values.map(value => `<span>${esc(value)}</span>`).join('')}</div>` : '<p class="empty-inline">No nutrition estimate is available.</p>'}</section>`;
  }

  function renderDefaultView(scenario) {
    const recipe = scenario.recipe;
    return `<div class="context-bar"><span>Default Recipe View</span><span>Reading and usage context</span></div>
      <div class="header-zone">${recipeHeaderPrimary(recipe)}${reviewStatus(recipe)}${secondaryMetadata(recipe)}</div>
      <div class="recipe-content">
        <div class="ingredients-column"><section class="recipe-section" aria-labelledby="ingredients-title"><h2 id="ingredients-title">Ingredients <span class="meta-label">${recipe.ingredients.length} items</span></h2><ul class="plain-list">${recipe.ingredients.map(item => `<li>${esc(item)}</li>`).join('')}</ul></section>${nutrition(recipe)}</div>
        <div class="instructions-column"><section class="recipe-section" aria-labelledby="instructions-title"><h2 id="instructions-title">Instructions <span class="meta-label">${recipe.steps.length} steps</span></h2><ol class="steps">${recipe.steps.map(step => `<li>${esc(step)}</li>`).join('')}</ol></section><section class="recipe-section" aria-labelledby="notes-title"><h2 id="notes-title">Cooking notes</h2><div class="notes">${esc(recipe.notes)}</div></section></div>
      </div>`;
  }

  function renderImportInfo(scenario) {
    if (!scenario.recipe || !scenario.recipe.imported || !scenario.importInfo) {
      return `<section class="state-panel"><h1>Import Info unavailable</h1><p>This manual recipe has no imported materials.</p><button type="button" data-action="back-default">Return to recipe</button></section>`;
    }
    const recipe = scenario.recipe;
    const info = scenario.importInfo;
    const flags = recipe.flags || [];
    const evidenceItems = (items, action) => items.map(item => `<div class="evidence-item"><span>${esc(item)}</span>${action ? ` <button type="button" class="link-button" data-action="${action}">${action === 'restore' ? 'Restore' : 'Retry'}</button>` : ''}</div>`).join('');
    return `<div class="context-bar"><span>Import Info</span><span>Review and provenance context</span></div>
      <header class="import-heading"><div><h1>Review imported recipe</h1><p>${esc(recipe.title)}</p></div><button type="button" data-action="back-default">View recipe</button></header>
      <div class="import-grid">
        <section class="result-pane" aria-labelledby="result-title"><h2 id="result-title">Extracted result</h2><h3>Ingredients</h3><ul class="plain-list">${recipe.ingredients.slice(0, 12).map(item => `<li>${esc(item)}</li>`).join('')}</ul><h3>Instructions</h3><ol class="steps">${recipe.steps.slice(0, 8).map(step => `<li>${esc(step)}</li>`).join('')}</ol></section>
        <aside class="evidence-pane" aria-label="Review and sources">
          <section class="evidence-group"><h2>Review needed · ${flags.length}</h2>${flags.length ? flags.map(flag => `<div class="evidence-item"><strong>${esc(flag.title)}</strong><span>${esc(flag.detail)}</span></div>`).join('') : '<p class="empty-inline">No unresolved review items.</p>'}</section>
          <section class="evidence-group"><h2>Sources used</h2>${evidenceItems(info.used)}</section>
          <section class="evidence-group"><h2>Sources ignored</h2>${evidenceItems(info.ignored)}</section>
          <section class="evidence-group"><h2>Deleted and restorable</h2>${evidenceItems(info.deleted, 'restore')}${state.resourceError ? '<p role="alert" class="empty-inline">Restore failed. The source is unchanged; try again.</p>' : ''}</section>
          <section class="evidence-group"><h2>Provenance</h2><p>${esc(info.provenance)}</p><p><strong>Original source:</strong> ${esc(info.sourceUrl)}</p></section>
          ${state.role === 'debug' ? `<section class="evidence-group"><h2>Eligible debug detail</h2><p class="debug-detail">${esc(info.debug)}</p></section>` : ''}
        </aside>
      </div>`;
  }

  function focusList(items, type) {
    const selected = type === 'ingredient' ? state.checkedIngredients : state.completedSteps;
    return `<ul class="check-list">${items.map((item, index) => `<li><label><input type="checkbox" data-check="${type}" data-index="${index}" ${selected.has(index) ? 'checked' : ''}><span>${type === 'step' ? `${index + 1}. ` : ''}${esc(item)}</span></label></li>`).join('')}</ul>`;
  }

  function renderCookingFocus(scenario) {
    if (!scenario.recipe) return renderStatePanel(scenario);
    const recipe = scenario.recipe;
    const scaled = Math.max(1, Math.round(recipe.servings * state.servingsScale));
    return `<div class="focus-shell"><div class="context-bar"><span>Cooking Focus</span><span>Temporary checks reset when this prototype reloads</span></div>
      <header class="focus-heading"><div><h1>${esc(recipe.title)}</h1><p>${scaled} servings · ${esc(recipe.time)}</p></div><div class="focus-actions"><div class="scale-control" aria-label="Portion scaling"><button type="button" data-action="scale-down" aria-label="Decrease portions">−</button><strong>${state.servingsScale}×</strong><button type="button" data-action="scale-up" aria-label="Increase portions">+</button></div>${scenario.mediaAvailable ? `<button type="button" data-action="media">Media · ${scenario.media.length}</button>` : '<span class="empty-inline">Media unavailable</span>'}<button type="button" data-action="back-default">Exit focus</button></div></header>
      <div class="mobile-tabs" role="tablist" aria-label="Cooking content"><button type="button" role="tab" aria-selected="${state.mobileFocusTab === 'ingredients'}" data-focus-tab="ingredients">Ingredients</button><button type="button" role="tab" aria-selected="${state.mobileFocusTab === 'instructions'}" data-focus-tab="instructions">Instructions</button></div>
      <div class="recipe-content"><section class="ingredients-column focus-panel" data-focus-panel="ingredients" ${state.mobileFocusTab !== 'ingredients' ? 'data-mobile-hidden="true"' : ''}><h2>Ingredients</h2>${focusList(recipe.ingredients, 'ingredient')}</section><section class="instructions-column focus-panel" data-focus-panel="instructions" ${state.mobileFocusTab !== 'instructions' ? 'data-mobile-hidden="true"' : ''}><h2>Instructions</h2>${focusList(recipe.steps, 'step')}<section class="recipe-section"><h2>Cooking notes</h2><div class="notes">${esc(recipe.notes)}</div></section></section></div>
    </div>`;
  }

  function renderCurrentState() {
    const scenario = current();
    roleSelect.value = state.role;
    scenarioSelect.value = state.scenario;
    viewSelect.value = state.view;
    if (scenario.state !== 'ready') root.innerHTML = renderStatePanel(scenario);
    else if (state.view === 'import') root.innerHTML = renderImportInfo(scenario);
    else if (state.view === 'cooking') root.innerHTML = renderCookingFocus(scenario);
    else root.innerHTML = renderDefaultView(scenario);
  }

  function openDisclosure(kind, trigger) {
    const recipe = current().recipe;
    const values = recipe[kind] || [];
    state.layer = { type: 'disclosure', kind };
    state.layerTrigger = trigger;
    trigger.setAttribute('aria-expanded', 'true');
    root.inert = true;
    toolbar.inert = true;
    layerRoot.innerHTML = `<div class="layer-backdrop" data-action="close-layer"></div><section class="layer popover" role="dialog" aria-modal="true" aria-labelledby="layer-title"><div class="layer-heading"><div><h2 id="layer-title">All ${esc(kind)}</h2><span class="meta-label">${values.length} items · inspection only</span></div><button type="button" data-action="close-layer">Close</button></div><ul class="plain-list">${values.map(value => `<li>${esc(value)}</li>`).join('')}</ul><p><button type="button" data-action="organize">Open Organize Recipe</button></p></section>`;
    layerRoot.querySelector('[data-action="close-layer"]').focus();
  }

  function openMedia(trigger) {
    state.layer = { type: 'media' };
    state.layerTrigger = trigger;
    document.body.classList.add('media-open');
    const media = current().media;
    const mobileSheet = window.matchMedia('(max-width: 760px)').matches;
    root.inert = mobileSheet;
    toolbar.inert = mobileSheet;
    layerRoot.innerHTML = `<div class="layer-backdrop media-layer-backdrop" data-action="close-layer"></div><aside class="layer drawer" role="dialog" aria-modal="${mobileSheet}" aria-labelledby="media-title"><div class="layer-heading"><div><h2 id="media-title">Cooking media · ${media.length}</h2><span class="meta-label">Supplementary reference</span></div><div><button type="button" data-action="expand-media">${state.mediaExpanded ? 'Compact' : 'Expand'}</button> <button type="button" data-action="close-layer">Close</button></div></div>${media.map(item => `<article class="media-item"><div class="media-placeholder" role="img" aria-label="Placeholder for ${esc(item.title)}">Image reference</div><strong>${esc(item.title)}</strong><div class="meta-label">${esc(item.origin)} · ${esc(item.author)}${item.current ? ' · Current cover' : ''}</div><button type="button" class="link-button">Open original source</button></article>`).join('')}</aside>`;
    layerRoot.querySelector('[data-action="close-layer"]').focus();
  }

  function closeLayer(returnFocus = true) {
    if (!state.layer) return;
    const trigger = state.layerTrigger;
    state.layer = null;
    state.layerTrigger = null;
    document.body.classList.remove('media-open');
    root.inert = false;
    toolbar.inert = false;
    layerRoot.innerHTML = '';
    if (returnFocus && trigger && document.contains(trigger)) {
      trigger.setAttribute('aria-expanded', 'false');
      trigger.focus();
    }
  }

  root.addEventListener('click', event => {
    const disclosure = event.target.closest('[data-disclosure]');
    if (disclosure) return openDisclosure(disclosure.dataset.disclosure, disclosure);
    const tab = event.target.closest('[data-focus-tab]');
    if (tab) { state.mobileFocusTab = tab.dataset.focusTab; renderCurrentState(); announce(`${state.mobileFocusTab} shown`); return; }
    const action = event.target.closest('[data-action]')?.dataset.action;
    if (!action) return;
    if (action === 'import') setView('import');
    else if (action === 'cooking') setView('cooking');
    else if (action === 'back-default') setView('default', { restoreDefault: true });
    else if (action === 'media') openMedia(event.target.closest('button'));
    else if (action === 'scale-up') { state.servingsScale = Math.min(4, state.servingsScale + .5); renderCurrentState(); }
    else if (action === 'scale-down') { state.servingsScale = Math.max(.5, state.servingsScale - .5); renderCurrentState(); }
    else if (action === 'restore') { state.resourceError = !state.resourceError; renderCurrentState(); announce(state.resourceError ? 'Restore failed' : 'Source restored'); }
    else if (action === 'retry') { state.scenario = 'normal'; scenarioSelect.value = 'normal'; renderCurrentState(); }
    else announce(`${action} is outside this structure-validation prototype`);
  });

  root.addEventListener('change', event => {
    const control = event.target.closest('[data-check]');
    if (!control) return;
    const set = control.dataset.check === 'ingredient' ? state.checkedIngredients : state.completedSteps;
    const index = Number(control.dataset.index);
    control.checked ? set.add(index) : set.delete(index);
    announce(control.checked ? 'Marked complete' : 'Marked incomplete');
  });

  layerRoot.addEventListener('click', event => {
    const action = event.target.closest('[data-action]')?.dataset.action;
    if (action === 'close-layer') closeLayer();
    else if (action === 'expand-media') { state.mediaExpanded = !state.mediaExpanded; openMedia(state.layerTrigger); announce(state.mediaExpanded ? 'Media expanded' : 'Media compact'); }
    else if (action === 'organize') announce('Organize Recipe is a separate context outside this prototype iteration');
  });

  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && state.layer) { closeLayer(); return; }
    const modal = layerRoot.querySelector('[role="dialog"][aria-modal="true"]');
    if (!modal || event.key !== 'Tab') return;
    const focusable = [...modal.querySelectorAll('button, [href], select, input, [tabindex]:not([tabindex="-1"])')].filter(node => !node.disabled);
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });
  scenarioSelect.addEventListener('change', () => {
    state.scenario = scenarioSelect.value;
    state.view = 'default'; viewSelect.value = 'default';
    state.checkedIngredients.clear(); state.completedSteps.clear(); state.resourceError = false;
    renderCurrentState(); window.scrollTo(0, 0);
  });
  viewSelect.addEventListener('change', () => setView(viewSelect.value));
  roleSelect.addEventListener('change', () => { state.role = roleSelect.value; renderCurrentState(); });

  renderCurrentState();
}());
