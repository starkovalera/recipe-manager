# Mobile Recipe Edit: Basics and Ingredients

Status: interactive refinement of Prototype 13

This isolated Prototype 14 preserves the approved compact Recipe Edit shell:

- `Back / truncated title / Save / Overflow`;
- Media and Import Info remain in Overflow while editing;
- one recipe-level draft and dirty-exit guard;
- single-open accordion sections;
- unchanged global mobile navigation.

The refinement applies only to mobile Basics and Ingredients:

- Basics has a full-width Recipe title followed by three equal two-column rows: Source / Author, Cooking time / Servings, and Difficulty / Personal rating.
- Source is a fixed select: Manual, Instagram, Threads, TikTok, Other.
- Difficulty is a fixed select: Not set, Easy, Moderate, Hard.
- Personal rating is a fixed select: Not rated and 1–5 out of 5 in whole-number steps.
- Ingredient rows retain the summary-button editor and trash action, but have no mobile DnD, reorder handle, reorder instruction, or accessible move commands.

This version supersedes mobile ingredient reordering only. Desktop ingredient reordering and instruction reordering are unchanged and outside this iteration. Difficulty and Personal rating persistence remain future backend work.

Open `index.html` directly to review. Run `test_prototype.js` and `capture_screenshots.js` with the bundled Node and Playwright runtime for deterministic verification and evidence.
