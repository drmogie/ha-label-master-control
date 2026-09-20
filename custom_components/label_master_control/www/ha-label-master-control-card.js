/**
 * Label Master Control - Matrix Card
 *
 * Read-only status grid: one row per category+domain combo (e.g. "Light
 * Default", "Fan Extra"), one column per Area, one cell per Label Master
 * Control device that exists for that combo. Shows "-" wherever no device
 * has been built yet for a given Area/category/domain combo.
 *
 * Fully auto-discovering: drop this card on a dashboard with no required
 * config at all. It finds every label_master_control device itself (via
 * each master entity's own `labels` attribute, added to the integration
 * alongside this card - see entity.py) and places it by:
 *   - domain: the master entity's own entity_id prefix (light/switch/fan)
 *   - category: whichever configured category name (default "Default"/
 *     "Extra") appears in that device's label set
 *   - Area: the device's own assigned Area (Settings -> Devices -> that
 *     device -> Area) - a real HA Area, not inferred from anything else
 *
 * This card does not create, edit, or relabel anything - it only reads.
 * Building a device for a combo that shows "-" is still done with Label
 * Master Control's own wizard, same as always.
 *
 * Row order is a Domain/Labels toggle in the table's top-left corner
 * (above the row labels, beside the Area column headers) - "Domain"
 * groups rows by domain first (Light Default, Light Extra, Switch
 * Default, ...), "Labels" groups by category first (Default Light,
 * Default Switch, ..., Extra Light, ...). Defaults to Domain. Each row's
 * own text always reads "<Domain> <Category>" either way - only the
 * grouping/order changes. Remembered per-browser (localStorage), same as
 * the right-click Area hide below.
 *
 * Area columns can be hidden two ways:
 *   - Right-click (or long-press) an Area's column header - a quick,
 *     per-browser toggle stored in localStorage. The card's own Recheck
 *     button (top right) clears these back to "show everything" - it
 *     doesn't touch the permanent list below.
 *   - The card's GUI editor lists every Area it currently sees with a
 *     checkbox - unchecking one hides it for everyone viewing this
 *     dashboard (saved in the card's own config, `hidden_areas`).
 * The two lists are independent and combine (an Area hidden by either one
 * is hidden).
 *
 * No build step, no external dependencies - plain custom elements.
 */
