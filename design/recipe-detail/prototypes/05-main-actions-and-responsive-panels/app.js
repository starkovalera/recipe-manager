(function () {
  const root = document.querySelector('#prototype-root');
  const layerRoot = document.querySelector('#layer-root');
  const live = document.querySelector('#live-region');
  const toolbar = document.querySelector('.prototype-toolbar');
  const scenarioSelect = document.querySelector('#scenario-select');
  const viewSelect = document.querySelector('#view-select');
  const roleSelect = document.querySelector('#role-select');
  const deleteResultSelect = document.querySelector('#delete-result-select');

  const state = {
    scenario: 'flagged', view: 'default', role: 'user',
    layer: null, layerTrigger: null, defaultScroll: 0, mobileFocusTab: 'ingredients',
    expanded: { ingredients: false, instructions: false, notes: false },
    flagsReviewed: new Set(), removedIds: new Set(), removedItems: [], removedExpanded: false,
    pending: null, message: '', mediaSelected: 0, overflowOpen: false,
    deleteResult: 'success', deleteError: false, recipeDeleted: false,
    previewExpanded: new Set(), panelScroll: { import: 0, media: 0 }, sheetGesture: null
  };

  const esc = value => String(value ?? '').replace(/[&<>"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[char]));
  const current = () => window.prototypeScenarios[state.scenario];
  const announce = message => { live.textContent = ''; requestAnimationFrame(() => { live.textContent = message; }); };
  const hasOpenFlags = recipe => Boolean(recipe.flags?.length && !state.flagsReviewed.has(state.scenario));
  const mediaTotal = scenario => (scenario.media?.length || 0) + (scenario.mediaLinks?.length || 0);
  const icon = name => {
    const paths = {
      close: '<path d="M5 5l14 14M19 5L5 19"/>',
      trash: '<path d="M4 7h16M9 3h6l1 4H8l1-4zm-2 4 1 14h8l1-14M10 11v6M14 11v6"/>',
      external: '<path d="M14 4h6v6M20 4l-9 9M19 14v6H4V5h6"/>',
      more: '<circle cx="5" cy="12" r="1.5" fill="currentColor" stroke="none"/><circle cx="12" cy="12" r="1.5" fill="currentColor" stroke="none"/><circle cx="19" cy="12" r="1.5" fill="currentColor" stroke="none"/>'
    };
    return `<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${paths[name]}</svg>`;
  };

  function mainActions(active, scenario) {
    const imported = scenario.recipe.imported;
    const mediaCount = mediaTotal(scenario);
    const modes = [['default', 'View'], ['cooking', 'Focus'], ['edit', 'Edit']];
    const overflow = state.overflowOpen ? `<div class="recipe-overflow-menu" role="menu" aria-label="More recipe actions"><span class="overflow-menu-label">Recipe actions</span><span class="overflow-separator" role="separator"></span><button type="button" class="danger-menu-item" role="menuitem" data-action="delete-recipe">${icon('trash')}<span>Delete recipe…</span></button></div>` : '';
    return `<div class="action-cluster"><nav class="mode-switch" aria-label="Recipe mode">${modes.map(([value, label]) => `<button type="button" data-mode="${value}" ${active === value ? 'aria-current="page" disabled' : ''}>${label}</button>`).join('')}</nav><span class="action-divider" aria-hidden="true"></span><div class="utility-actions" aria-label="Recipe resources">${mediaCount ? `<button type="button" data-action="media">Media · ${mediaCount}</button>` : ''}${imported ? '<button type="button" data-action="import">Import info</button>' : ''}<div class="recipe-overflow"><button type="button" class="icon-button" aria-label="More recipe actions" title="More recipe actions" aria-haspopup="menu" aria-expanded="${state.overflowOpen}" data-action="overflow">${icon('more')}</button>${overflow}</div></div></div>`;
  }

  function setView(view, options) {
    if (state.view === 'default') state.defaultScroll = window.scrollY;
    state.view = view; state.overflowOpen = false;
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
    const actions = mainActions('default', current());
    return `<div class="header-zone placement-full-width"><div class="cover-stack"><div class="cover ${recipe.cover ? 'has-cover' : ''}" role="img" aria-label="${recipe.cover ? 'Recipe cover placeholder' : 'No cover available'}">${recipe.cover ? 'Recipe cover' : 'No cover available'}</div></div><header class="identity"><h1>${esc(recipe.title)}</h1>${sourceRow}${factsRow}</header><div class="header-wide-actions">${actions}</div>${reviewStatus(recipe)}${secondaryMetadata(recipe)}</div>`;
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
    return `<div class="focus-shell"><div class="context-bar"><span>Cooking Focus</span><span>Simplified reading context</span></div><header class="focus-heading"><div><h1>${esc(recipe.title)}</h1><p>${esc(recipe.time)} · ${recipe.servings} servings</p></div></header><div class="focus-actions">${mainActions('cooking', scenario)}</div><div class="mobile-tabs" role="tablist" aria-label="Cooking content"><button type="button" role="tab" aria-selected="${state.mobileFocusTab === 'ingredients'}" data-focus-tab="ingredients">Ingredients</button><button type="button" role="tab" aria-selected="${state.mobileFocusTab === 'instructions'}" data-focus-tab="instructions">Instructions</button></div><div class="recipe-content"><section class="ingredients-column focus-panel" data-focus-panel="ingredients" ${state.mobileFocusTab !== 'ingredients' ? 'data-mobile-hidden="true"' : ''}><h2>Ingredients</h2><ul class="plain-list">${recipe.ingredients.map(item => `<li>${esc(item)}</li>`).join('')}</ul></section><section class="instructions-column focus-panel" data-focus-panel="instructions" ${state.mobileFocusTab !== 'instructions' ? 'data-mobile-hidden="true"' : ''}><h2>Instructions</h2><ol class="steps">${recipe.steps.map(step => `<li>${esc(step)}</li>`).join('')}</ol>${notesSection(recipe)}</section></div></div>`;
  }

  function renderEdit(scenario) {
    const recipe = scenario.recipe;
    return `<div class="context-bar"><span>Edit Recipe Content</span><span>Separate editing context</span></div><header class="edit-heading"><div><h1>Edit ${esc(recipe.title)}</h1><p>Structure placeholder for mode-transition evaluation.</p></div></header><div class="edit-actions">${mainActions('edit', scenario)}</div><section class="edit-placeholder"><h2>Recipe content</h2><p>Title, source/author, servings, time, Ingredients, Instructions, Notes, and Estimated Nutrition belong here. Organization and imported-resource management remain separate.</p><button type="button">Save changes</button></section>`;
  }

  function renderCurrentState() {
    const scenario = current();
    scenarioSelect.value = state.scenario; viewSelect.value = state.view; roleSelect.value = state.role; deleteResultSelect.value = state.deleteResult;
    if (state.recipeDeleted) root.innerHTML = `<section class="recipe-list-destination"><p class="success-toast" role="status">Recipe deleted</p><h1>Recipes</h1><p>The deleted recipe is no longer available in the recipe list or search.</p></section>`;
    else if (scenario.state !== 'ready') root.innerHTML = renderStatePanel(scenario);
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

  function resourcePreview(resource, size) {
    if (resource.type !== 'Image' || !resource.preview) return '';
    const expanded = state.previewExpanded.has(resource.id);
    return `<button type="button" class="resource-thumbnail ${size === 'primary' ? 'primary-thumbnail' : ''}" data-preview-id="${esc(resource.id)}" aria-expanded="${expanded}" aria-label="${expanded ? 'Collapse' : 'Preview'} ${esc(resource.label)}" title="${expanded ? 'Collapse preview' : 'Preview image'}"><img src="${esc(resource.preview)}" alt="" width="64" height="48" loading="lazy"></button>`;
  }

  function expandedResourcePreview(resource) {
    if (!state.previewExpanded.has(resource.id) || !resource.preview) return '';
    return `<div class="expanded-resource-preview"><img src="${esc(resource.preview)}" alt="Expanded preview of ${esc(resource.label)}" width="160" height="110"><button type="button" class="icon-button preview-close" data-preview-id="${esc(resource.id)}" aria-label="Close preview of ${esc(resource.label)}" title="Close preview">${icon('close')}</button></div>`;
  }

  function primaryConfirmation(group) {
    if (state.pending?.type !== 'primary' || state.pending.groupId !== group.id) return '';
    const removed = activeChildren(group).filter(child => !child.currentCover);
    const coverKept = activeChildren(group).some(child => child.currentCover);
    const total = removed.length + 1;
    return `<section class="inline-confirm group-confirm" role="alertdialog" aria-labelledby="confirm-${esc(group.id)}"><h3 id="confirm-${esc(group.id)}">Remove this ${esc(group.type.toLowerCase())}?</h3><p><strong>Your saved recipe will not change.</strong> Ingredients, instructions, notes, and other recipe details will stay as they are.</p><p>Only this source and ${removed.length} related imported resources will be removed: ${esc(countTypes(removed)) || 'no related resources'}.</p>${coverKept ? '<p><strong>The current cover will be kept.</strong></p>' : ''}<div class="confirm-actions"><button type="button" data-action="cancel-confirm">Cancel</button><button type="button" class="primary danger-confirm" data-action="confirm-primary">Remove ${total} resource${total === 1 ? '' : 's'}</button></div></section>`;
  }

  function resourceGroup(group) {
    if (state.removedIds.has(group.id)) return '';
    const allChildren = activeChildren(group);
    const children = allChildren.filter(child => child.status !== 'Ignored');
    const counts = countTypes(allChildren);
    const pending = state.pending?.type === 'primary' && state.pending.groupId === group.id;
    const primaryBody = `<div class="resource-item-body">${resourcePreview(group, 'primary')}<div><span class="resource-type">${esc(group.type)}</span><h3 id="resource-${esc(group.id)}">${esc(group.label)}</h3><p>${esc(group.detail)} · ${esc(group.status)}${allChildren.length ? ` · ${allChildren.length} derived (${esc(counts)})` : ''}</p></div></div>`;
    const childRows = children.map(child => resourceChildRow(child, pending)).join('');
    return `<section class="resource-group ${pending ? 'pending-removal' : ''}" aria-labelledby="resource-${esc(group.id)}"><header class="resource-primary">${primaryBody}${pending ? '<span class="pending-marker">Pending</span>' : `<button type="button" class="icon-button icon-remove" data-remove-primary="${esc(group.id)}" aria-label="Remove ${esc(group.label)}" title="Remove resource">${icon('trash')}</button>`}</header>${expandedResourcePreview(group)}${primaryConfirmation(group)}${children.length ? `<div class="resource-children">${childRows}</div>` : ''}</section>`;
  }

  function resourceChildRow(child, pending) {
    const affected = pending && !child.currentCover;
    const protectedCover = pending && child.currentCover;
    const childPending = state.pending?.type === 'child' && state.pending.childId === child.id;
    return `<div class="resource-child ${affected ? 'will-remove' : ''} ${protectedCover ? 'will-keep' : ''} ${childPending ? 'pending-child-removal' : ''}"><div class="resource-item-body">${resourcePreview(child)}<div><span class="resource-type">${esc(child.type)}</span><strong>${esc(child.label)}</strong><span class="resource-status">${esc(child.status)}${child.currentCover ? ' · Current cover' : ''}</span></div></div>${child.currentCover ? '<span class="cover-lock resource-consequence">Kept as cover</span>' : pending ? '<span class="pending-marker resource-consequence">Will be removed</span>' : childPending ? '<span class="pending-marker resource-consequence">Pending</span>' : `<button type="button" class="icon-button icon-remove" data-remove-child="${esc(child.id)}" data-type="${esc(child.type)}" data-label="${esc(child.label)}" aria-label="Remove ${esc(child.label)}" title="Remove resource">${icon('trash')}</button>`}${expandedResourcePreview(child)}${childConfirmation(child)}</div>`;
  }

  function childConfirmation(child) {
    if (state.pending?.type !== 'child' || state.pending.childId !== child.id) return '';
    return `<section class="inline-confirm child-confirm" role="alertdialog" aria-labelledby="confirm-child-${esc(child.id)}"><h3 id="confirm-child-${esc(child.id)}">Remove this resource?</h3><p><strong>This resource cannot be restored.</strong></p><p>Your saved recipe will not change. Only this imported ${esc(child.type.toLowerCase())} will be removed.</p><div class="confirm-actions"><button type="button" data-action="cancel-confirm">Cancel</button><button type="button" class="primary danger-confirm" data-action="confirm-child">Remove resource</button></div></section>`;
  }

  function ignoredResources(info) {
    const groups = info.groups.map(group => ({ group, children: activeChildren(group).filter(child => child.status === 'Ignored') })).filter(entry => entry.children.length);
    const count = groups.reduce((sum, entry) => sum + entry.children.length, 0);
    if (!count) return '';
    const content = groups.map(({ group, children }) => {
      const pending = state.pending?.type === 'primary' && state.pending.groupId === group.id;
      return `<section class="ignored-source-group" aria-label="Ignored resources from ${esc(group.label)}"><div class="ignored-source-label"><span>From</span><strong>${esc(group.label)}</strong></div><div class="resource-children">${children.map(child => resourceChildRow(child, pending)).join('')}</div></section>`;
    }).join('');
    return `<section class="drawer-section ignored-section"><h3>Ignored resources · ${count}</h3><p class="helper-text">These materials were kept with the import but were not used to create the recipe.</p>${content}</section>`;
  }

  function pendingConfirmation(info) {
    if (!state.pending) return '';
    if (state.pending.type === 'flags') return `<section class="inline-confirm" role="alertdialog" aria-labelledby="confirm-title"><h3 id="confirm-title">Mark all flags as reviewed?</h3><p>This removes ${info.flags.length} review messages. Recipe content and imported resources will not change.</p><div><button type="button" data-action="cancel-confirm">Cancel</button> <button type="button" class="primary" data-action="confirm-flags">Mark all reviewed</button></div></section>`;
    return '';
  }

  function importDrawer() {
    const scenario = current();
    const recipe = scenario.recipe;
    const info = scenario.importInfo;
    const records = removedRecords(info);
    const flagsOpen = hasOpenFlags(recipe);
    return `<aside class="layer drawer import-drawer" role="dialog" aria-modal="${window.innerWidth < 1360}" aria-labelledby="import-title" data-panel-type="import"><div class="sheet-handle" aria-hidden="true"></div><div class="layer-heading"><div><h2 id="import-title">Import info</h2><span class="meta-label">Review messages and imported resources</span></div><div class="layer-heading-actions"><button type="button" class="icon-button" data-action="close-layer" aria-label="Close Import info" title="Close">${icon('close')}</button></div></div>${pendingConfirmation(info)}${state.message ? `<p class="drawer-message" role="status">${esc(state.message)}</p>` : ''}<section class="drawer-section flags-section"><div class="section-heading"><h3>Review needed · ${flagsOpen ? info.flags.length : 0}</h3>${flagsOpen ? '<button type="button" data-action="prepare-flags">Mark all reviewed</button>' : ''}</div>${flagsOpen ? `<ul class="flag-list">${info.flags.map(flag => `<li>${esc(flag)}</li>`).join('')}</ul><p class="helper-text">After reviewing these messages, edit the recipe or mark all reviewed to keep it as it is.</p><button type="button" data-action="edit-from-drawer">Edit recipe</button>` : '<p class="empty-inline">All import messages have been reviewed.</p>'}</section><section class="drawer-section"><h3>Imported resources</h3><p class="helper-text">Derived resources are grouped beneath the primary resource that produced them.</p>${info.groups.map(resourceGroup).join('') || '<p class="empty-inline">No active imported resources.</p>'}</section>${ignoredResources(info)}${records.length ? `<section class="drawer-section removed-summary"><button type="button" class="summary-button" data-action="toggle-removed" aria-expanded="${state.removedExpanded}"><span>Removed resources · ${records.length}</span><span>${esc(countTypes(records))}</span></button>${state.removedExpanded ? `<ul>${records.map(item => `<li>${esc(item.type)} · ${esc(item.label)}</li>`).join('')}</ul><p class="helper-text">Removed resources cannot be restored here.</p>` : ''}</section>` : ''}${state.role === 'debug' ? `<section class="drawer-section"><h3>Extraction details</h3><p class="debug-detail">${esc(info.debug)}</p></section>` : ''}</aside>`;
  }

  function mediaDrawer() {
    const scenario = current();
    const media = scenario.media;
    const links = scenario.mediaLinks || [];
    const selected = media[state.mediaSelected] || media[0];
    const imageContent = selected ? `<article class="media-feature"><img src="${esc(selected.preview)}" alt="${esc(selected.title)}" width="160" height="110"><strong>${esc(selected.title)}</strong><div class="meta-label">${esc(selected.origin)} · ${esc(selected.author)}${selected.current ? ' · Current cover' : ''}</div></article><div class="media-strip" aria-label="Choose cooking image">${media.map((item, index) => `<button type="button" data-media-index="${index}" aria-pressed="${index === state.mediaSelected}"><img src="${esc(item.preview)}" alt="" width="64" height="48" loading="lazy"><span>${esc(item.title)}</span></button>`).join('')}</div>` : '<p class="empty-inline">No imported images are available.</p>';
    const linkContent = links.length ? links.map(link => `<a class="media-link" href="${esc(link.href)}" target="_blank" rel="noopener noreferrer"><span><strong>${esc(link.title)}</strong><small>${esc(link.platform)} · ${esc(link.author)}</small></span>${icon('external')}</a>`).join('') : '<p class="empty-inline">No cooking links are available.</p>';
    return `<aside class="layer drawer media-drawer" role="dialog" aria-modal="${window.innerWidth < 1360}" aria-labelledby="media-title" data-panel-type="media"><div class="sheet-handle" aria-hidden="true"></div><div class="layer-heading"><div><h2 id="media-title">Cooking media · ${mediaTotal(scenario)}</h2><span class="meta-label">Images and external cooking references</span></div><div class="layer-heading-actions"><button type="button" class="icon-button" data-action="close-layer" aria-label="Close Cooking media" title="Close">${icon('close')}</button></div></div><section class="media-section" aria-labelledby="media-images-title"><h3 id="media-images-title">Images · ${media.length}</h3>${imageContent}</section><section class="media-section" aria-labelledby="media-links-title"><h3 id="media-links-title">Videos &amp; links · ${links.length}</h3>${linkContent}</section></aside>`;
  }

  function deleteRecipeDialog() {
    const recipe = current().recipe;
    const scope = recipe.imported
      ? 'This permanently deletes the recipe and its imported files, images, and links. It cannot be restored.'
      : 'This permanently deletes the recipe. It cannot be restored.';
    return `<section class="layer delete-recipe-dialog" role="dialog" aria-modal="true" aria-labelledby="delete-recipe-title"><div class="dialog-heading"><h2 id="delete-recipe-title">Delete “${esc(recipe.title)}”?</h2><button type="button" class="icon-button" data-action="close-layer" aria-label="Close delete recipe confirmation" title="Close">${icon('close')}</button></div><p>${scope}</p>${state.deleteError ? '<p class="delete-error" role="alert">Recipe couldn’t be deleted. Try again.</p>' : ''}<div class="confirm-actions"><button type="button" data-action="close-layer">Cancel</button><button type="button" class="primary danger-confirm" data-action="confirm-delete-recipe">Delete recipe</button></div></section>`;
  }

  function renderLayer(options) {
    if (!state.layer) { layerRoot.innerHTML = ''; return; }
    const previousDrawer = layerRoot.querySelector('.drawer[data-panel-type]');
    if (previousDrawer) state.panelScroll[previousDrawer.dataset.panelType] = previousDrawer.scrollTop;
    const modal = window.innerWidth < 1360 || ['disclosure', 'delete-recipe'].includes(state.layer.type);
    root.inert = modal; toolbar.inert = modal;
    document.body.classList.toggle('wide-drawer-open', !modal && ['import', 'media'].includes(state.layer.type));
    const backdrop = modal ? '<div class="layer-backdrop" data-action="close-layer"></div>' : '';
    if (state.layer.type === 'import') layerRoot.innerHTML = backdrop + importDrawer();
    else if (state.layer.type === 'media') layerRoot.innerHTML = backdrop + mediaDrawer();
    else if (state.layer.type === 'delete-recipe') layerRoot.innerHTML = backdrop + deleteRecipeDialog();
    else {
      const values = current().recipe[state.layer.kind] || [];
      layerRoot.innerHTML = `${backdrop}<section class="layer popover" role="dialog" aria-modal="true" aria-labelledby="disclosure-title"><div class="layer-heading"><h2 id="disclosure-title">All ${esc(state.layer.kind)}</h2><button type="button" class="icon-button" data-action="close-layer" aria-label="Close ${esc(state.layer.kind)}" title="Close">${icon('close')}</button></div><ul class="plain-list">${values.map(value => `<li>${esc(value)}</li>`).join('')}</ul></section>`;
    }
    const drawer = layerRoot.querySelector('.drawer[data-panel-type]');
    if (drawer) {
      const savedScroll = state.panelScroll[drawer.dataset.panelType] || 0;
      void drawer.offsetHeight;
      drawer.scrollTop = savedScroll;
      requestAnimationFrame(() => { if (document.contains(drawer)) drawer.scrollTop = savedScroll; });
    }
    const focusTarget = options?.focusSelector ? layerRoot.querySelector(options.focusSelector) : null;
    if (focusTarget) focusTarget.focus({ preventScroll: true });
    else if (options?.initial) layerRoot.querySelector('[data-action="close-layer"]')?.focus();
  }

  function openLayer(type, trigger, details) {
    state.overflowOpen = false; state.deleteError = false;
    state.layer = Object.assign({ type }, details || {}); state.layerTrigger = trigger; state.pending = null; state.message = '';
    renderLayer({ initial: true });
  }

  function switchPanel(type) {
    if (!state.layer || !['import', 'media'].includes(type)) return;
    state.pending = null;
    state.layer = { type };
    renderLayer({ focusSelector: '[data-action="close-layer"]' });
    announce(type === 'media' ? 'Cooking media opened.' : 'Import info opened.');
  }

  function closeLayer(returnFocus = true) {
    if (!state.layer) return;
    const drawer = layerRoot.querySelector('.drawer[data-panel-type]');
    if (drawer) state.panelScroll[drawer.dataset.panelType] = drawer.scrollTop;
    const trigger = state.layerTrigger;
    state.layer = null; state.layerTrigger = null; state.pending = null; state.sheetGesture = null;
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

  function removeChild() {
    const pending = state.pending;
    if (!pending || pending.type !== 'child') return;
    state.removedIds.add(pending.childId);
    state.removedItems.push({ type: pending.resourceType, label: pending.label });
    state.message = `${pending.label} removed. It cannot be restored.`;
    state.pending = null;
    renderLayer({ focusSelector: '[data-action="toggle-removed"]' });
    announce(state.message);
  }

  function pendingTriggerSelector(pending) {
    if (pending?.type === 'child') return `[data-remove-child="${pending.childId}"]`;
    if (pending?.type === 'primary') return `[data-remove-primary="${pending.groupId}"]`;
    return '[data-action="prepare-flags"]';
  }

  function confirmDeleteRecipe() {
    if (state.deleteResult === 'failure') {
      state.deleteError = true;
      renderLayer({ focusSelector: '[data-action="confirm-delete-recipe"]' });
      announce('Recipe couldn’t be deleted. Try again.');
      return;
    }
    closeLayer(false);
    state.recipeDeleted = true;
    renderCurrentState();
    root.focus({ preventScroll: true });
    announce('Recipe deleted');
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
    if (action === 'overflow') {
      state.overflowOpen = !state.overflowOpen;
      renderCurrentState();
      requestAnimationFrame(() => root.querySelector(state.overflowOpen ? '[role="menuitem"]' : '[data-action="overflow"]')?.focus());
    }
    else if (action === 'delete-recipe') {
      const trigger = root.querySelector('[data-action="overflow"]');
      state.overflowOpen = false;
      renderCurrentState();
      openLayer('delete-recipe', root.querySelector('[data-action="overflow"]') || trigger);
    }
    else if (action === 'import') {
      if (state.layer?.type === 'media') switchPanel('import');
      else openLayer('import', event.target.closest('button'));
    }
    else if (action === 'media') {
      if (state.layer?.type === 'import') switchPanel('media');
      else openLayer('media', event.target.closest('button'));
    }
    else if (action === 'retry') { state.scenario = 'normal'; renderCurrentState(); }
    else if (action) announce(`${action} is outside this refinement prototype`);
  });

  layerRoot.addEventListener('click', event => {
    const removePrimaryId = event.target.closest('[data-remove-primary]')?.dataset.removePrimary;
    if (removePrimaryId) {
      const group = current().importInfo.groups.find(item => item.id === removePrimaryId);
      [group.id, ...group.children.map(child => child.id)].forEach(id => state.previewExpanded.delete(id));
      state.pending = { type: 'primary', groupId: removePrimaryId };
      renderLayer({ focusSelector: '.group-confirm [data-action="cancel-confirm"]' });
      return;
    }
    const previewButton = event.target.closest('[data-preview-id]');
    if (previewButton) {
      const id = previewButton.dataset.previewId;
      if (state.previewExpanded.has(id)) state.previewExpanded.delete(id); else state.previewExpanded.add(id);
      renderLayer({ focusSelector: `[data-preview-id="${id}"]` });
      return;
    }
    const mediaButton = event.target.closest('[data-media-index]');
    if (mediaButton) { state.mediaSelected = Number(mediaButton.dataset.mediaIndex); renderLayer({ focusSelector: `[data-media-index="${state.mediaSelected}"]` }); return; }
    const childButton = event.target.closest('[data-remove-child]');
    if (childButton) {
      state.pending = { type: 'child', childId: childButton.dataset.removeChild, resourceType: childButton.dataset.type, label: childButton.dataset.label };
      renderLayer({ focusSelector: '.child-confirm [data-action="cancel-confirm"]' });
      return;
    }
    const action = event.target.closest('[data-action]')?.dataset.action;
    if (action === 'close-layer') closeLayer();
    else if (action === 'prepare-flags') { state.pending = { type: 'flags' }; renderLayer(); }
    else if (action === 'cancel-confirm') { const selector = pendingTriggerSelector(state.pending); state.pending = null; renderLayer({ focusSelector: selector }); }
    else if (action === 'confirm-flags') { state.flagsReviewed.add(state.scenario); state.pending = null; state.message = 'All import messages marked as reviewed.'; renderCurrentState(); renderLayer(); announce(state.message); }
    else if (action === 'confirm-primary') removePrimary();
    else if (action === 'confirm-child') removeChild();
    else if (action === 'confirm-delete-recipe') confirmDeleteRecipe();
    else if (action === 'edit-from-drawer') setView('edit');
    else if (action === 'toggle-removed') { state.removedExpanded = !state.removedExpanded; renderLayer(); }
  });

  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && state.overflowOpen) { state.overflowOpen = false; renderCurrentState(); requestAnimationFrame(() => root.querySelector('[data-action="overflow"]')?.focus()); return; }
    if (event.key === 'Escape' && state.layer && state.pending) { const selector = pendingTriggerSelector(state.pending); state.pending = null; renderLayer({ focusSelector: selector }); announce('Removal cancelled.'); return; }
    if (event.key === 'Escape' && state.layer) { closeLayer(); return; }
    const modal = layerRoot.querySelector('[role="dialog"][aria-modal="true"]');
    if (!modal || event.key !== 'Tab') return;
    const focusable = [...modal.querySelectorAll('button, [href], select, input, [tabindex]:not([tabindex="-1"])')].filter(node => !node.disabled);
    if (!focusable.length) return;
    const first = focusable[0], last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });

  layerRoot.addEventListener('pointerdown', event => {
    if (window.innerWidth > 760 || !event.target.closest('.sheet-handle')) return;
    const drawer = event.target.closest('.drawer');
    if (!drawer || drawer.scrollTop > 0) return;
    state.sheetGesture = { pointerId: event.pointerId, startY: event.clientY, lastY: event.clientY, startedAt: performance.now(), drawer };
    drawer.classList.add('is-dragging');
    drawer.setPointerCapture?.(event.pointerId);
  });

  layerRoot.addEventListener('pointermove', event => {
    const gesture = state.sheetGesture;
    if (!gesture || gesture.pointerId !== event.pointerId) return;
    const distance = Math.max(0, event.clientY - gesture.startY);
    gesture.lastY = event.clientY;
    gesture.drawer.style.transform = `translateY(${distance}px)`;
    event.preventDefault();
  });

  function finishSheetGesture(event) {
    const gesture = state.sheetGesture;
    if (!gesture || gesture.pointerId !== event.pointerId) return;
    const distance = Math.max(0, gesture.lastY - gesture.startY);
    const elapsed = Math.max(1, performance.now() - gesture.startedAt);
    const velocity = distance / elapsed;
    gesture.drawer.classList.remove('is-dragging');
    gesture.drawer.style.transform = '';
    state.sheetGesture = null;
    if (distance >= 96 || (distance >= 44 && velocity >= 0.7)) {
      closeLayer();
      announce('Panel closed.');
    }
  }

  layerRoot.addEventListener('pointerup', finishSheetGesture);
  layerRoot.addEventListener('pointercancel', finishSheetGesture);

  scenarioSelect.addEventListener('change', () => { state.scenario = scenarioSelect.value; state.view = 'default'; state.expanded = { ingredients: false, instructions: false, notes: false }; state.removedIds.clear(); state.removedItems = []; state.previewExpanded.clear(); state.removedExpanded = false; state.mediaSelected = 0; state.overflowOpen = false; state.recipeDeleted = false; state.deleteError = false; state.panelScroll = { import: 0, media: 0 }; state.pending = null; state.message = ''; closeLayer(false); renderCurrentState(); window.scrollTo(0, 0); });
  viewSelect.addEventListener('change', () => setView(viewSelect.value));
  roleSelect.addEventListener('change', () => { state.role = roleSelect.value; renderCurrentState(); if (state.layer) renderLayer(); });
  deleteResultSelect.addEventListener('change', () => { state.deleteResult = deleteResultSelect.value; state.deleteError = false; if (state.layer?.type === 'delete-recipe') renderLayer(); });
  window.addEventListener('resize', () => { if (state.layer) renderLayer(); });

  scenarioSelect.value = state.scenario;
  renderCurrentState();
}());
