/**
 * Label Master Control - Matrix Card
 *
 * Read-only status grid: one row per category+domain combo (e.g. "Default
 * Light", "Extra Fan"), one column per Area, one cell per Label Master
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
  const CARD_VERSION = "2026.09.20.04";

  const DOMAINS = ["light", "switch", "fan"];
  const DEFAULT_CATEGORIES = ["Default", "Extra"];
  const NO_AREA_LABEL = "No Area";

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
      cells.set(key, { entityId, state: states[entityId] });
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

    async _forceRecheck() {
      if (!this._hass || this._checking) return;
      this._checking = true;
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

    _render() {
      if (!this._hass) return;
      this._config = this._config || {};
      this._categories = this._categories || parseCategories(this._config.categories);

      if (!this.shadowRoot) {
        this.attachShadow({ mode: "open" });
        this.shadowRoot.innerHTML = `
          <style>
            ha-card { padding: 0; }
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
            table { border-collapse: collapse; width: 100%; }
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
              background: var(--card-background-color, var(--ha-card-background));
            }
            thead th {
              color: var(--secondary-text-color);
              font-weight: 500;
              border-bottom: 1px solid var(--divider-color, #333);
            }
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
            .dot.on { background: var(--state-icon-active-color, #f5a623); }
            .dot.off { background: var(--disabled-text-color, #888); }
            .dot.na { background: var(--error-color, #db4437); opacity: 0.6; }
            .missing { color: var(--disabled-text-color, #888); opacity: 0.6; }
            .empty {
              padding: 24px 16px;
              color: var(--secondary-text-color);
              text-align: center;
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
          </ha-card>
        `;
        this.shadowRoot
          .querySelector("ha-icon-button")
          .addEventListener("click", () => this._forceRecheck());
      }

      const titleEl = this.shadowRoot.querySelector(".title");
      titleEl.textContent = this._config.title || "Label Master Control";

      const refreshBtn = this.shadowRoot.querySelector("ha-icon-button");
      refreshBtn.label = "Recheck everything";
      refreshBtn.path =
        "M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z";
      refreshBtn.classList.toggle("spin", this._checking);

      const wrap = this.shadowRoot.querySelector(".wrap");

      const snapshot = this._forcedSnapshot || liveEntitiesFrom(this._hass);
      const { cells, areas } = buildMatrix(
        this._categories,
        snapshot.entities,
        snapshot.devicesById,
        snapshot.areasById,
        this._hass.states
      );

      if (areas.length === 0) {
        wrap.innerHTML = `<div class="empty">No Label Master Control devices found yet. Build one with the Label Master Control wizard to see it here.</div>`;
        return;
      }

      const rows = [];
      this._categories.forEach((category) => {
        DOMAINS.forEach((domain) => {
          rows.push({ category, domain, label: `${category} ${titleCase(domain)}` });
        });
      });

      let html = "<table><thead><tr><th class=\"row-head\"></th>";
      areas.forEach((area) => {
        html += `<th>${this._escape(area)}</th>`;
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
            input {
              padding: 8px;
              border-radius: 4px;
              border: 1px solid var(--divider-color, #ccc);
              background: var(--card-background-color, transparent);
              color: inherit;
              font: inherit;
            }
            .hint { font-size: 0.8em; color: var(--secondary-text-color); opacity: 0.8; }
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
            <div class="hint">Each row is one category × domain (light/switch/fan). Columns are whatever Areas your Label Master Control devices are already assigned to. Nothing here can add or edit devices - build those with Label Master Control's own wizard.</div>
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
