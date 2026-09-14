# Changelog

## 2026.09.14.2
- Reworked the whole mechanism: the integration no longer asks you to pick a label through a config flow. Instead it watches the entity registry directly - labeling any light/switch/fan through that entity's own settings automatically creates/updates/removes a matching domain-scoped master device, live. Added a "grouping mode" choice (exact label-set match, or shared label pairs) and a hidden per-light-group "Representative light" select entity to replace the old per-device options flow.

## 2026.09.14.1
- Initial release (superseded by 2026.09.14.2's rework): config flow (pick a label), live label-membership tracking via the entity registry, and master switch/fan/light entities with any-on aggregate state and fan-out commands.