(() => {
  const CARD_TAG = "ha-label-master-control-card";
  const EDITOR_TAG = "ha-label-master-control-card-editor";
  const PLATFORM = "label_master_control";
  // Shown as small print at the bottom of the GUI editor only (never on
  // the card itself), same convention as this integration's sibling cards
  // (e.g. Piper Browser Speaker) - bump alongside const.py's CARD_VERSION
  // on every release; no shared source of truth between the two.
  const CARD_VERSION = "2026.09.20.08";

  const DOMAINS = ["light", "switch", "fan"];
  const DEFAULT_CATEGORIES = ["Default", "Extra"];
  const NO_AREA_LABEL = "No Area";
  const SORT_MODES = ["domain", "label"];
  const DEFAULT_SORT_MODE = "domain";

  function titleCase(word) {
    return word.charAt(0).toUpperCase() + word.slice(1);
  }

  function parseCategories(raw) {
    if (!raw) return DEFAULT_CATEGORIES.slice();
    const list = String(raw)
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    return list.length ? list : DEFAULT_CATEGORIES.slice();
  }

  function buildRows(categories, sortMode) {
    const rows = [];
    if (sortMode === "label") {
      categories.forEach((category) => {
        DOMAINS.forEach((domain) => {
          rows.push({ category, domain, label: `${titleCase(domain)} ${category}` });
        });
      });
    } else {
      DOMAINS.forEach((domain) => {
        categories.forEach((category) => {
          rows.push({ category, domain, label: `${titleCase(domain)} ${category}` });
        });
      });
    }
    return rows;
  }

  // Per-browser storage, shared shape for both the right-click Area hide
  // and the Domain/Labels sort toggle - keyed by the card's own title so
  // two differently-titled instances on the same dashboard don't fight
  // over the same values. Two instances sharing a title (including the
  // default, both left blank) share this state - an acceptable
  // simplification for what's expected to normally be a single instance
  // per dashboard.
  function storageKey(title, suffix) {
    return `ha-label-master-control-card:${suffix}:${title || "default"}`;
  }

  function loadLocallyHidden(title) {
    try {
      const raw = window.localStorage.getItem(storageKey(title, "hidden-areas"));
      const parsed = raw ? JSON.parse(raw) : [];
      return new Set(Array.isArray(parsed) ? parsed : []);
    } catch (err) {
      return new Set();
    }
  }

  function saveLocallyHidden(title, set) {
    try {
      window.localStorage.setItem(storageKey(title, "hidden-areas"), JSON.stringify(Array.from(set)));
    } catch (err) {
      // Private browsing / storage blocked - quick-hide just won't persist
      // across reloads this session. Not worth surfacing to the user.
    }
  }

  function loadSortMode(title) {
    try {
      const raw = window.localStorage.getItem(storageKey(title, "sort-mode"));
      return SORT_MODES.includes(raw) ? raw : DEFAULT_SORT_MODE;
    } catch (err) {
      return DEFAULT_SORT_MODE;
    }
  }

  function saveSortMode(title, mode) {
    try {
      window.localStorage.setItem(storageKey(title, "sort-mode"), mode);
    } catch (err) {
      // Same as above - just won't persist across reloads.
    }
  }

  // Shared grid-building logic. `entities` is an array of
  // { entityId, labels, deviceId }, `devicesById` maps device_id -> area_id,
  // `areasById` maps area_id -> area name, `states` maps entity_id -> HA
  // state string (on/off/unavailable/unknown/etc). Used both by the normal
  // live path (built from the reactive `hass.entities`/`hass.devices`/
  // `hass.areas` collections on every hass update) and by the manual
  // "Recheck" button's path (built from a fresh direct registry fetch via
  // hass.callWS, bypassing any local cache lag).
  function buildMatrix(categories, entities, devicesById, areasById, states) {
    const cells = new Map(); // `${category}|${domain}|${area}` -> {entityId, state}
    const areasSeen = new Set();
    const warnings = [];

    entities.forEach(({ entityId, labels, deviceId }) => {
      const domain = entityId.split(".", 1)[0];
      if (!DOMAINS.includes(domain)) return;

      const labelList = Array.isArray(labels) ? labels : [];
      const matched = categories.filter((cat) =>
        labelList.some((l) => String(l).toLowerCase() === cat.toLowerCase())
      );
      if (matched.length !== 1) {
        warnings.push(
          `${entityId}: expected exactly one category label from [${categories.join(
            ", "
          )}], found [${labelList.join(", ")}] - skipped`
        );
        return;
      }
      const category = matched[0];

      let areaName = NO_AREA_LABEL;
      const areaId = deviceId ? devicesById.get(deviceId) : null;
      if (areaId && areasById.has(areaId)) {
        areaName = areasById.get(areaId);
      }
      areasSeen.add(areaName);

      const key = `${category}|${domain}|${areaName}`;
      if (cells.has(key)) {
        warnings.push(
          `Two devices both match ${key.replace(/\|/g, " / ")}: ${
            cells.get(key).entityId
          } and ${entityId} - keeping the first, ignoring the second`
        );
        return;
      }
      const stateObj = states[entityId];
      cells.set(key, { entityId, state: stateObj ? stateObj.state : undefined });
    });

    if (warnings.length) {
      warnings.forEach((w) => console.warn(`[${CARD_TAG}] ${w}`));
    }

    const areas = Array.from(areasSeen).sort((a, b) => {
      if (a === NO_AREA_LABEL) return 1;
      if (b === NO_AREA_LABEL) return -1;
      return a.localeCompare(b);
    });

    return { cells, areas };
  }

  function liveEntitiesFrom(hass) {
    const entities = [];
    const devicesById = new Map();
    const areasById = new Map();

    if (hass.areas) {
      Object.values(hass.areas).forEach((area) => {
        areasById.set(area.area_id, area.name);
      });
    }
    if (hass.devices) {
      Object.values(hass.devices).forEach((device) => {
        devicesById.set(device.id, device.area_id);
      });
    }
    if (hass.entities) {
      Object.values(hass.entities).forEach((entry) => {
        if (entry.platform !== PLATFORM) return;
        const stateObj = hass.states[entry.entity_id];
        if (!stateObj) return;
        entities.push({
          entityId: entry.entity_id,
          labels: (stateObj.attributes && stateObj.attributes.labels) || [],
          deviceId: entry.device_id,
        });
      });
    }
    return { entities, devicesById, areasById };
  }

  class HaLabelMasterControlCard extends HTMLElement {
    setConfig(config) {
      this._config = config || {};
      this._categories = parseCategories(this._config.categories);
      this._checking = false;
      this._locallyHidden = loadLocallyHidden(this._config.title);
      this._sortMode = loadSortMode(this._config.title);
      this._render();
    }

    set hass(hass) {
      this._hass = hass;
      this._render();
    }

    get hass() {
      return this._hass;
    }

    getCardSize() {
      return 2 + this._categories.length * DOMAINS.length;
    }

    getGridOptions() {
      return { columns: "full", rows: "auto", min_rows: 4 };
    }

    static getConfigElement() {
      return document.createElement(EDITOR_TAG);
    }

    static getStubConfig() {
      return { title: "Label Master Control", categories: "Default, Extra" };
    }

    _configHiddenAreas() {
      return Array.isArray(this._config.hidden_areas) ? this._config.hidden_areas : [];
    }

    _setSortMode(mode) {
      if (!SORT_MODES.includes(mode) || mode === this._sortMode) return;
      this._sortMode = mode;
      saveSortMode(this._config.title, mode);
      this._render();
    }

    async _forceRecheck() {
      if (!this._hass || this._checking) return;
      this._checking = true;
      // "Recheck" doubles as "show every quick-hidden Area again" - the
      // permanent editor-configured hidden_areas list is untouched, only
      // the per-browser right-click list clears.
      this._locallyHidden = new Set();
      saveLocallyHidden(this._config.title, this._locallyHidden);
      this._render();
      try {
        const [entityRegistry, deviceRegistry, areaRegistry] = await Promise.all([
          this._hass.callWS({ type: "config/entity_registry/list" }),
          this._hass.callWS({ type: "config/device_registry/list" }),
          this._hass.callWS({ type: "config/area_registry/list" }),
        ]);

        const devicesById = new Map();
        deviceRegistry.forEach((d) => devicesById.set(d.id, d.area_id));
        const areasById = new Map();
        areaRegistry.forEach((a) => areasById.set(a.area_id, a.name));

        const entities = [];
        entityRegistry.forEach((entry) => {
          if (entry.platform !== PLATFORM) return;
          const stateObj = this._hass.states[entry.entity_id];
          if (!stateObj) return;
          entities.push({
            entityId: entry.entity_id,
            labels: (stateObj.attributes && stateObj.attributes.labels) || [],
            deviceId: entry.device_id,
          });
        });

        this._forcedSnapshot = { entities, devicesById, areasById };
      } catch (err) {
        console.warn(`[${CARD_TAG}] Recheck failed, falling back to live data:`, err);
        this._forcedSnapshot = null;
      } finally {
        this._checking = false;
        this._render();
      }
    }

    _onCellClick(entityId) {
      if (!entityId) return;
      const event = new CustomEvent("hass-more-info", {
        detail: { entityId },
        bubbles: true,
        composed: true,
      });
      this.dispatchEvent(event);
    }

    _onAreaHeaderContextMenu(ev, areaName) {
      ev.preventDefault();
      this._locallyHidden.add(areaName);
      saveLocallyHidden(this._config.title, this._locallyHidden);
      this._render();
    }

    _render() {
      if (!this._hass) return;
      this._config = this._config || {};
      this._categories = this._categories || parseCategories(this._config.categories);
      if (!this._locallyHidden) {
        this._locallyHidden = loadLocallyHidden(this._config.title);
      }
      if (!this._sortMode) {
        this._sortMode = loadSortMode(this._config.title);
      }

      if (!this.shadowRoot) {
        this.attachShadow({ mode: "open" });
        this.shadowRoot.innerHTML = `
          <style>
            ha-card {
              padding: 0;
              overflow: hidden;
              border-radius: var(--ha-card-border-radius, 12px);
            }
            .header {
              display: flex;
              align-items: center;
              justify-content: space-between;
              padding: 12px 16px 4px 16px;
            }
            .header .title {
              font-size: 1.2em;
              font-weight: 500;
              color: var(--ha-card-header-color, var(--primary-text-color));
            }
            .wrap { overflow-x: auto; padding: 0 16px 16px 16px; }
            table {
              border-collapse: separate;
              border-spacing: 0;
              width: 100%;
            }
            th, td {
              padding: 8px 12px;
              text-align: center;
              border-bottom: 1px solid var(--divider-color, #333);
              white-space: nowrap;
              font-size: 0.95em;
            }
            th.row-head, td.row-head {
              text-align: left;
              color: var(--secondary-text-color);
              font-weight: 500;
              position: sticky;
              left: 0;
              z-index: 2;
              background-color: var(--ha-card-background, var(--card-background-color, #1c1c1c));
              box-shadow: 2px 0 4px -2px rgba(0, 0, 0, 0.4);
            }
            thead th {
              color: var(--secondary-text-color);
              font-weight: 500;
              border-bottom: 1px solid var(--divider-color, #333);
            }
            th.area-head { cursor: context-menu; }
            td.cell { cursor: default; }
            td.cell.clickable { cursor: pointer; }
            td.cell.clickable:hover { background: var(--secondary-background-color); }
            .dot {
              display: inline-block;
              width: 8px;
              height: 8px;
              border-radius: 50%;
              margin-right: 6px;
              vertical-align: middle;
            }
            .dot.on { background: var(--success-color, #4caf50); }
            .dot.off { background: var(--disabled-text-color, #888); }
            .dot.na { background: var(--warning-color, #ff9800); }
            .missing { color: var(--disabled-text-color, #888); opacity: 0.6; }
            .empty {
              padding: 24px 16px;
              color: var(--secondary-text-color);
              text-align: center;
            }
            .hidden-note {
              padding: 0 16px 12px 16px;
              color: var(--secondary-text-color);
              opacity: 0.7;
              font-size: 0.8em;
            }
            .sort-toggle {
              display: inline-flex;
              border: 1px solid var(--divider-color, #555);
              border-radius: 6px;
              overflow: hidden;
              font-weight: 400;
            }
            .sort-toggle button {
              border: none;
              background: transparent;
              color: var(--secondary-text-color);
              padding: 3px 8px;
              font-size: 0.75em;
              cursor: pointer;
              font-family: inherit;
            }
            .sort-toggle button + button { border-left: 1px solid var(--divider-color, #555); }
            .sort-toggle button.active {
              background: var(--primary-color, #03a9f4);
              color: var(--text-primary-color, #fff);
            }
            ha-icon-button.spin { animation: lmc-spin 1s linear infinite; }
            @keyframes lmc-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
          </style>
          <ha-card>
            <div class="header">
              <div class="title"></div>
              <ha-icon-button></ha-icon-button>
            </div>
            <div class="wrap"></div>
            <div class="hidden-note"></div>
          </ha-card>
        `;
        this.shadowRoot
          .querySelector("ha-icon-button")
          .addEventListener("click", () => this._forceRecheck());
      }

      const titleEl = this.shadowRoot.querySelector(".title");
      titleEl.textContent = this._config.title || "Label Master Control";

      const refreshBtn = this.shadowRoot.querySelector("ha-icon-button");
      refreshBtn.label = "Recheck everything (also un-hides right-click-hidden Areas)";
      refreshBtn.path =
        "M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z";
      refreshBtn.classList.toggle("spin", this._checking);

      const wrap = this.shadowRoot.querySelector(".wrap");
      const hiddenNote = this.shadowRoot.querySelector(".hidden-note");

      const snapshot = this._forcedSnapshot || liveEntitiesFrom(this._hass);
      const { cells, areas: allAreas } = buildMatrix(
        this._categories,
        snapshot.entities,
        snapshot.devicesById,
        snapshot.areasById,
        this._hass.states
      );

      const configHidden = this._configHiddenAreas();
      const areas = allAreas.filter(
        (a) => !configHidden.includes(a) && !this._locallyHidden.has(a)
      );
      const hiddenCount = allAreas.length - areas.length;
      hiddenNote.textContent = hiddenCount
        ? `${hiddenCount} of ${allAreas.length} Areas hidden - right-click hides, Recheck (↻) un-hides right-click-hidden ones, the card editor manages permanent hides.`
        : "";

      if (allAreas.length === 0) {
        wrap.innerHTML = `<div class="empty">No Label Master Control devices found yet. Build one with the Label Master Control wizard to see it here.</div>`;
        return;
      }
      if (areas.length === 0) {
        wrap.innerHTML = `<div class="empty">Every Area is hidden right now. Click Recheck (↻) to show right-click-hidden Areas again, or edit the card to un-hide one permanently.</div>`;
        return;
      }

      const rows = buildRows(this._categories, this._sortMode);

      let html = `<table><thead><tr><th class="row-head">
        <span class="sort-toggle">
          <button type="button" data-mode="domain">Domain</button><button type="button" data-mode="label">Labels</button>
        </span>
      </th>`;
      areas.forEach((area) => {
        html += `<th class="area-head" data-area="${this._escape(area)}" title="Right-click to hide">${this._escape(
          area
        )}</th>`;
      });
      html += "</tr></thead><tbody>";

      rows.forEach((row) => {
        html += `<tr><td class="row-head">${this._escape(row.label)}</td>`;
        areas.forEach((area) => {
          const cell = cells.get(`${row.category}|${row.domain}|${area}`);
          if (!cell) {
            html += `<td class="cell missing">–</td>`;
            return;
          }
          const state = cell.state;
          let dotClass = "off";
          let text = "Off";
          if (state === "on") {
            dotClass = "on";
            text = "On";
          } else if (state === "unavailable") {
            dotClass = "na";
            text = "Unavailable";
          } else if (state === "unknown" || state == null) {
            dotClass = "na";
            text = "Unknown";
          }
          html += `<td class="cell clickable" data-entity="${this._escape(
            cell.entityId
          )}" title="${this._escape(cell.entityId)}"><span class="dot ${dotClass}"></span>${text}</td>`;
        });
        html += "</tr>";
      });
      html += "</tbody></table>";

      wrap.innerHTML = html;
      wrap.querySelectorAll("td.cell.clickable").forEach((td) => {
        td.addEventListener("click", () => this._onCellClick(td.dataset.entity));
      });
      wrap.querySelectorAll("th.area-head").forEach((th) => {
        th.addEventListener("contextmenu", (ev) => this._onAreaHeaderContextMenu(ev, th.dataset.area));
      });
      wrap.querySelectorAll(".sort-toggle button").forEach((btn) => {
        btn.classList.toggle("active", btn.dataset.mode === this._sortMode);
        btn.addEventListener("click", () => this._setSortMode(btn.dataset.mode));
      });
    }

    _escape(str) {
      const div = document.createElement("div");
      div.textContent = String(str);
      return div.innerHTML;
    }
  }

  class HaLabelMasterControlCardEditor extends HTMLElement {
    setConfig(config) {
      this._config = config || {};
      this._render();
    }

    set hass(hass) {
      this._hass = hass;
      this._render();
    }

    _knownAreas() {
      if (!this._hass) return [];
      const categories = parseCategories(this._config.categories);
      const snapshot = liveEntitiesFrom(this._hass);
      const { areas } = buildMatrix(
        categories,
        snapshot.entities,
        snapshot.devicesById,
        snapshot.areasById,
        this._hass.states
      );
      return areas;
    }

    _toggleHiddenArea(areaName, hide) {
      const current = new Set(
        Array.isArray(this._config.hidden_areas) ? this._config.hidden_areas : []
      );
      if (hide) {
        current.add(areaName);
      } else {
        current.delete(areaName);
      }
      this._config = { ...this._config, hidden_areas: Array.from(current) };
      this._fireChanged();
      this._render();
    }

    _render() {
      this._config = this._config || {};
      if (!this._hass) return;

      if (!this.shadowRoot) {
        this.attachShadow({ mode: "open" });
        this.shadowRoot.innerHTML = `
          <style>
            .wrap { padding: 12px 0; display: flex; flex-direction: column; gap: 12px; }
            label {
              display: flex;
              flex-direction: column;
              gap: 4px;
              font-size: 0.9em;
              color: var(--secondary-text-color);
            }
            input[type="text"] {
              padding: 8px;
              border-radius: 4px;
              border: 1px solid var(--divider-color, #ccc);
              background: var(--card-background-color, transparent);
              color: inherit;
              font: inherit;
            }
            .hint { font-size: 0.8em; color: var(--secondary-text-color); opacity: 0.8; }
            .areas-list {
              display: flex;
              flex-direction: column;
              gap: 6px;
              border: 1px solid var(--divider-color, #ccc);
              border-radius: 4px;
              padding: 8px 12px;
            }
            .areas-list .row {
              display: flex;
              align-items: center;
              gap: 8px;
              font-size: 0.9em;
            }
            .areas-list .empty {
              font-size: 0.85em;
              color: var(--secondary-text-color);
              opacity: 0.8;
            }
            .version {
              text-align: center;
              font-size: 0.7em;
              color: var(--secondary-text-color);
              opacity: 0.6;
              margin-top: 4px;
            }
          </style>
          <div class="wrap">
            <label>
              <span>Title</span>
              <input id="title" type="text" placeholder="Label Master Control" />
            </label>
            <label>
              <span>Category labels (comma separated, matched case-insensitively)</span>
              <input id="categories" type="text" placeholder="Default, Extra" />
            </label>
            <label>
              <span>Areas shown (unchecked = hidden permanently, for everyone viewing this dashboard)</span>
              <div class="areas-list"></div>
            </label>
            <div class="hint">Rows are category × domain (light/switch/fan) - a Domain/Labels toggle on the card itself (top-left of the table) controls whether rows group by domain or by category first; that toggle and right-clicking an Area's column header are both quick, per-browser settings remembered in this browser only, separate from the permanent list above and unaffected by it. Nothing here can add or edit devices - build those with Label Master Control's own wizard.</div>
            <div class="version"></div>
          </div>
        `;
        this._titleInput = this.shadowRoot.getElementById("title");
        this._categoriesInput = this.shadowRoot.getElementById("categories");

        this._titleInput.addEventListener("change", () => {
          this._config = { ...this._config, title: this._titleInput.value };
          this._fireChanged();
        });
        this._categoriesInput.addEventListener("change", () => {
          this._config = { ...this._config, categories: this._categoriesInput.value };
          this._fireChanged();
          this._render();
        });
        this.shadowRoot.querySelector(".version").textContent = `v${CARD_VERSION}`;
      }

      const focused = this.shadowRoot.activeElement;
      if (this._titleInput !== focused) {
        this._titleInput.value = this._config.title || "";
      }
      if (this._categoriesInput !== focused) {
        this._categoriesInput.value = this._config.categories || "";
      }

      const areasListEl = this.shadowRoot.querySelector(".areas-list");
      const areas = this._knownAreas();
      const hidden = new Set(
        Array.isArray(this._config.hidden_areas) ? this._config.hidden_areas : []
      );

      if (areas.length === 0) {
        areasListEl.innerHTML = `<div class="empty">No Areas found yet - build a Label Master Control device first.</div>`;
        return;
      }

      areasListEl.innerHTML = areas
        .map(
          (area) => `
            <div class="row">
              <input type="checkbox" data-area="${this._escape(area)}" ${
                hidden.has(area) ? "" : "checked"
              } />
              <span>${this._escape(area)}</span>
            </div>
          `
        )
        .join("");
      areasListEl.querySelectorAll("input[type=checkbox]").forEach((cb) => {
        cb.addEventListener("change", () => {
          this._toggleHiddenArea(cb.dataset.area, !cb.checked);
        });
      });
    }

    _escape(str) {
      const div = document.createElement("div");
      div.textContent = String(str);
      return div.innerHTML;
    }

    _fireChanged() {
      const event = new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true,
      });
      this.dispatchEvent(event);
    }
  }

  if (!customElements.get(EDITOR_TAG)) {
    customElements.define(EDITOR_TAG, HaLabelMasterControlCardEditor);
  }
  if (!customElements.get(CARD_TAG)) {
    customElements.define(CARD_TAG, HaLabelMasterControlCard);
  }

  window.customCards = window.customCards || [];
  window.customCards.push({
    type: CARD_TAG,
    name: "Label Master Control Card",
    description: "Read-only status matrix of your Label Master Control devices, by category and Area.",
  });
})();
