(function () {
  const root = document.querySelector('#prototype-root');
  const live = document.querySelector('#live-region');
  let state = 'normal';

  const ingredients = [
    ['2', 'tbsp', 'smoked paprika'],
    ['3', 'clove', 'garlic, thinly sliced'],
    ['250', 'ml', 'low-sodium vegetable stock'],
    ['', 'No unit', 'flat-leaf parsley, roughly chopped']
  ];

  function announce(message) {
    live.textContent = '';
    requestAnimationFrame(() => { live.textContent = message; });
  }

  function field(id, label, value, options = {}) {
    const error = options.error ? `<span class="field-error" id="${id}-error">${options.error}</span>` : '';
    const describedBy = options.error ? ` aria-describedby="${id}-error" aria-invalid="true"` : '';
    const suffix = options.suffix ? `<span class="suffix" aria-hidden="true">${options.suffix}</span>` : '';
    return `<div class="field${options.error ? ' invalid' : ''}"><label for="${id}">${label}</label><div class="compound${suffix ? ' has-suffix' : ''}"><input id="${id}" name="${id}" value="${value}" autocomplete="off"${options.inputmode ? ` inputmode="${options.inputmode}"` : ''}${describedBy}>${suffix}</div>${error}</div>`;
  }

  function sourceField() {
    return `<div class="field"><label for="source">Source</label><select id="source" name="source"><option>Manual</option><option selected>Instagram</option><option>Threads</option><option>TikTok</option><option>Other</option></select></div>`;
  }

  function assessmentControls() {
    return `<fieldset class="choice-field"><legend>Difficulty</legend><div class="segmented"><label><input type="radio" name="difficulty" value="easy"><span>Easy</span></label><label><input type="radio" name="difficulty" value="moderate" checked><span>Moderate</span></label><label><input type="radio" name="difficulty" value="hard"><span>Hard</span></label></div><button type="button" class="text-button" data-action="clear-difficulty">Clear</button></fieldset>
      <fieldset class="choice-field rating-field"><legend>Personal rating</legend><div class="stars" aria-label="Personal rating"><button type="button" aria-label="Rate 1 out of 5">★</button><button type="button" aria-label="Rate 2 out of 5">★</button><button type="button" aria-label="Rate 3 out of 5">★</button><button type="button" aria-label="Rate 4 out of 5">★</button><button type="button" class="empty" aria-label="Rate 5 out of 5">☆</button></div><strong>4 of 5</strong><button type="button" class="text-button" data-action="clear-rating">Clear</button></fieldset>`;
  }

  function ingredientRows() {
    const rows = ingredients.map((item, index) => {
      const invalid = state === 'errors' && index === 1;
      const quantity = invalid ? '2x' : item[0];
      const name = invalid ? '' : item[2];
      return `<li class="ingredient-row">
        <button type="button" class="icon-button handle" aria-label="Reorder ${item[2] || `ingredient ${index + 1}`}">⠿</button>
        ${field(`quantity-${index}`, 'Quantity', quantity, { inputmode: 'decimal', error: invalid ? 'Use numbers and numeric symbols only.' : '' })}
        <div class="field"><label for="unit-${index}">Unit</label><select id="unit-${index}" name="unit-${index}"><option>${item[1]}</option><option>No unit</option><option>g</option><option>ml</option><option>tsp</option><option>tbsp</option></select></div>
        ${field(`ingredient-${index}`, 'Ingredient', name, { error: invalid ? 'Enter an ingredient name.' : '' })}
        <button type="button" class="icon-button trash" aria-label="Remove ${item[2] || `ingredient ${index + 1}`}">⌫</button>
      </li>`;
    }).join('');
    return `<ol class="ingredient-list">${rows}</ol>`;
  }

  function render() {
    const errors = state === 'errors';
    root.innerHTML = `<div class="recipe-page${state === 'guard' ? ' guard-open' : ''}">
      <header class="recipe-header">
        <p class="context">Edit Recipe</p>
        <h1>Smoky Tomato &amp; Butter Bean Stew</h1>
        <p>Imported recipe · last saved 12 minutes ago</p>
        <nav class="recipe-actions" aria-label="Recipe modes and actions">
          <a href="#view">View</a><a href="#focus">Focus</a><a href="#edit-main" aria-current="page">Edit</a><span aria-hidden="true"></span><button type="button">Media · 4</button><button type="button" class="icon-button more" aria-label="More recipe actions">•••</button>
        </nav>
      </header>
      <div class="editor-layout">
        <nav class="section-rail" aria-label="Recipe edit sections">
          <strong>Recipe sections</strong>
          <a href="#basics" class="active${errors ? ' has-error' : ''}"><span>Basics</span><small>${errors ? '3 errors' : '7 fields'}</small></a>
          <a href="#ingredients" class="${errors ? 'has-error' : ''}"><span>Ingredients</span><small>${errors ? '3 errors' : '12 / 50'}</small></a>
          <a href="#instructions"><span>Instructions</span><small>8 steps</small></a>
          <a href="#notes"><span>Cooking notes</span></a>
          <a href="#nutrition"><span>Nutrition</span></a>
        </nav>
        <main id="edit-main" class="edit-canvas" tabindex="-1">
          ${errors ? `<section class="error-summary" tabindex="-1" aria-labelledby="error-title"><h2 id="error-title">6 issues must be fixed before saving</h2><ul><li><a href="#title">Title is too long</a></li><li><a href="#cooking-time">Cooking time must be a positive whole number</a></li><li><a href="#servings">Servings must be a positive whole number</a></li><li><a href="#ingredients">Ingredients exceeds the 50-item limit</a></li><li><a href="#quantity-1">Ingredient 2 has an invalid quantity</a></li><li><a href="#ingredient-1">Ingredient 2 needs a name</a></li></ul></section>` : ''}
          <section id="basics" class="edit-section"><div class="section-heading"><h2>Basics</h2><span>${errors ? '7 fields · 3 errors' : '7 fields'}</span></div>
            <div class="basics-grid"><div><h3>Recipe identity</h3>${field('title', 'Title', errors ? 'Smoky Tomato & Butter Bean Stew with preserved lemon and extra-long seasonal garnish' : 'Smoky Tomato & Butter Bean Stew', { error: errors ? 'Title is too long. Shorten it before saving.' : '' })}<div class="identity-row">${sourceField()}${field('author', 'Author', 'Marta Cooks')}</div></div>
              <div class="assessment"><h3>Cooking facts &amp; assessment</h3><div class="fact-row">${field('cooking-time', 'Cooking time', errors ? '45m' : '45', { suffix: 'min', inputmode: 'numeric', error: errors ? 'Enter a positive whole number or leave this empty.' : '' })}${field('servings', 'Servings', errors ? '4 people' : '4', { inputmode: 'numeric', error: errors ? 'Enter a positive whole number or leave this empty.' : '' })}</div>${assessmentControls()}</div></div>
          </section>
          <section id="ingredients" class="edit-section"><div class="section-heading"><h2>Ingredients</h2><span>${errors ? '51 / 50 · 3 errors' : '12 / 50 · drag to reorder'}</span></div>${errors ? '<div class="section-alert"><strong>Too many ingredients</strong><span>A recipe can contain up to 50. Remove 1 ingredient.</span></div>' : ''}${ingredientRows()}<button type="button" class="secondary">+ Add ingredient</button></section>
          <section id="instructions" class="edit-section"><div class="section-heading"><h2>Instructions</h2><span>8 steps</span></div><p>Instruction editing remains the next design slice; this section is included only to demonstrate continuous-page navigation and scrollspy.</p></section>
          <section id="notes" class="edit-section"><div class="section-heading"><h2>Cooking notes</h2><span>Optional</span></div><p>The stew thickens as it rests. Add the tahini dressing immediately before serving.</p></section>
          <section id="nutrition" class="edit-section"><div class="section-heading"><h2>Estimated nutrition</h2><span>Per serving</span></div><p>420 kcal · 18 g protein · 48 g carbohydrates · 16 g fat</p></section>
        </main>
      </div>
      <footer class="save-bar"><span>3 unsaved changes</span><div><button type="button" data-action="leave">Cancel</button><button type="button" class="primary" data-action="save">Save changes</button></div></footer>
      ${state === 'guard' ? `<div class="scrim"></div><section class="guard" role="dialog" aria-modal="true" aria-labelledby="guard-title"><div><h2 id="guard-title">Unsaved changes</h2><p>Save changes before leaving this recipe?</p></div><footer><button type="button" data-action="keep">Cancel</button><button type="button" class="danger" data-action="discard">Discard</button><button type="button" class="primary" data-action="save-leave">Save</button></footer></section>` : ''}
    </div>`;
    root.querySelectorAll('.section-rail a').forEach(link => link.addEventListener('click', () => {
      root.querySelectorAll('.section-rail a').forEach(item => item.classList.remove('active'));
      link.classList.add('active');
    }));
    root.querySelector('[data-action="leave"]')?.addEventListener('click', () => setState('guard'));
    root.querySelector('[data-action="keep"]')?.addEventListener('click', () => setState('normal'));
    root.querySelector('[data-action="save"]')?.addEventListener('click', () => {
      if (state === 'errors') root.querySelector('.error-summary')?.focus();
      announce(state === 'errors' ? 'Recipe has 6 validation errors.' : 'Prototype save complete.');
    });
  }

  function setState(next) {
    state = next;
    document.querySelectorAll('[data-state]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.state === state)));
    render();
    if (state === 'guard') requestAnimationFrame(() => root.querySelector('.guard button')?.focus());
  }

  document.querySelectorAll('[data-state]').forEach(button => button.addEventListener('click', () => setState(button.dataset.state)));
  render();
}());
