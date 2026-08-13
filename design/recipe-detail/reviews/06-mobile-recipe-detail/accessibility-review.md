# Accessibility review

Status: internal pass; user approval pending.

Tested semantic headings/lists, named dialogs, Focus tabs, live announcements, Escape priority, focus return, deletion focus trap, inert background, and representative touch targets.

- View/Focus state uses `aria-current`; Focus section uses a named tablist and accurate `aria-selected` values.
- Non-destructive sheets are named dialogs; close, Escape, and handle swipe are complementary dismissal methods.
- Blocking recipe deletion traps focus, makes the product surface inert, and cannot be swipe-dismissed.
- Opening and closing layers moves focus predictably; a race guard prevents focusing a layer removed before the next animation frame.
- Primary controls and representative review/disclosure actions meet the 44 × 44 px practical mobile target.
- Loading uses `aria-busy`; failure/missing states use alerts; Edit, review completion, resource removal, and recipe deletion use the polite live region.

Remaining risk: screen-reader output and rotor order should be checked on iOS VoiceOver and Android TalkBack once production components exist.
