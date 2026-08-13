const state = {
  activeSection: 'ingredients',
  dirty: true,
  saveState: 'idle',
  layer: null,
  layerTrigger: null,
  ingredientDraft: null,
  ingredients: [
    { id: 1, quantity: '2', unit: 'tbsp', name: 'smoked paprika' },
    { id: 2, quantity: '3', unit: 'cloves', name: 'garlic, thinly sliced' },
    { id: 3, quantity: '250', unit: 'ml', name: 'low-sodium vegetable stock' },
    { id: 4, quantity: '20', unit: 'g', name: 'flat-leaf parsley, roughly chopped' }
  ]
};

const units = ['none', 'g', 'ml', 'tsp', 'tbsp', 'cup', 'clove', 'kg', 'l', 'oz', 'lb', 'pinch'];
const appRoot = document.querySelector('#app-root');
const layerRoot = document.querySelector('#layer-root');
const liveRegion = document.querySelector('#live-region');
let sheetGesture = null;

function announce(message) {
  liveRegion.textContent = '';
  requestAnimationFrame(() => { liveRegion.textContent = message; });
}

function sectionHeader(key, title, meta) {
  const expanded = state.activeSection === key;
  return `<button class="section-toggle" type="button" data-section-toggle="${key}" aria-expanded="${expanded}" aria-controls="${key}-panel">
    <span><strong>${title}</strong><small>${meta}</small></span><span class="chevron" aria-hidden="true">${expanded ? '⌃' : '⌄'}</span>
  </button>`;
}

function renderBasics() {
  return `<div class="section-panel basics-form" id="basics-panel">
    <label>Recipe title<input name="title" value="Smoky Tomato & Butter Bean Stew"></label>
    <div class="two-up"><label>Source<input name="source" value="Instagram"></label><label>Author<input name="author" value="Marta Cooks"></label></div>
    <div class="two-up facts"><label>Cooking time<input name="time" value="45 min"></label><label>Servings<input name="servings" inputmode="decimal" value="4"></label></div>
  </div>`;
}

function ingredientSummary(item) {
  return `${item.quantity}${item.unit === 'none' ? '' : ` ${item.unit}`} · ${item.name}`;
}

function renderIngredients() {
  return `<div class="section-panel" id="ingredients-panel">
    <p class="section-help">Drag to reorder</p>
    <ul class="editable-list ingredient-list">${state.ingredients.map(item => `<li data-ingredient-id="${item.id}">
      <button class="handle" type="button" aria-label="Reorder ${item.name}">⠿</button>
      <button class="row-summary" type="button" data-edit-ingredient="${item.id}"><span>${ingredientSummary(item)}</span><span aria-hidden="true">›</span></button>
      <button class="trash" type="button" data-delete-ingredient="${item.id}" aria-label="Delete ${item.name}"></button>
    </li>`).join('')}</ul>
    <button class="add-button" type="button" data-add-ingredient>+ Add ingredient</button>
  </div>`;
}

function renderInstructions() {
  const steps = [
    'Heat the oven to 220°C / 200°C fan and warm two shallow roasting trays.',
    'Toss the aubergine with olive oil, cumin, coriander, salt, and pepper.',
    'Roast for 18 minutes, turn, then continue until deeply browned.',
    'Add beans and tomatoes, pour over the seasoned stock, and return to the oven.'
  ];
  return `<div class="section-panel" id="instructions-panel"><p class="section-help">Drag to reorder</p><ol class="editable-list step-list">${steps.map((step, index) => `<li><button class="handle" aria-label="Reorder step ${index + 1}">⠿</button><button class="row-summary"><span>${step}</span><span aria-hidden="true">›</span></button><button class="trash" aria-label="Delete step ${index + 1}"></button></li>`).join('')}</ol><button class="add-button">+ Add step</button></div>`;
}

function renderNotes() {
  return `<div class="section-panel provisional" id="notes-panel"><p class="provisional-label">Provisional section structure</p><label>Cooking notes<textarea name="notes" rows="9">The stew thickens as it rests. Add the parsley immediately before serving. Leftovers keep for up to three days.</textarea></label></div>`;
}

function renderNutrition() {
  return `<div class="section-panel provisional nutrition-form" id="nutrition-panel"><p class="provisional-label">Provisional section structure</p><div class="two-up"><label>Calories<input name="calories" value="420 kcal"></label><label>Protein<input name="protein" value="18 g"></label></div><div class="two-up"><label>Carbohydrates<input name="carbs" value="52 g"></label><label>Fat<input name="fat" value="17 g"></label></div></div>`;
}

const sections = [
  ['basics', 'Basics', '5 fields', renderBasics],
  ['ingredients', 'Ingredients', '12 of 50', renderIngredients],
  ['instructions', 'Instructions', '8 steps', renderInstructions],
  ['notes', 'Cooking notes', '248 characters', renderNotes],
  ['nutrition', 'Estimated nutrition', '4 values', renderNutrition]
];

