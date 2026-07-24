(function () {
  const baseIngredients = [
    '2 large aubergines, cut into 3 cm pieces', '2 × 400 g tins butter beans, drained',
    '350 g cherry tomatoes', '1 preserved lemon, rind finely chopped',
    '1–2 tbsp smoked paprika (quantity needs review)', '3 garlic cloves, thinly sliced',
    '2 tbsp tomato paste', '250 ml low-sodium vegetable stock', '3 tbsp extra-virgin olive oil',
    '2 tbsp tahini', '1 lemon, juiced', '20 g flat-leaf parsley, roughly chopped'
  ];
  const pantryIngredients = [
    '1 tsp ground cumin', '1 tsp coriander seeds, crushed', '½ tsp chilli flakes',
    '1 red onion, cut into wedges', '1 yellow pepper, sliced', '120 g baby spinach',
    '80 g pitted green olives', '2 tbsp capers, rinsed', '150 g cooked freekeh',
    '100 g Greek-style plant yoghurt', '30 g toasted almonds', '2 spring onions, sliced',
    '1 small fennel bulb, shaved', '1 tbsp date syrup', '2 tsp sherry vinegar',
    '1 tsp flaky sea salt', '½ tsp black pepper', '1 bay leaf', '2 thyme sprigs',
    '1 rosemary sprig', '½ bunch dill, chopped', '½ bunch mint, leaves picked',
    '100 g tenderstem broccoli', '150 g courgette, sliced', '120 g roasted red peppers',
    '1 tbsp harissa paste', '2 tsp maple syrup', '60 g sourdough crumbs',
    '1 tsp sumac', '½ tsp turmeric', '1 tbsp sesame seeds', '1 tsp fennel seeds',
    '120 ml water', '1 tbsp neutral oil', 'Lemon wedges, to serve', 'Warm flatbreads, to serve'
  ];
  const longIngredients = baseIngredients.concat(pantryIngredients).slice(0, 48);

  const baseSteps = [
    'Heat the oven to 220°C / 200°C fan. Put two shallow roasting trays in the oven so they heat evenly.',
    'Toss the aubergine with olive oil, cumin, coriander, salt, and pepper. Spread it across the hot trays without crowding.',
    'Roast for 18 minutes, turn the pieces, then roast until the cut edges are deeply browned but the centres remain soft.',
    'Stir together the tomato paste, stock, garlic, preserved lemon, paprika, and chilli flakes in a wide jug.',
    'Add the beans and tomatoes to the trays. Pour over the seasoned stock and fold gently so the aubergine keeps its shape.',
    'Return the trays to the oven until the tomatoes burst and the sauce reduces around the beans.',
    'Whisk tahini with lemon juice and enough cold water to make a spoonable dressing.',
    'Rest the traybake for 5 minutes. Finish with tahini, parsley, and a final squeeze of lemon.'
  ];
  const longStepDetails = [
    'Toast the coriander and fennel seeds in a dry pan until fragrant, then crush them coarsely.',
    'Soak the sliced red onion in sherry vinegar with a pinch of salt to soften its sharpness.',
    'Drain the butter beans thoroughly and pat them dry so the sauce does not become watery.',
    'Taste the preserved lemon before seasoning; some brands are considerably saltier than others.',
    'Mix the yoghurt with dill, mint, and half the lemon zest. Keep chilled until serving.',
    'Warm the freekeh with a spoonful of stock and loosen the grains with a fork.',
    'Char the yellow pepper directly over a flame or under a hot grill, then peel and slice it.',
    'Blanch the tenderstem broccoli for 90 seconds and cool it immediately to keep its colour.',
    'Fold spinach through the hot beans in two batches so it wilts without releasing excess water.',
    'Toast the almonds and sesame seeds separately because the sesame browns more quickly.',
    'Combine olives, capers, spring onion, and parsley for the sharp finishing relish.',
    'Check the trays after 10 minutes and rotate them if the back of the oven runs hotter.',
    'If the sauce reduces too quickly, add water in 30 ml increments rather than flooding the tray.',
    'If the aubergine is pale, move it closer to the top element for the final 3 minutes.',
    'Brush the flatbreads lightly with neutral oil and warm them on a separate rack.',
    'Whisk date syrup and maple syrup into the remaining sherry vinegar for a balanced glaze.',
    'Add harissa a teaspoon at a time, tasting between additions because heat levels vary.',
    'Season the courgette separately before adding it so the aubergine is not over-salted.',
    'Scatter sourdough crumbs over one tray for the final 5 minutes to create a crisp topping.',
    'Reserve a spoonful of herbs for serving so their colour and aroma remain fresh.',
    'Transfer the hottest tray to a heatproof board and keep its handles away from the table edge.',
    'Spoon freekeh into shallow bowls, leaving room for the vegetables and their sauce.',
    'Divide the traybake evenly, making sure every serving gets beans, aubergine, and tomatoes.',
    'Add the yoghurt and tahini in separate spoonfuls rather than mixing them into the sauce.',
    'Finish with the olive relish, toasted nuts, sumac, herbs, and lemon wedges.',
    'Let leftovers cool uncovered for 20 minutes before transferring them to shallow containers.',
    'Refrigerate the dressing separately so the vegetables can be reheated without splitting it.',
    'Reheat leftovers in a covered skillet with two tablespoons of water until steaming.',
    'Taste once more after reheating and brighten with lemon rather than additional salt.',
    'Record any preferred paprika quantity after review so the next cook starts with a settled value.'
  ];
  const longSteps = baseSteps.concat(longStepDetails).slice(0, 38);

  const tags = [
    'vegan', 'smoky', 'weeknight', 'one-pan', 'high-fibre', 'dairy-free', 'Mediterranean-inspired',
    'batch-friendly', 'freezer-friendly', 'beans', 'aubergine', 'traybake', 'plant-based', 'family dinner',
    'make-ahead', 'pantry', 'lemon', 'tahini', 'tomato', 'herb-forward', 'comfort food', 'budget-aware',
    'meal prep', 'gluten-free option', 'nut-free option', 'spicy', 'roasted', 'sharing', 'autumn', 'winter',
    'protein-rich', 'iron-rich', 'no refined sugar', 'olive oil', 'Middle Eastern-inspired', 'bright',
    'savoury', 'low effort', 'hands-off', 'crowd-pleaser', 'leftovers', 'reheats well', 'flexible',
    'vegetable-forward', 'sauce', 'flatbread-friendly', 'grain bowl', 'lunchbox', 'dinner', 'favourite'
  ];
  const collections = [
    'Weeknight rotation', 'Traybakes', 'Marta recipes', 'Cook next', 'Plant-based mains', 'Autumn dinners',
    'Batch cooking', 'Freezer options', 'High-fibre meals', 'Pantry-led', 'Guests', 'Under one hour',
    'Mediterranean table', 'Bean recipes', 'Aubergine ideas', 'Comfort food', 'Meal prep', 'Family favourites',
    'Test kitchen', 'Reliable repeats'
  ];
  const media = [
    { title: 'Finished traybake', origin: 'Instagram video frame', author: 'Marta Cooks', current: true, preview: 'assets/finished-traybake.svg' },
    { title: 'Aubergine browning reference', origin: 'Instagram video frame', author: 'Marta Cooks', preview: 'assets/aubergine-browning.svg' },
    { title: 'Tahini consistency', origin: 'Imported caption image', author: 'Marta Cooks', preview: 'assets/tahini-consistency.svg' },
    { title: 'Packaging photo', origin: 'Ignored imported image', author: 'Unknown', preview: 'assets/packaging-photo.svg' }
  ];
  const mediaLinks = [
    { title: 'Watch original Instagram cooking video', platform: 'Instagram', author: 'Marta Cooks', href: 'https://www.instagram.com/reel/example-traybake/' },
    { title: 'Open the written preparation guide', platform: 'Marta Cooks website', author: 'Marta Cooks', href: 'https://example.com/marta-cooks/aubergine-traybake' }
  ];
  const importInfo = {
    flags: [
      'Some imported resources were ignored because they did not contribute usable recipe information.',
      'Conflicting information was found between imported sources.',
      'One primary source produced content with lower extraction confidence.'
    ],
    groups: [
      {
        id: 'instagram-link', type: 'Link', label: 'Instagram reel', detail: 'instagram.com/reel/example-traybake', status: 'Used',
        children: [
          { id: 'transcript', type: 'Transcript', label: 'Video transcript', status: 'Used' },
          { id: 'cover-frame', type: 'Image', label: 'Finished traybake', status: 'Used', currentCover: true, preview: 'assets/finished-traybake.svg' },
          { id: 'cooking-frame', type: 'Image', label: 'Aubergine browning reference', status: 'Used', preview: 'assets/aubergine-browning.svg' },
          { id: 'package-frame', type: 'Image', label: 'Packaging photo', status: 'Ignored', preview: 'assets/packaging-photo.svg' },
          { id: 'profile-frame', type: 'Image', label: 'Profile avatar', status: 'Ignored', preview: 'assets/profile-avatar.svg' },
          { id: 'caption-text', type: 'Text', label: 'Caption text', status: 'Used' }
        ]
      },
      {
        id: 'uploaded-image', type: 'Image', label: 'Uploaded cookbook page', detail: 'page-42.jpg', status: 'Used', preview: 'assets/cookbook-page.svg', children: []
      },
      {
        id: 'pasted-text', type: 'Text', label: 'Personal preparation note', detail: 'Pasted during import', status: 'Used', children: []
      }
    ],
    previouslyRemoved: [
      { type: 'Image', label: 'Duplicate low-resolution frame' },
      { type: 'Image', label: 'Blurred preparation frame' },
      { type: 'Link', label: 'Unavailable mirror link' }
    ],
    debug: 'extraction-pass=recipe-v3 · confidence=0.82 · primary-resources=3 · derived-resources=6'
  };
  const normalRecipe = {
    title: 'Smoky Tomato & Butter Bean Stew', imported: true, cover: true,
    source: 'Instagram video', author: 'Marta Cooks', time: '45 min', servings: 4,
    difficulty: 'Moderate', rating: '4.5 out of 5',
    collections: ['Weeknight rotation', 'Pantry-led'], tags: ['vegan', 'smoky', 'high-fibre', 'one-pan'],
    ingredients: baseIngredients, steps: baseSteps,
    notes: 'Add stock gradually if the tomatoes are especially juicy. The stew thickens as it rests.',
    nutrition: { state: 'complete', label: 'Estimated per serving', values: ['430 kcal', '21 g protein', '14 g fibre', '12 g fat'] }
  };
  function scenario(recipe, overrides) {
    return Object.assign({ state: 'ready', recipe, importInfo, media, mediaLinks, mediaAvailable: true }, overrides || {});
  }
  window.prototypeScenarios = {
    normal: scenario(normalRecipe),
    flagged: scenario(Object.assign({}, normalRecipe, { flags: importInfo.flags })),
    manual: scenario(Object.assign({}, normalRecipe, {
      title: 'Roasted Carrot, Lentil & Dill Salad', imported: false, source: '', author: '', cover: true,
      time: '40 min', servings: 4, difficulty: 'Easy', rating: 'Not rated',
      collections: [], tags: [], nutrition: { state: 'missing', label: 'Nutrition unavailable', values: [] }
    }), { importInfo: null, media: [], mediaLinks: [], mediaAvailable: false }),
    dense: scenario(Object.assign({}, normalRecipe, {
      title: 'Charred Aubergine, Butter Bean & Preserved Lemon Weeknight Traybake', cover: false,
      time: '55 min', servings: 6, collections, tags, flags: importInfo.flags,
      nutrition: { state: 'partial', label: 'Estimated · partial', values: ['510 kcal', '24 g protein', 'Fibre unavailable'] }
    })),
    long: scenario(Object.assign({}, normalRecipe, {
      title: 'Slow-Roasted Aubergine, Butter Bean, Preserved Lemon, Freekeh & Herb Sharing Tray',
      cover: false, time: '1 hr 35 min', servings: 8, collections, tags,
      ingredients: longIngredients, steps: longSteps,
      notes: 'Substitution: use chickpeas if butter beans are unavailable.\n\nWarning: preserved lemons vary greatly in saltiness; rinse before use and season only after tasting.\n\nFor serving, keep the tahini, herb yoghurt, and sharp olive relish separate so every person can adjust richness and acidity.',
      nutrition: { state: 'estimated', label: 'Clearly estimated per serving', values: ['560–620 kcal', '22–26 g protein', 'Values vary with toppings'] }
    })),
    loading: { state: 'loading' },
    failed: { state: 'failed', message: 'The recipe could not be loaded. Your library is still available.' },
    missing: { state: 'missing', message: 'This recipe no longer exists or you do not have access.' }
  };
}());
