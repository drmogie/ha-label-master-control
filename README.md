# Label Master Control

Turn a Home Assistant **label** into a master control device. Add the label to any light, switch, or fan, and this integration gives you one master entity per domain that aggregates and controls every entity currently carrying that label - live, with no reload needed when you add or remove the label from something.

## What it does

- Pick a label when adding the integration. One HA device is created for it, with three entities:
  - **Switch** - on if any labeled switch is on; turns all of them on/off together.
  - **Fan** - on if any labeled fan is on; reports/sets percentage and preset mode from a representative fan; turns all of them on/off together.
  - **Light** - on if any labeled light is on; reports/sets brightness, HS color, and color temperature from a representative light; turns all of them on/off together.
- Membership is tracked live against the entity registry. Add or remove the label from an entity and the master device picks it up immediately - no restart or reload.
- The light's "representative" entity (the one whose brightness/color the master reports) defaults to the first found, but can be pinned to a specific light from the device's Configure options - it automatically falls back to first-found again if that light is later unlabeled or becomes unavailable.
- All three master entities are always created for every label device, even if nothing of that type currently carries the label - they just report off/idle until something does. This keeps live relabeling simple: no platforms need to be added or removed as membership changes.

## Install

### HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=drmogie&repository=ha-label-master-control&category=integration)

### Manual

Copy `custom_components/label_master_control` into your `config/custom_components/` folder and restart Home Assistant.

## Use

Settings -> Devices & Services -> Add Integration -> **Label Master Control** -> pick a label.

To reassign the label, or pin a representative light, open the device and choose **Configure**.

## Roadmap

v1 covers light, switch, and fan. Lock and cover are planned next, but each needs its own aggregate-state rule decided deliberately (candidate for both: any-member-active wins, mirroring any-on) rather than reusing the on/off default blindly. Climate, media_player, and a read-only binary_sensor aggregate are further out.

## Status

Freshly built - not yet run against a live Home Assistant instance. Please open an issue with anything that doesn't behave as documented above.
