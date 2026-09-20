# Label Master Control

Build a "master" device that toggles every light, switch, or fan sharing a set of labels you pick - one device at a time, through a wizard, the same shape as Device Emulator's own "pick a type, then name it" flow. No auto-discovery, and nothing appears that you didn't ask for.

## What it does

- **Add Integration -> Label Master Control** starts a 3-step wizard:
  1. Pick the domain this device controls - light, switch, or fan. Fixed for the device's lifetime; a different domain means building a separate device.
  2. Pick one or more labels. Every entity of that domain carrying *all* of these labels becomes a member.
  3. Name the device - a name is suggested from the domain and label names, or type your own.
- Once built, **membership stays live**: label a new entity (or remove a label) through that entity's own settings and the device's members update immediately, no reload. Only the device's *existence* is manual - its membership tracking isn't.
- Each master entity is on if any member is on, and fans commands out to every current member (brightness/color/percentage/preset mode included, for light and fan).
- The master light's reported brightness/color come from a "representative" member - by default the first one currently on, but pinnable to a specific light via a "Representative light" picker in that device's Configure section. It falls back to first-found again if the pinned light stops being on.
- A device's Configure options let you change its label set later (not its domain) - handy if you relabel things and want an existing device to follow, without rebuilding it.
- Want to see exactly what a device is controlling right now? Open the master entity's More info dialog and check the **Related** tab - it lists the current members live, the same way a native Light/Switch/Cover Group shows what it's made of.
- Every device also gets a **Members** diagnostic sensor - its state is the live member count, right on the device's own page, no need to open a specific entity to check. Two more diagnostic sensors, **Members On** and **Members Off**, split that count live so you can see how many are currently on vs. off without opening anything.

## Companion card: Matrix Card

A read-only Lovelace card auto-loads with the integration - no manual resource to add. Drop it on a dashboard:

```yaml
type: custom:ha-label-master-control-card
```

It shows a grid: one row per category+domain combo (e.g. "Default Light", "Extra Fan"), one column per Area, one cell per device that exists for that combo - on/off state, or "-" where you haven't built one yet. It finds every Label Master Control device itself; a device lands in its row by whichever category name (default "Default"/"Extra", editable in the card's own GUI editor) appears in its label set, and in its column by its own assigned Area (Settings -> Devices -> that device -> Area). A **Recheck** button (top right) re-scans the entity/device/area registries directly, in case anything looks stale.

The card only displays - it never creates, edits, or relabels anything. Build a device for a combo that shows "-" with the wizard above, same as always.

## Install

### HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=drmogie&repository=ha-label-master-control&category=integration)

### Manual

Copy `custom_components/label_master_control` into your `config/custom_components/` folder and restart Home Assistant.

## Use

Settings -> Devices & Services -> Add Integration -> **Label Master Control**. Its icon (built from the logo you provided) should show up automatically - Home Assistant 2026.3+ reads brand images straight out of the integration's own `brand/` folder. Pick a domain -> pick labels -> name it -> done.

Repeat to build as many devices as you want. Each shows up under Settings -> Devices & Services -> Label Master Control.

## Roadmap

The wizard currently offers light, switch, and fan. Lock and cover are planned next, but each needs its own aggregate-state rule decided deliberately (candidate for both: any-member-active wins, mirroring any-on) rather than reusing the on/off default blindly. Climate, media_player, and a read-only binary_sensor aggregate are further out.

## Status

Rebuilt around manual, wizard-driven device creation with live membership tracking - not yet run against a live Home Assistant instance. Please open an issue with anything that doesn't behave as documented above.