function renderApp() {
  const saveLabel = state.saveState === 'saving' ? 'Saving…' : state.saveState === 'saved' && !state.dirty ? 'Saved' : 'Save';
  appRoot.innerHTML = `<header class="compact-edit-header">
      <button class="header-icon" type="button" data-action="back" aria-label="Back to recipe">‹</button>
      <strong class="recipe-title">Smoky Tomato & Butter Bean Stew</strong>
      <button class="save-action" type="button" data-action="save"${state.saveState === 'saving' ? ' disabled' : ''}>${saveLabel}</button>
      <button class="header-icon overflow-trigger" type="button" data-action="overflow" aria-label="More recipe actions">•••</button>
    </header>
    <main class="editor-scroll">${sections.map(([key, title, meta, renderPanel]) => `<section class="accordion-section${state.activeSection === key ? ' is-expanded' : ''}" data-section="${key}">${sectionHeader(key, title, meta)}${state.activeSection === key ? renderPanel() : ''}</section>`).join('')}</main>
    <nav class="global-navigation" aria-label="Main navigation">
      <button type="button" data-destination="recipes" aria-current="page"><b aria-hidden="true">☰</b><span>Recipes</span></button>
      <button type="button" data-destination="collections"><b aria-hidden="true">▦</b><span>Collections</span></button>
      <button class="global-add" type="button" data-destination="add" aria-label="Add recipe">+</button>
      <button type="button" data-destination="notifications"><b aria-hidden="true">●</b><span>Notifications</span></button>
      <button type="button" data-destination="profile"><b aria-hidden="true">○</b><span>Profile</span></button>
    </nav>`;
}

function sheetFrame(title, body, type, blocking = false) {
  return `<div class="sheet-backdrop" data-close-layer></div><section class="bottom-sheet${blocking ? ' blocking' : ''}" role="dialog" aria-modal="true" aria-labelledby="sheet-title" data-layer="${type}"><div class="sheet-handle" aria-hidden="true"></div><header><h2 id="sheet-title">${title}</h2><button type="button" data-close-layer aria-label="Close">×</button></header><div class="sheet-body">${body}</div></section>`;
}

function renderOverflow() {
  return sheetFrame('Recipe actions', `<div class="mode-options" role="group" aria-label="Recipe mode"><button>View</button><button>Focus</button><button aria-current="page">Edit</button></div><button class="menu-row" data-open-aux="media">Media <span>6</span></button><button class="menu-row" data-open-aux="import">Import info</button><hr><button class="menu-row danger">Delete recipe…</button>`, 'overflow');
}

function renderIngredientSheet() {
  const draft = state.ingredientDraft;
  const visible = units.filter(unit => unit.includes(draft.query.toLowerCase()));
  return sheetFrame(draft.isNew ? 'Add ingredient' : 'Edit ingredient', `<label>Ingredient<input data-draft-field="name" value="${draft.name}"></label><div class="two-up"><label>Quantity<input data-draft-field="quantity" inputmode="decimal" value="${draft.quantity}"></label><label>Unit<input data-draft-field="unit" value="${draft.unit}" readonly></label></div><label>Find unit<input data-unit-search placeholder="Search units…" value="${draft.query}"></label><div class="unit-chips" aria-label="Available units">${visible.slice(0, 6).map(unit => `<button type="button" data-unit="${unit}"${draft.unit === unit ? ' aria-pressed="true"' : ''}>${unit}</button>`).join('')}${draft.query ? '' : `<button type="button" class="more-units">+${Math.max(0, units.length - 6)}</button>`}</div><p class="dictionary-note">Fixed dictionary · ${Math.min(visible.length, 6)} units shown</p><footer><button type="button" data-close-layer>Cancel</button><button class="primary" type="button" data-done-ingredient>Done</button></footer>`, 'ingredient');
}

function renderGuard() {
  return sheetFrame('Discard unsaved changes?', `<p>Your changes to this recipe have not been saved.</p><div class="stacked-actions"><button class="primary" type="button" data-close-layer>Keep editing</button><button class="danger-action" type="button" data-discard-draft>Discard changes</button></div>`, 'dirty-guard', true);
}

function renderAux(type) {
  const title = type === 'media' ? 'Media' : 'Import info';
  const copy = type === 'media' ? 'Read-only recipe media opens here. Manage media remains a separate workspace.' : 'Import flags and grouped resources open here without leaving Edit Mode.';
  return sheetFrame(title, `<p>${copy}</p><p class="preserved-state">Recipe draft and active section are preserved.</p>`, type);
}

function renderLayer() {
  if (!state.layer) { layerRoot.replaceChildren(); return; }
  layerRoot.innerHTML = state.layer === 'overflow' ? renderOverflow() : state.layer === 'ingredient' ? renderIngredientSheet() : state.layer === 'dirty-guard' ? renderGuard() : renderAux(state.layer);
  requestAnimationFrame(() => layerRoot.querySelector('[data-close-layer], input, button')?.focus());
}

function openLayer(type, trigger) {
  state.layer = type;
  state.layerTrigger = trigger || document.activeElement;
  appRoot.inert = true;
  renderLayer();
}

