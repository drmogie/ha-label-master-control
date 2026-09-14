# Label Master Control

Label any light, switch, or fan the normal Home Assistant way, and this integration automatically creates a master device that toggles every entity sharing that same label combination - live, no reload, and no separate "pick a label" setup step.

## What it does

- Add the integration once. That's the only manual step - it just turns the feature on and asks how you want labels grouped (see below). It never asks you to pick a specific label.
- From then on, label any light/switch/fan through that entity's own settings (Settings -> Devices & Services -> Entities -> pick the entity -> Labels). The moment you do, a matching **domain-scoped** master device appears (or an existing one gains a member) - e.g. labeling a light with `basement_bathroom` and `default` creates a **Light** device that aggregates and controls every other light sharing that same label combination. A switch with the same two labels gets its own separate **Switch** device - domains are never mixed onto one device.
- Each master entity is on if any member is on, and fans commands out to every current member (brightness/color/percentage/preset mode included, for light and fan).
- The master light's reported brightness/color come from a "representative" member - by default the first one currently on, but pinnable to a specific light via a hidden "Representative light" picker on that device's Configure section. It automatically falls back to first-found again if the pinned light stops being on.
- Remove a label and the device updates (or disappears, if it was the last member) immediately.

## Grouping modes

Chosen once when you add the integration (changeable later from its own Configure options):

- **Exact label match** (default) - a group's key is an entity's entire label set. Two entities only share a device if they carry *exactly* the same labels. Simple to predict; adding any unrelated label to an entity splits it into a new group.
- **Shared label pairs** - a group's key is every unordered pair of labels an entity carries, so an entity with 3 labels can belong to up to 3 different pair-groups. This tolerates extra, unrelated labels riding along on the same entity, closer to how a two-label intersection works, at the cost of an entity potentially joining more than one group.

## Install

### HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=drmogie&repository=ha-label-master-control&category=integration)

### Manual

Copy `custom_components/label_master_control` into your `config/custom_components/` folder and restart Home Assistant.

## Use

Settings -> Devices & Services -> Add Integration -> **Label Master Control** -> pick a grouping mode -> done.

Then just label your entities as you normally would. Devices appear on their own under Settings -> Devices & Services -> Label Master Control.

## Roadmap

v1 covers light, switch, and fan. Lock and cover are planned next, but each needs its own aggregate-state rule decided deliberately (candidate for both: any-member-active wins, mirroring any-on) rather than reusing the on/off default blindly. Climate, media_player, and a read-only binary_sensor aggregate are further out.

## Status

Freshly rebuilt around live, label-driven auto-discovery (no config-flow-per-label) - not yet run against a live Home Assistant instance. Please open an issue with anything that doesn't behave as documented above.
