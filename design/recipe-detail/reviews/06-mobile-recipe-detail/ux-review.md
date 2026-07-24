# UX review

Status: internal pass; user approval pending.

Tested Default View, Focus, metadata disclosure, Media, Import Info, resource removal, overflow, deletion success/failure, and error destinations.

- The sequential reading page keeps recipe content primary and makes the two action groups understandable without turning every section into a card.
- Focus removes secondary context and exposes only one reading list at a time; returning to View restores the prior reading position.
- Media and Import Info share one auxiliary slot and never stack or link to one another internally.
- Import review stays message-level: one Mark all reviewed action, no field-level resolution UI.
- Primary and derived resources remain visibly grouped; confirmations stay adjacent to the affected row/group and explain that the saved recipe is unchanged.
- Recipe deletion remains de-emphasized in overflow and uses a distinct blocking confirmation.

Remaining risk: real-device swipe feel and the perceived density of very large import graphs need validation with production-scale data.
