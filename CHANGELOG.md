# Changelog

## 2026.09.20.04
- Added a companion Lovelace card: **Matrix Card** (`custom:ha-label-master-control-card`). Read-only status grid - one row per category+domain combo (e.g. "Default Light", "Extra Fan"), one column per Area, showing each device's on/off state or "-" where no device exists yet for that combo. Auto-discovers every device on the dashboard with no required config; a Recheck button re-scans the entity/device/area registries directly in case anything's out of sync. Served automatically (no manual Lovelace resource needed), same pattern as Piper Browser Speaker's own card.
- Every master entity now also exposes a `labels` attribute (its configured label set, by name) alongside the existing `entity_id` members attribute - added so the new Matrix Card (or anything else) can tell which category a device represents without guessing from its display name.

## 2026.09.20.03
- Added two more diagnostic sensors alongside **Members**: **Members On** and **Members Off**, each showing a live count (and, as its `entity_id` attribute, the matching subset) so you can see at a glance how many of a device's matched entities are currently on vs. off, right on the device's own page.

## 2026.09.20.02
- Added a **Members** diagnostic sensor to every device (any domain) - its state is the live member count and its `entity_id` attribute is the full list, so you can see what a device is controlling right from the device's own page (Settings -> Devices & services -> that device) instead of having to open a specific master entity's Related tab.

## 2026.09.20.01
- Every master entity now exposes its current members as an `entity_id` attribute - the same attribute HA's own native Light/Switch/Cover Group entities use, which the frontend already reads to populate that entity's **Related** tab. Open any master switch/fan/light -> More info -> Related to see exactly which real entities it's currently controlling, live off the aggregator, no new UI needed.

## 2026.09.14.5
- Added brand images (`custom_components/label_master_control/brand/icon.png`, `icon@2x.png`, `logo.png`, `logo@2x.png`) so the integration shows a proper icon in Settings -> Devices & Services and the HACS store, same pattern as Device Emulator.

## 2026.09.14.4
- Fixed the master fan entity not responding to on/off at all. Modern Home Assistant requires a `FanEntity` to declare `FanEntityFeature.TURN_ON`/`TURN_OFF` in `supported_features` before it will call `async_turn_on`/`async_turn_off` - without them the methods were implemented but never invoked, so toggling the fan silently did nothing. Switch and light aren't affected; only `FanEntity` has this explicit-opt-in requirement.

## 2026.09.14.3
- Reworked device creation back to manual: the integration no longer auto-discovers a device the moment two entities happen to share labels (that produced too many unwanted devices). Add Integration now runs a 3-step wizard - pick a domain (light/switch/fan), pick one or more labels, name the device (suggested from domain + labels, or your own) - the same "pick a type, then name it" shape as Device Emulator's own flow. Dropped the "grouping mode" choice (exact match vs. shared label pairs) along with auto-discovery. What's unchanged: once a device exists, its *membership* still tracks the entity registry live - labeling a new entity with the same label set joins it automatically, no reload. `manifest.json`'s `integration_type` reverts to `device` (one device per config entry, like 2026.09.14.1) since each entry is a single manually-built device again.

## 2026.09.14.2
- Reworked the whole mechanism: the integration no longer asks you to pick a label through a config flow. Instead it watches the entity registry directly - labeling any light/switch/fan through that entity's own settings automatically creates/updates/removes a matching domain-scoped master device, live. Added a "grouping mode" choice (exact label-set match, or shared label pairs) and a hidden per-light-group "Representative light" select entity to replace the old per-device options flow. Superseded by 2026.09.14.3's revert to manual device creation.

## 2026.09.14.1
- Initial release (superseded by 2026.09.14.2's rework): config flow (pick a label), live label-membership tracking via the entity registry, and master switch/fan/light entities with any-on aggregate state and fan-out commands.
