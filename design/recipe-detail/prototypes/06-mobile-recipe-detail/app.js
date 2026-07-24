const state = {
  scenario: 'normal', context: 'default', role: 'user', deleteResult: 'success',
  layer: null, layerTrigger: null, defaultScroll: 0, focusTab: 'ingredients',
  expanded: { ingredients: false, instructions: false, notes: false },
  selectedMedia: 0, reviewed: new Set(), removedIds: new Set(), removedItems: [],
  pending: null, panelScroll: { media: 0, import: 0 }, sheetGesture: null
};

const prototypeRoot = document.querySelector('#prototype-root');
const layerRoot = document.querySelector('#layer-root');
const scenarioSelect = document.querySelector('#scenario-select');
const contextSelect = document.querySelector('#context-select');
const roleSelect = document.querySelector('#role-select');
const deleteResultSelect = document.querySelector('#delete-result-select');

function currentScenario() { return window.mobileRecipeScenarios[state.scenario]; }
function renderLayer() { layerRoot.replaceChildren(); }
function render() {
  const scenario = currentScenario();
  if (scenario.state === 'ready') {
    prototypeRoot.innerHTML = '<article class="product-surface" data-product-surface><p>Recipe surface ready</p></article>';
  } else if (scenario.state === 'loading') {
    prototypeRoot.innerHTML = '<section class="product-surface state-panel" data-product-surface aria-busy="true"><h1>Loading recipe</h1><p>Your recipe is being prepared.</p></section>';
  } else if (scenario.state === 'missing') {
    prototypeRoot.innerHTML = `<section class="product-surface state-panel" data-product-surface role="alert"><h1>Recipe not found</h1><p>${scenario.message}</p></section>`;
  } else {
    prototypeRoot.innerHTML = `<section class="product-surface state-panel" data-product-surface role="alert"><h1>Recipe failed to load</h1><p>${scenario.message}</p></section>`;
  }
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
scenarioSelect.addEventListener('change', event => { state.scenario = event.target.value; render(); });
contextSelect.addEventListener('change', event => { state.context = event.target.value; render(); });
roleSelect.addEventListener('change', event => { state.role = event.target.value; render(); });
deleteResultSelect.addEventListener('change', event => { state.deleteResult = event.target.value; });

window.mobileRecipePrototype = { getState: () => state };
render();
