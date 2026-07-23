(function () {
  const root = document.querySelector('#prototype-root');
  const layerRoot = document.querySelector('#layer-root');
  const live = document.querySelector('#live-region');
  const toolbar = document.querySelector('.prototype-toolbar');
  const scenarioSelect = document.querySelector('#scenario-select');
  const viewSelect = document.querySelector('#view-select');
  const roleSelect = document.querySelector('#role-select');
  const placementSelect = document.querySelector('#placement-select');

  const state = {
    scenario: 'flagged', view: 'default', role: 'user', placement: 'under-title',
    layer: null, layerTrigger: null, defaultScroll: 0, mobileFocusTab: 'ingredients',
    expanded: { ingredients: false, instructions: false, notes: false },
    flagsReviewed: new Set(), removedIds: new Set(), removedItems: [], removedExpanded: false,
    pending: null, message: '', mediaExpanded: false
  };

  const esc = value => String(value ?? '').replace(/[&<>"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[char]));
  const current = () => window.prototypeScenarios[state.scenario];
  const announce = message => { live.textContent = ''; requestAnimationFrame(() => { live.textContent = message; }); };
  const hasOpenFlags = recipe => Boolean(recipe.flags?.length && !state.flagsReviewed.has(state.scenario));

  function modeSwitch(active, imported) {
    const modes = [['default', 'View'], ['cooking', 'Focus'], ['edit', 'Edit']];
    return `<div class="action-cluster"><nav class="mode-switch" aria-label="Recipe mode">${modes.map(([value, label]) => `<button type="button" data-mode="${value}" ${active === value ? 'aria-current="page" disabled' : ''}>${label}</button>`).join('')}</nav>${imported ? '<button type="button" data-action="import">Import info</button>' : ''}<button type="button" aria-label="More recipe actions" data-action="overflow">•••</button></div>`;
  }

  function setView(view, options) {
    if (state.view === 'default') state.defaultScroll = window.scrollY;
    state.view = view;
    viewSelect.value = view;
    closeLayer(false);
    renderCurrentState();
    requestAnimationFrame(() => window.scrollTo(0, options?.restoreDefault ? state.defaultScroll : 0));
    root.focus({ preventScroll: true });
  }

  function renderStatePanel(scenario) {
    if (scenario.state === 'loading') return `<section class="state-panel" aria-busy="true"><h1>Loading recipe</h1><p>Preparing saved recipe details…</p><div class="loading-line"></div><div class="loading-line"></div></section>`;
    const missing = scenario.state === 'missing';
    return `<section class="state-panel" role="alert"><h1>${missing ? 'Recipe not found' : 'Recipe failed to load'}</h1><p>${esc(scenario.message)}</p><button type="button" data-action="retry">${missing ? 'Return to recipes' : 'Try again'}</button></section>`;
  }

  function visibleMeta(kind, values) {
    if (!values?.length) return '<span class="empty-inline">None</span>';
    const visible = values.slice(0, 2).map(value => `<span>${esc(value)}</span>`).join('<span aria-hidden="true">·</span>');
    const remaining = values.length - 2;
    return `${visible}${remaining > 0 ? `<button type="button" class="link-button" data-disclosure="${kind}" aria-haspopup="dialog" aria-expanded="false">+${remaining} more ${kind}</button>` : ''}`;
  }

  function reviewStatus(recipe) {
    if (!hasOpenFlags(recipe)) return '';
    return `<section class="review-status" aria-labelledby="review-status-title"><div><strong id="review-status-title">${recipe.flags.length} imported details need review</strong><span>Review the import messages, then edit the recipe or mark them reviewed.</span></div><button type="button" class="link-button" data-action="import">Review import</button></section>`;
  }

  function secondaryMetadata(recipe) {
    return `<aside class="secondary-meta" aria-label="Recipe organization metadata"><div class="meta-row"><span class="meta-label">Difficulty · Personal rating</span><div class="meta-values"><span>${esc(recipe.difficulty)}</span><span aria-hidden="true">·</span><span>${esc(recipe.rating)}</span></div></div><div class="meta-row"><span class="meta-label">Collections</span><div class="meta-values">${visibleMeta('collections', recipe.collections)}</div></div><div class="meta-row"><span class="meta-label">Tags</span><div class="meta-values">${visibleMeta('tags', recipe.tags)}</div></div></aside>`;
  }

  function defaultHeader(recipe) {
    const sourceRow = recipe.imported ? `<p class="source-meta">${esc(recipe.source)} <span aria-hidden="true">·</span> ${esc(recipe.author)}</p>` : '';
    const factsRow = `<p class="cooking-meta">${esc(recipe.time)} <span aria-hidden="true">·</span> ${esc(recipe.servings)} servings</p>`;
    const actions = modeSwitch('default', recipe.imported);
    return `<div class="header-zone placement-${state.placement}"><div class="cover-stack"><div class="cover ${recipe.cover ? 'has-cover' : ''}" role="img" aria-label="${recipe.cover ? 'Recipe cover placeholder' : 'No cover available'}">${recipe.cover ? 'Recipe cover' : 'No cover available'}</div>${state.placement === 'under-cover' ? actions : ''}</div><header class="identity"><h1>${esc(recipe.title)}</h1>${sourceRow}${factsRow}${state.placement === 'under-title' ? actions : ''}</header>${reviewStatus(recipe)}${secondaryMetadata(recipe)}</div>`;
  }

  function expandableList(items, kind, threshold, ordered) {
    const expanded = state.expanded[kind];
    const hasMore = items.length > threshold;
    const visible = hasMore && !expanded ? items.slice(0, threshold) : items;
    const tag = ordered ? 'ol' : 'ul';
    const className = ordered ? 'steps' : 'plain-list';
    return `<${tag} class="${className}">${visible.map(item => `<li>${esc(item)}</li>`).join('')}</${tag}>${hasMore ? `<button type="button" class="section-toggle" data-expand="${kind}" aria-expanded="${expanded}">${expanded ? `Show first ${threshold}` : `Show all ${items.length}`}</button>` : ''}`;
  }

  function notesSection(recipe) {
    const expanded = state.expanded.notes;
    const long = recipe.notes.length > 170 || recipe.notes.includes('\n\n');
    return `<section class="recipe-section" aria-labelledby="notes-title"><h2 id="notes-title">Cooking notes</h2><div class="notes ${long && !expanded ? 'notes-collapsed' : ''}">${esc(recipe.notes)}</div>${long ? `<button type="button" class="section-toggle" data-expand="notes" aria-expanded="${expanded}">${expanded ? 'Collapse note' : 'Show full note'}</button>` : ''}</section>`;
  }

  function nutrition(recipe) {
    const nutrition = recipe.nutrition;
    return `<section class="recipe-section" aria-labelledby="nutrition-title"><h2 id="nutrition-title">Estimated nutrition</h2><p class="meta-label">${esc(nutrition.label)}</p>${nutrition.values.length ? `<div class="nutrition-values">${nutrition.values.map(value => `<span>${esc(value)}</span>`).join('')}</div>` : '<p class="empty-inline">No nutrition estimate is available.</p>'}</section>`;
  }

  function renderDefaultView(scenario) {
    const recipe = scenario.recipe;
    return `<div class="context-bar"><span>Default Recipe View</span><span>Reading and usage context</span></div>${defaultHeader(recipe)}<div class="recipe-content"><div class="ingredients-column"><section class="recipe-section" aria-labelledby="ingredients-title"><h2 id="ingredients-title">Ingredients <span class="meta-label">${recipe.ingredients.length} items</span></h2>${expandableList(recipe.ingredients, 'ingredients', 12, false)}</section>${nutrition(recipe)}</div><div class="instructions-column"><section class="recipe-section" aria-labelledby="instructions-title"><h2 id="instructions-title">Instructions <span class="meta-label">${recipe.steps.length} steps</span></h2>${expandableList(recipe.steps, 'instructions', 8, true)}</section>${notesSection(recipe)}</div></div>`;
  }

  function renderCookingFocus(scenario) {
    const recipe = scenario.recipe;
    return `<div class="focus-shell"><div class="context-bar"><span>Cooking Focus</span><span>Simplified reading context</span></div><header class="focus-heading"><div><h1>${esc(recipe.title)}</h1><p>${esc(recipe.time)} · ${recipe.servings} servings</p></div><div class="focus-actions">${modeSwitch('cooking', recipe.imported)}${scenario.mediaAvailable ? `<button type="button" data-action="media">Media · ${scenario.media.length}</button>` : '<span class="empty-inline">Media unavailable</span>'}</div></header><div class="mobile-tabs" role="tablist" aria-label="Cooking content"><button type="button" role="tab" aria-selected="${state.mobileFocusTab === 'ingredients'}" data-focus-tab="ingredients">Ingredients</button><button type="button" role="tab" aria-selected="${state.mobileFocusTab === 'instructions'}" data-focus-tab="instructions">Instructions</button></div><div class="recipe-content"><section class="ingredients-column focus-panel" data-focus-panel="ingredients" ${state.mobileFocusTab !== 'ingredients' ? 'data-mobile-hidden="true"' : ''}><h2>Ingredients</h2><ul class="plain-list">${recipe.ingredients.map(item => `<li>${esc(item)}</li>`).join('')}</ul></section><section class="instructions-column focus-panel" data-focus-panel="instructions" ${state.mobileFocusTab !== 'instructions' ? 'data-mobile-hidden="true"' : ''}><h2>Instructions</h2><ol class="steps">${recipe.steps.map(step => `<li>${esc(step)}</li>`).join('')}</ol>${notesSection(recipe)}</section></div></div>`;
  }

  function renderEdit(scenario) {
    const recipe = scenario.recipe;
    return `<div class="context-bar"><span>Edit Recipe Content</span><span>Separate editing context</span></div><header class="edit-heading"><div><h1>Edit ${esc(recipe.title)}</h1><p>Structure placeholder for mode-transition evaluation.</p></div>${modeSwitch('edit', recipe.imported)}</header><section class="edit-placeholder"><h2>Recipe content</h2><p>Title, source/author, servings, time, Ingredients, Instructions, Notes, and Estimated Nutrition belong here. Organization and imported-resource management remain separate.</p><button type="button">Save changes</button></section>`;
  }

  function renderCurrentState() {
    const scenario = current();
    scenarioSelect.value = state.scenario; viewSelect.value = state.view; roleSelect.value = state.role; placementSelect.value = state.placement;
    if (scenario.state !== 'ready') root.innerHTML = renderStatePanel(scenario);
    else if (state.view === 'cooking') root.innerHTML = renderCookingFocus(scenario);
    else if (state.view === 'edit') root.innerHTML = renderEdit(scenario);
    else root.innerHTML = renderDefaultView(scenario);
  }

  function removedRecords(info) {
    return info.previouslyRemoved.concat(state.removedItems);
  }

  function countTypes(records) {
    const counts = records.reduce((map, item) => (map[item.type] = (map[item.type] || 0) + 1, map), {});
    return Object.entries(counts).map(([type, count]) => `${count} ${type.toLowerCase()}${count === 1 ? '' : 's'}`).join(' · ');
  }

  function activeChildren(group) {
    return group.children.filter(child => !state.removedIds.has(child.id));
  }

  function resourceGroup(group) {
    if (state.removedIds.has(group.id)) return '';
    const children = activeChildren(group);
    const counts = countTypes(children);
    return `<section class="resource-group" aria-labelledby="resource-${esc(group.id)}"><header class="resource-primary"><div><span class="resource-type">${esc(group.type)}</span><h3 id="resource-${esc(group.id)}">${esc(group.label)}</h3><p>${esc(group.detail)} · ${esc(group.status)}${children.length ? ` · ${children.length} derived (${esc(counts)})` : ''}</p></div><button type="button" class="remove-button" data-remove-primary="${esc(group.id)}" aria-label="Remove ${esc(group.label)}">Remove</button></header>${children.length ? `<div class="resource-children">${children.map(child => `<div class="resource-child"><div><span class="resource-type">${esc(child.type)}</span><strong>${esc(child.label)}</strong><span class="resource-status">${esc(child.status)}${child.currentCover ? ' · Current cover' : ''}</span></div>${child.currentCover ? '<span class="cover-lock">Kept as cover</span>' : `<button type="button" class="icon-remove" data-remove-child="${esc(child.id)}" data-type="${esc(child.type)}" data-label="${esc(child.label)}" aria-label="Remove ${esc(child.label)}">×</button>`}</div>`).join('')}</div>` : ''}</section>`;
  }

  function pendingConfirmation(info) {
    if (!state.pending) return '';
    if (state.pending.type === 'flags') return `<section class="inline-confirm" role="alertdialog" aria-labelledby="confirm-title"><h3 id="confirm-title">Mark all flags as reviewed?</h3><p>This removes ${info.flags.length} review messages. Recipe content and imported resources will not change.</p><div><button type="button" data-action="cancel-confirm">Cancel</button> <button type="button" class="primary" data-action="confirm-flags">Mark all reviewed</button></div></section>`;
    const group = info.groups.find(item => item.id === state.pending.groupId);
    const removed = activeChildren(group).filter(child => !child.currentCover);
    const coverKept = activeChildren(group).some(child => child.currentCover);
    const total = removed.length + 1;
    return `<section class="inline-confirm" role="alertdialog" aria-labelledby="confirm-title"><h3 id="confirm-title">Remove this ${esc(group.type.toLowerCase())}?</h3><p>The primary resource and ${removed.length} derived resources will be removed: ${esc(countTypes(removed)) || 'no derived resources'}.</p>${coverKept ? '<p><strong>The current cover will be kept.</strong></p>' : ''}<div><button type="button" data-action="cancel-confirm">Cancel</button> <button type="button" class="primary" data-action="confirm-primary">Remove ${total} resource${total === 1 ? '' : 's'}</button></div></section>`;
  }

  function importDrawer() {
    const scenario = current();
    const recipe = scenario.recipe;
    const info = scenario.importInfo;
    const records = removedRecords(info);
    const flagsOpen = hasOpenFlags(recipe);
    return `<aside class="layer drawer import-drawer" role="dialog" aria-modal="${window.innerWidth < 1200}" aria-labelledby="import-title"><div class="layer-heading"><div><h2 id="import-title">Import info</h2><span class="meta-label">Review messages and imported resources</span></div><button type="button" data-action="close-layer" aria-label="Close Import info">Close</button></div>${pendingConfirmation(info)}${state.message ? `<p class="drawer-message" role="status">${esc(state.message)}</p>` : ''}<section class="drawer-section flags-section"><div class="section-heading"><h3>Review needed · ${flagsOpen ? info.flags.length : 0}</h3>${flagsOpen ? '<button type="button" data-action="prepare-flags">Mark all reviewed</button>' : ''}</div>${flagsOpen ? `<ul class="flag-list">${info.flags.map(flag => `<li>${esc(flag)}</li>`).join('')}</ul><p class="helper-text">After reviewing these messages, edit the recipe or mark all reviewed to keep it as it is.</p><button type="button" data-action="edit-from-drawer">Edit recipe</button>` : '<p class="empty-inline">All import messages have been reviewed.</p>'}</section><section class="drawer-section"><h3>Imported resources</h3><p class="helper-text">Derived resources are grouped beneath the primary resource that produced them.</p>${info.groups.map(resourceGroup).join('') || '<p class="empty-inline">No active imported resources.</p>'}</section>${records.length ? `<section class="drawer-section removed-summary"><button type="button" class="summary-button" data-action="toggle-removed" aria-expanded="${state.removedExpanded}"><span>Removed resources · ${records.length}</span><span>${esc(countTypes(records))}</span></button>${state.removedExpanded ? `<ul>${records.map(item => `<li>${esc(item.type)} · ${esc(item.label)}</li>`).join('')}</ul><p class="helper-text">Removed resources cannot be restored here.</p>` : ''}</section>` : ''}${state.role === 'debug' ? `<section class="drawer-section"><h3>Extraction details</h3><p class="debug-detail">${esc(info.debug)}</p></section>` : ''}</aside>`;
  }

  function mediaDrawer() {
    const media = current().media;
    return `<aside class="layer drawer" role="dialog" aria-modal="${window.innerWidth < 1200}" aria-labelledby="media-title"><div class="layer-heading"><div><h2 id="media-title">Cooking media · ${media.length}</h2><span class="meta-label">Supplementary reference</span></div><div><button type="button" data-action="expand-media">${state.mediaExpanded ? 'Compact' : 'Expand'}</button> <button type="button" data-action="close-layer">Close</button></div></div>${media.map(item => `<article class="media-item"><div class="media-placeholder" role="img" aria-label="Placeholder for ${esc(item.title)}">Image reference</div><strong>${esc(item.title)}</strong><div class="meta-label">${esc(item.origin)} · ${esc(item.author)}${item.current ? ' · Current cover' : ''}</div></article>`).join('')}</aside>`;
  }

  function renderLayer() {
    if (!state.layer) { layerRoot.innerHTML = ''; return; }
    const modal = window.innerWidth < 1200 || state.layer.type === 'disclosure';
    root.inert = modal; toolbar.inert = modal;
    document.body.classList.toggle('wide-drawer-open', !modal && ['import', 'media'].includes(state.layer.type));
    const backdrop = modal ? '<div class="layer-backdrop" data-action="close-layer"></div>' : '';
    if (state.layer.type === 'import') layerRoot.innerHTML = backdrop + importDrawer();
    else if (state.layer.type === 'media') layerRoot.innerHTML = backdrop + mediaDrawer();
    else {
      const values = current().recipe[state.layer.kind] || [];
      layerRoot.innerHTML = `${backdrop}<section class="layer popover" role="dialog" aria-modal="true" aria-labelledby="disclosure-title"><div class="layer-heading"><h2 id="disclosure-title">All ${esc(state.layer.kind)}</h2><button type="button" data-action="close-layer">Close</button></div><ul class="plain-list">${values.map(value => `<li>${esc(value)}</li>`).join('')}</ul></section>`;
    }
    layerRoot.querySelector('[data-action="close-layer"]')?.focus();
  }

  function openLayer(type, trigger, details) {
    state.layer = Object.assign({ type }, details || {}); state.layerTrigger = trigger; state.pending = null; state.message = '';
    renderLayer();
  }

  function closeLayer(returnFocus = true) {
    if (!state.layer) return;
    const trigger = state.layerTrigger;
    state.layer = null; state.layerTrigger = null; state.pending = null;
    root.inert = false; toolbar.inert = false; document.body.classList.remove('wide-drawer-open'); layerRoot.innerHTML = '';
    if (returnFocus && trigger && document.contains(trigger)) trigger.focus();
  }

  function removePrimary() {
    const info = current().importInfo;
    const group = info.groups.find(item => item.id === state.pending.groupId);
    const removableChildren = activeChildren(group).filter(child => !child.currentCover);
    state.removedIds.add(group.id); state.removedItems.push({ type: group.type, label: group.label });
    removableChildren.forEach(child => { state.removedIds.add(child.id); state.removedItems.push({ type: child.type, label: child.label }); });
    state.message = removableChildren.some(child => child.currentCover) ? 'Source removed. Its current cover remains available.' : 'Source and derived resources removed.';
    if (group.children.some(child => child.currentCover)) state.message = 'Source and derived resources removed. The current cover was kept.';
    state.pending = null; renderLayer(); announce(state.message);
  }

  root.addEventListener('click', event => {
    const mode = event.target.closest('[data-mode]')?.dataset.mode;
    if (mode) { setView(mode, { restoreDefault: mode === 'default' }); return; }
    const disclosure = event.target.closest('[data-disclosure]');
    if (disclosure) { openLayer('disclosure', disclosure, { kind: disclosure.dataset.disclosure }); return; }
    const expand = event.target.closest('[data-expand]');
    if (expand) { const kind = expand.dataset.expand; state.expanded[kind] = !state.expanded[kind]; renderCurrentState(); requestAnimationFrame(() => root.querySelector(`[data-expand="${kind}"]`)?.focus()); return; }
    const tab = event.target.closest('[data-focus-tab]');
    if (tab) { state.mobileFocusTab = tab.dataset.focusTab; renderCurrentState(); return; }
    const action = event.target.closest('[data-action]')?.dataset.action;
    if (action === 'import') openLayer('import', event.target.closest('button'));
    else if (action === 'media') openLayer('media', event.target.closest('button'));
    else if (action === 'retry') { state.scenario = 'normal'; renderCurrentState(); }
    else if (action) announce(`${action} is outside this refinement prototype`);
  });

  layerRoot.addEventListener('click', event => {
    const removePrimaryId = event.target.closest('[data-remove-primary]')?.dataset.removePrimary;
    if (removePrimaryId) { state.pending = { type: 'primary', groupId: removePrimaryId }; renderLayer(); return; }
    const childButton = event.target.closest('[data-remove-child]');
    if (childButton) { state.removedIds.add(childButton.dataset.removeChild); state.removedItems.push({ type: childButton.dataset.type, label: childButton.dataset.label }); state.message = `${childButton.dataset.label} removed.`; renderLayer(); return; }
    const action = event.target.closest('[data-action]')?.dataset.action;
    if (action === 'close-layer') closeLayer();
    else if (action === 'prepare-flags') { state.pending = { type: 'flags' }; renderLayer(); }
    else if (action === 'cancel-confirm') { state.pending = null; renderLayer(); }
    else if (action === 'confirm-flags') { state.flagsReviewed.add(state.scenario); state.pending = null; state.message = 'All import messages marked as reviewed.'; renderCurrentState(); renderLayer(); announce(state.message); }
    else if (action === 'confirm-primary') removePrimary();
    else if (action === 'edit-from-drawer') setView('edit');
    else if (action === 'toggle-removed') { state.removedExpanded = !state.removedExpanded; renderLayer(); }
    else if (action === 'expand-media') { state.mediaExpanded = !state.mediaExpanded; renderLayer(); }
  });

  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && state.layer) { closeLayer(); return; }
    const modal = layerRoot.querySelector('[role="dialog"][aria-modal="true"]');
    if (!modal || event.key !== 'Tab') return;
    const focusable = [...modal.querySelectorAll('button, [href], select, input, [tabindex]:not([tabindex="-1"])')].filter(node => !node.disabled);
    if (!focusable.length) return;
    const first = focusable[0], last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });

  scenarioSelect.addEventListener('change', () => { state.scenario = scenarioSelect.value; state.view = 'default'; state.expanded = { ingredients: false, instructions: false, notes: false }; state.removedIds.clear(); state.removedItems = []; state.removedExpanded = false; state.pending = null; state.message = ''; closeLayer(false); renderCurrentState(); window.scrollTo(0, 0); });
  viewSelect.addEventListener('change', () => setView(viewSelect.value));
  roleSelect.addEventListener('change', () => { state.role = roleSelect.value; renderCurrentState(); if (state.layer) renderLayer(); });
  placementSelect.addEventListener('change', () => { state.placement = placementSelect.value; renderCurrentState(); });
  window.addEventListener('resize', () => { if (state.layer) renderLayer(); });

  scenarioSelect.value = state.scenario;
  renderCurrentState();
}());