function closeLayer() {
  const trigger = state.layerTrigger;
  state.layer = null;
  state.ingredientDraft = null;
  appRoot.inert = false;
  renderLayer();
  requestAnimationFrame(() => trigger?.focus());
}

function editIngredient(id) {
  const item = state.ingredients.find(candidate => candidate.id === id);
  state.ingredientDraft = { ...item, query: '', isNew: false };
  openLayer('ingredient', document.querySelector(`[data-edit-ingredient="${id}"]`));
}

appRoot.addEventListener('click', event => {
  const control = event.target.closest('button');
  if (!control) return;
  if (control.dataset.sectionToggle) {
    state.activeSection = state.activeSection === control.dataset.sectionToggle ? null : control.dataset.sectionToggle;
    renderApp();
    return;
  }
  if (control.dataset.editIngredient) { editIngredient(Number(control.dataset.editIngredient)); return; }
  if (control.hasAttribute('data-add-ingredient')) {
    state.ingredientDraft = { id: Date.now(), quantity: '', unit: 'none', name: '', query: '', isNew: true };
    openLayer('ingredient', control);
    return;
  }
  if (control.dataset.deleteIngredient) {
    state.ingredients = state.ingredients.filter(item => item.id !== Number(control.dataset.deleteIngredient));
    state.dirty = true;
    state.saveState = 'idle';
    renderApp();
    return;
  }
  if (control.dataset.action === 'overflow') { openLayer('overflow', control); return; }
  if (control.dataset.action === 'back') { if (state.dirty) openLayer('dirty-guard', control); else announce('Back to recipe'); return; }
  if (control.dataset.action === 'save') {
    state.saveState = 'saving'; renderApp(); announce('Saving recipe');
    setTimeout(() => { state.dirty = false; state.saveState = 'saved'; renderApp(); announce('Recipe saved'); }, 450);
    return;
  }
  if (control.dataset.destination && control.dataset.destination !== 'recipes') {
    if (state.dirty) openLayer('dirty-guard', control); else announce(`Open ${control.dataset.destination}`);
  }
});

appRoot.addEventListener('input', event => {
  if (event.target.matches('input, textarea')) {
    state.dirty = true;
    state.saveState = 'idle';
    const save = appRoot.querySelector('.save-action');
    if (save) save.textContent = 'Save';
  }
});

layerRoot.addEventListener('click', event => {
  const control = event.target.closest('button, [data-close-layer]');
  if (!control) return;
  if (control.hasAttribute('data-close-layer')) { closeLayer(); return; }
  if (control.dataset.openAux) { state.layer = control.dataset.openAux; renderLayer(); return; }
  if (control.dataset.unit) { state.ingredientDraft.unit = control.dataset.unit; state.ingredientDraft.query = ''; renderLayer(); return; }
  if (control.hasAttribute('data-done-ingredient')) {
    const draft = state.ingredientDraft;
    if (draft.isNew) state.ingredients.push({ id: draft.id, quantity: draft.quantity, unit: draft.unit, name: draft.name || 'New ingredient' });
    else state.ingredients = state.ingredients.map(item => item.id === draft.id ? { id: draft.id, quantity: draft.quantity, unit: draft.unit, name: draft.name } : item);
    state.dirty = true; state.saveState = 'idle'; closeLayer(); renderApp(); return;
  }
  if (control.hasAttribute('data-discard-draft')) { state.dirty = false; closeLayer(); announce('Changes discarded'); }
});

layerRoot.addEventListener('input', event => {
  if (!state.ingredientDraft) return;
  if (event.target.dataset.draftField) state.ingredientDraft[event.target.dataset.draftField] = event.target.value;
  if (event.target.hasAttribute('data-unit-search')) { state.ingredientDraft.query = event.target.value; renderLayer(); }
});

layerRoot.addEventListener('pointerdown', event => {
  if (!event.target.closest('.sheet-handle') || state.layer === 'dirty-guard') return;
  sheetGesture = { y:event.clientY, time:performance.now() };
});

layerRoot.addEventListener('pointerup', event => {
  if (!sheetGesture) return;
  const distance = event.clientY - sheetGesture.y;
  const velocity = distance / Math.max(1, performance.now() - sheetGesture.time);
  sheetGesture = null;
  if (distance >= 96 || velocity >= 0.65) closeLayer();
});

document.querySelector('.prototype-toolbar').addEventListener('click', event => {
  const button = event.target.closest('[data-scenario]');
  if (!button) return;
  state.activeSection = button.dataset.scenario;
  document.querySelectorAll('[data-scenario]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
  renderApp();
});

document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && state.layer) { event.preventDefault(); closeLayer(); }
  if (event.key === 'Tab' && state.layer) {
    const focusable = [...layerRoot.querySelectorAll('button:not([disabled]), input:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')];
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }
});

window.mobileEditPrototype = { getState: () => ({ ...state, ingredients: state.ingredients.map(item => ({ ...item })) }) };
renderApp();
