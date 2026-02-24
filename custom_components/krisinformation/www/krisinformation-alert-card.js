/*
 * Krisinformation Alert Card
 * @license MIT (c) 2025 Niklas V
 */

// Använd HA:s inbyggda Lit om tillgängligt, annars fallback till CDN
const getLit = async () => {
  // Home Assistant 2023.4+ exponerar Lit globalt
  if (window.LitElement && window.litHtml) {
    return {
      LitElement: window.LitElement,
      html: window.litHtml.html,
      css: window.litHtml.css,
    };
  }
  // Fallback för äldre HA-versioner eller fristående testning
  return import('https://unpkg.com/lit@3.1.0?module');
};

const { LitElement, html, css } = await getLit();

class KrisinformationAlertCard extends LitElement {
  static properties = {
    hass: {},
    config: {},
    _expanded: {},
  };

  static styles = css`
    :host {
      /* Strength of the severity-tinted background when enabled (used in color-mix) */
      --kris-alert-bg-strong: 22%;
      --kris-alert-bg-soft: 12%;
      /* Optical vertical adjustment for the title in compact (1-row) mode */
      --kris-alert-compact-title-offset: 2px;
      /* Outer horizontal padding for the list (set to 0 to align with other cards) */
      --kris-alert-outer-padding: 0px;
      display: block;
    }

    ha-card {
      /* Keep the container tight so stacking multiple transparent cards doesn't show "gaps" */
      padding: 0;
      background: transparent;
      box-shadow: none;
      border: none;
      --ha-card-background: transparent;
      --ha-card-border-width: 0;
      --ha-card-border-color: transparent;
    }
    .alerts {
      display: flex;
      flex-direction: column;
      gap: 8px;
      /* No vertical padding: otherwise it becomes visible whitespace between stacked cards */
      padding: 0 var(--kris-alert-outer-padding, 0px);
    }
    .alert {
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 12px;
      align-items: start;
      padding: 12px;
      border-radius: var(--kris-alert-border-radius, 8px);
      border: 1px solid var(--divider-color);
      background: var(--card-background-color);
      position: relative;
    }
    /* Compact (single-line) layout: vertically center the whole row */
    .alert.compact {
      align-items: center;
    }

    /* Optional severity-tinted background (keeps normal card background as base) */
    .alert.bg-severity {
      background: linear-gradient(
          90deg,
          color-mix(in srgb, var(--kris-accent) var(--kris-alert-bg-strong, 22%), var(--card-background-color)) 0%,
          color-mix(in srgb, var(--kris-accent) var(--kris-alert-bg-soft, 12%), var(--card-background-color)) 55%,
          var(--card-background-color) 100%
        );
    }
    .alert::before {
      content: '';
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      width: 4px;
      border-top-left-radius: inherit;
      border-bottom-left-radius: inherit;
      background: var(--kris-accent, var(--primary-color));
    }
    .alert.sev-minor { --kris-accent: var(--kris-alert-yellow, #f1c40f); }
    .alert.sev-moderate { --kris-accent: var(--kris-alert-orange, #e67e22); }
    .alert.sev-severe { --kris-accent: var(--kris-alert-red, var(--error-color, #e74c3c)); }
    .alert.sev-extreme { --kris-accent: var(--kris-alert-red, var(--error-color, #e74c3c)); }
    .alert.sev-unknown { --kris-accent: var(--primary-color); }

    .icon {
      width: 32px;
      height: 32px;
      margin-inline-start: 4px;
      margin-top: 2px;
      color: var(--kris-icon-color, var(--primary-color));
    }
    .icon-col {
      display: flex;
      align-items: flex-start;
    }
    .icon-col.compact {
      align-items: center;
    }
    .content {
      display: flex;
      flex-direction: column;
      gap: 4px;
      min-width: 0;
    }
    .content {
      align-self: stretch;
    }
    /* In compact layout, don't stretch the content; let the grid center it precisely */
    .content.compact {
      align-self: center;
    }
    .title {
      display: flex;
      gap: 8px;
      align-items: center;
      min-width: 0;
    }
    .headline {
      font-weight: 600;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      flex: 1 1 auto;
      min-width: 0;
    }
    /* In compact mode, apply a tiny optical offset so the text looks centered */
    .headline.compact {
      transform: translateY(var(--kris-alert-compact-title-offset, 2px));
      line-height: 1;
    }
    .meta {
      color: var(--secondary-text-color);
      font-size: 0.9em;
      display: flex;
      flex-wrap: wrap;
      gap: 8px 12px;
    }
    .details { margin-top: 6px; }
    .details-toggle {
      color: var(--primary-color);
      cursor: pointer;
      user-select: none;
      font-size: 0.95em;
    }
    .toggle-col {
      display: flex;
      justify-content: flex-end;
      align-items: center;
      margin-left: auto;
    }
    .toggle-col.compact {
      align-items: center;
    }
    /* Compact toggle when placed in the right column (prevents it from consuming an extra line) */
    .details-toggle.compact {
      margin: 0;
      font-size: 0.9em;
      white-space: nowrap;
    }
    .empty {
      color: var(--secondary-text-color);
      padding: 8px var(--kris-alert-outer-padding, 0px);
    }

    /* Editor-only controls */
    .meta-fields { margin: 12px 0; padding: 0 12px; }
    .meta-row { display: grid; grid-template-columns: 1fr auto auto; align-items: center; gap: 8px; padding: 6px 0; }
    .meta-name { color: var(--primary-text-color); }
    .order-actions { display: flex; gap: 6px; }
    .order-btn { background: var(--secondary-background-color); color: var(--primary-text-color); border: 1px solid var(--divider-color); border-radius: 4px; padding: 2px 6px; cursor: pointer; }
    .order-btn[disabled] { opacity: 0.4; cursor: default; }
  `;

  setConfig(config) {
    if (!config?.entity) throw new Error('You must specify an entity.');
    const normalized = this._normalizeConfig(config);
    this.config = normalized;
    this._expanded = {};
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    // Rensa timers för att undvika minnesläckor
    clearTimeout(this._holdTimer);
    clearTimeout(this._tapTimer);
  }

  getCardSize() {
    const header = this._showHeader() ? 1 : 0;

    // Important: HA may call getCardSize() before hass is injected.
    // If we return 0 here, Lovelace can drop the card entirely from the editor UI.
    if (!this.hass) return header + 1;

    const alerts = this._visibleAlerts();
    const count = Array.isArray(alerts) ? alerts.length : 0;

    // When empty (including in editor), reserve at least one row for the empty state.
    return header + (count > 0 ? count : 1);
  }

  /**
   * Sections (grid) view support.
   * Home Assistant uses this to determine the default/min size and to enable the UI "Layout" tab resizing.
   * Each section is 12 columns wide.
   */
  getGridOptions() {
    // Provide only column sizing. Avoid returning `rows` here so Sections can auto-size height
    // based on content (prevents fixed-height behavior and overlap issues when expanding).
    return {
      columns: 12,
      min_columns: 1,
      max_columns: 12,
      // In edit mode + empty state, HA Sections can collapse cards to 0 height unless a min is provided.
      // This keeps the card selectable/movable even when there is no data.
      min_rows: 1,
    };
  }

  _alerts() {
    if (!this.hass || !this.config) return [];
    const stateObj = this.hass.states?.[this.config.entity];
    const raw = stateObj ? stateObj.attributes?.alerts || [] : [];
    return this._normalizeCapAlerts(Array.isArray(raw) ? raw : []);
  }

  _visibleAlerts() {
    const alerts = this._alerts();
    if (!Array.isArray(alerts)) return [];
    const cfg = this.config || {};
    const filterSev = (cfg.filter_severities || []).map((s) => String(s).toLowerCase());
    const filterAreas = (cfg.filter_areas || []).map((s) => String(s).toLowerCase());

    const filtered = alerts.filter((a) => {
      const sev = String(a.severity || '').toLowerCase();
      const area = String(a.area || a.areas || '').toLowerCase();
      const sevOk = filterSev.length === 0 || filterSev.includes(sev);
      const areaOk = filterAreas.length === 0 || filterAreas.some((x) => area.includes(x));
      return sevOk && areaOk;
    });

    const sorted = [...filtered].sort((a, b) => {
      const order = cfg.sort_order || 'time_desc';
      if (order === 'severity_then_time') {
        const as = this._severityRank(a);
        const bs = this._severityRank(b);
        if (as !== bs) return bs - as; // higher first
      } else if (order === 'type_then_time') {
        const ae = String(a.event || '').toLowerCase();
        const be = String(b.event || '').toLowerCase();
        if (ae !== be) return ae.localeCompare(be);
      }
      const at = new Date(a.sent || a.published || 0).getTime();
      const bt = new Date(b.sent || b.published || 0).getTime();
      return bt - at;
    });

    const max = Number(cfg.max_items || 0);
    return max > 0 ? sorted.slice(0, max) : sorted;
  }

  _severityRank(item) {
    const sev = String(item?.severity || '').toLowerCase();
    switch (sev) {
      case 'extreme':
        return 4;
      case 'severe':
        return 3;
      case 'moderate':
        return 2;
      case 'minor':
        return 1;
      default:
        return 0;
    }
  }

  _severityClass(item) {
    const sev = String(item?.severity || '').toLowerCase();
    if (sev === 'minor') return 'sev-minor';
    if (sev === 'moderate') return 'sev-moderate';
    if (sev === 'severe') return 'sev-severe';
    if (sev === 'extreme') return 'sev-extreme';
    return 'sev-unknown';
  }

  _iconTemplate(item) {
    if (this.config.show_icon === false) return html``;
    const icon = this.config.icon || 'mdi:alert-circle-outline';
    const color = this.config.icon_color || '';
    const style = color ? `color:${color}` : '';
    return html`<ha-icon class="icon" style="${style}" icon="${icon}" aria-hidden="true"></ha-icon>`;
  }

  render() {
    if (!this.hass || !this.config) return html``;
    const stateObj = this.hass.states?.[this.config.entity];
    const t = this._t.bind(this);
    const alerts = this._visibleAlerts();

    const header = this._showHeader()
      ? (this.config.title || stateObj?.attributes?.friendly_name || 'Krisinformation')
      : undefined;

    return html`
      <ha-card header=${header}>
        ${alerts.length === 0
          ? html`<div class="empty">${t('no_alerts')}</div>`
          : html`<div class="alerts">${this._renderGrouped(alerts)}</div>`}
      </ha-card>
    `;
  }

  _renderGrouped(alerts) {
    const groupBy = this.config?.group_by || 'none';
    if (groupBy === 'none') {
      return alerts.map((item, idx) => this._renderAlert(item, idx));
    }

    // Build group map based on requested key
    const groups = {};
    const getKey = (a) => {
      if (groupBy === 'area') return a.area || a.areas || '—';
      if (groupBy === 'severity') return (a.severity || 'Unknown');
      if (groupBy === 'type') return (a.event || '—');
      return '—';
    };
    for (const a of alerts) {
      const key = getKey(a);
      if (!groups[key]) groups[key] = [];
      groups[key].push(a);
    }

    // Sort group keys
    let keys = Object.keys(groups);
    if (groupBy === 'severity') {
      keys.sort((ka, kb) => {
        const ra = this._severityRank({ severity: ka });
        const rb = this._severityRank({ severity: kb });
        return rb - ra; // higher severity first
      });
    } else {
      keys.sort((a, b) => String(a).localeCompare(String(b)));
    }

    return keys.map((key) => html`
      <div class="area-group">
        <div class="meta" style="margin: 0;">${key}</div>
        ${groups[key].map((item, idx) => this._renderAlert(item, idx))}
      </div>
    `);
  }

  _renderAlert(item, idx) {
    const t = this._t.bind(this);
    const sevClass = this._severityClass(item);
    const expanded = !!this._expanded[this._alertKey(item, idx)];
    const showIcon = this.config.show_icon !== false;
    const sevBgClass = this.config?.severity_background ? 'bg-severity' : '';

    const metaFields = {
      area: (this.config.show_area !== false && (item.area || item.areas))
        ? html`<span><b>${t('area')}:</b> ${item.area || item.areas}</span>`
        : null,
      type: (this.config.show_type !== false && item.event)
        ? html`<span><b>${t('type')}:</b> ${item.event}</span>`
        : null,
      severity: (this.config.show_severity !== false && item.severity)
        ? html`<span><b>${t('severity')}:</b> ${item.severity}</span>`
        : null,
      sent: (this.config.show_sent !== false && item.sent)
        ? html`<span><b>${t('sent')}:</b> ${this._fmtTs(item.sent)}</span>`
        : null,
    };

    const headline = item.headline || item.event || '';
    const description = item.description || '';
    const detailsText = String(item.details || description || '');
    metaFields.text = (this.config.show_details !== false && detailsText.trim().length > 0)
      ? this._markdown(detailsText)
      : null;

    // Divider-driven meta layout (same concept as smhi-alert-card)
    const defaultOrder = ['area', 'type', 'severity', 'sent', 'divider', 'text'];
    const rawOrder = Array.isArray(this.config.meta_order) && this.config.meta_order.length
      ? this.config.meta_order
      : defaultOrder;
    // Ensure divider and text exist exactly once
    let order = rawOrder.filter((k, i) => rawOrder.indexOf(k) === i);
    if (!order.includes('divider')) order = [...order, 'divider'];
    if (!order.includes('text')) order = [...order, 'text'];

    const dividerIndex = order.indexOf('divider');
    const inlineKeys = dividerIndex >= 0 ? order.slice(0, dividerIndex) : order.filter((k) => k !== 'divider');
    const detailsKeys = dividerIndex >= 0 ? order.slice(dividerIndex + 1) : [];

    const inlineParts = inlineKeys
      .filter((k) => k !== 'text')
      .map((key) => metaFields[key])
      .filter((node) => !!node);
    const inlineTextBlock = inlineKeys.includes('text') ? metaFields.text : null;

    const detailsParts = detailsKeys
      .filter((k) => k !== 'text')
      .map((key) => metaFields[key])
      .filter((node) => !!node);
    const detailsTextBlock = detailsKeys.includes('text') ? metaFields.text : null;

    const hasDetailsContent = (detailsParts.length > 0 || !!detailsTextBlock);
    const canCollapse = this.config.collapse_details !== false; // backward compat; if false, show details content without toggle
    const expandedEffective = canCollapse ? expanded : true;
    const showToggle = canCollapse && hasDetailsContent;
    const isCompact = !expandedEffective && inlineParts.length === 0 && !inlineTextBlock;

    return html`
      <div
        class="alert ${sevClass} ${sevBgClass} ${isCompact ? 'compact' : ''}"
        role="button"
        tabindex="0"
        aria-label="${item.headline || item.event || ''}"
        @pointerdown=${(e) => this._onPointerDown(e)}
        @pointerup=${(e) => this._onPointerUp(e, item)}
        @keydown=${(e) => this._onKeydown(e, item)}
      >
        ${showIcon ? html`<div class="icon-col ${isCompact ? 'compact' : ''}">${this._iconTemplate(item)}</div>` : html``}
        <div class="content ${isCompact ? 'compact' : ''}">
          <div class="title">
            <div class="headline ${isCompact ? 'compact' : ''}">${headline || description || (item.area || item.areas) || ''}</div>
            ${showToggle ? html`
              <div class="toggle-col ${isCompact ? 'compact' : ''}">
                <div
                  class="details-toggle compact"
                  role="button"
                  tabindex="0"
                  aria-expanded="${expandedEffective}"
                  title="${expandedEffective ? t('hide_details') : t('show_details')}"
                  @click=${(e) => this._toggleDetails(e, item, idx)}
                  @pointerdown=${(e) => e.stopPropagation()}
                  @pointerup=${(e) => e.stopPropagation()}
                  @keydown=${(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      this._toggleDetails(e, item, idx);
                    }
                    e.stopPropagation();
                  }}
                >
                  ${expandedEffective ? t('hide_details') : t('show_details')}
                </div>
              </div>
            ` : html``}
          </div>
          ${inlineParts.length > 0 ? html`<div class="meta">${inlineParts}</div>` : html``}
          ${inlineTextBlock ? html`<div class="details">${inlineTextBlock}</div>` : html``}
          ${hasDetailsContent
            ? html`
                <div class="details">
                  ${expandedEffective ? html`
                    ${detailsParts.length > 0 ? html`<div class="meta">${detailsParts}</div>` : html``}
                    ${detailsTextBlock ? html`${detailsTextBlock}` : html``}
                  ` : html``}
                </div>
              `
            : html``}
        </div>
      </div>`;
  }

  _toggleDetails(e, item, idx) {
    e.stopPropagation();
    const key = this._alertKey(item, idx);
    this._expanded = { ...this._expanded, [key]: !this._expanded[key] };
  }

  _onPointerDown(e) {
    if (e.button !== 0) return;
    clearTimeout(this._holdTimer);
    this._holdFired = false;
    this._holdTimer = setTimeout(() => {
      this._holdFired = true;
    }, 500);
  }

  _onPointerUp(e, item) {
    if (e.button !== 0) return;
    clearTimeout(this._holdTimer);
    if (this._holdFired) {
      this._runAction(this.config?.hold_action || this.config?.tap_action || { action: 'more-info' }, item);
      return;
    }
    const now = Date.now();
    if (this._lastTap && now - this._lastTap < 250) {
      this._lastTap = 0;
      this._runAction(this.config?.double_tap_action || this.config?.tap_action || { action: 'more-info' }, item);
    } else {
      this._lastTap = now;
      clearTimeout(this._tapTimer);
      this._tapTimer = setTimeout(() => {
        if (this._lastTap && Date.now() - this._lastTap >= 250) {
          this._lastTap = 0;
          this._runAction(this.config?.tap_action || { action: 'more-info' }, item);
        }
      }, 260);
    }
  }

  _onKeydown(e, item) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      this._runAction(this.config?.tap_action || { action: 'more-info' }, item);
    }
  }

  _alertKey(item, idx) {
    return `${String(item.severity || '')}-${String(item.area || item.areas || '')}-${String(item.sent || item.published || idx)}`;
  }

  _fmtTs(value) {
    return this._formatDate(value);
  }

  _formatDate(value) {
    if (!value) return '';
    const date = this._parseDate(value);
    if (!date) return String(value);
    const locale = (this.hass?.language || this.hass?.locale?.language || 'en').toLowerCase();
    const format = this.config?.date_format || 'locale';
    if (format === 'weekday_time') {
      return this._formatDateParts(
        date,
        locale,
        { weekday: 'long' },
        { hour: '2-digit', minute: '2-digit' },
      );
    }
    if (format === 'day_month_time') {
      return this._formatDateParts(
        date,
        locale,
        { day: 'numeric', month: 'long' },
        { hour: '2-digit', minute: '2-digit' },
      );
    }
    if (format === 'day_month_time_year') {
      return this._formatDateParts(
        date,
        locale,
        { day: 'numeric', month: 'long', year: 'numeric' },
        { hour: '2-digit', minute: '2-digit' },
      );
    }
    return date.toLocaleString(locale);
  }

  _formatDateParts(date, locale, dateOptions, timeOptions) {
    const safeTimeOptions = timeOptions ? { ...timeOptions } : null;
    if (safeTimeOptions && !Object.prototype.hasOwnProperty.call(safeTimeOptions, 'hour12')) {
      safeTimeOptions.hour12 = false;
    }
    const dateStr = dateOptions
      ? new Intl.DateTimeFormat(locale, dateOptions).format(date)
      : '';
    const timeStr = safeTimeOptions
      ? new Intl.DateTimeFormat(locale, safeTimeOptions).format(date)
      : '';
    if (dateStr && timeStr) return `${dateStr} ${timeStr}`;
    return dateStr || timeStr || '';
  }

  _parseDate(value) {
    if (!value) return null;
    if (value instanceof Date) {
      return Number.isNaN(value.getTime()) ? null : value;
    }
    if (typeof value === 'number') {
      const numericDate = new Date(value);
      return Number.isNaN(numericDate.getTime()) ? null : numericDate;
    }
    const raw = String(value).trim();
    if (!raw) return null;
    let normalized = raw;
    if (/^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}/.test(raw)) {
      normalized = raw.replace(' ', 'T');
    }
    const parsed = new Date(normalized);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

  _showHeader() {
    return this.config?.show_header !== false;
  }

  shouldUpdate(changed) {
    if (changed.has('config')) return true;
    if (changed.has('hass')) {
      const alerts = this._alerts();
      const key = JSON.stringify(
        alerts?.map((m) => [
          m.severity,
          m.area || m.areas,
          m.sent,
          m.published,
          m.event,
          m.headline,
          m.description,
          m.details,
        ])
      );
      if (this._lastKey !== key) {
        this._lastKey = key;
        return true;
      }
      return false;
    }
    return true;
  }

  _t(key) {
    const lang = (this.hass?.language || this.hass?.locale?.language || 'en').toLowerCase();
    const dict = {
      en: {
        no_alerts: 'No alerts',
        area: 'Area',
        type: 'Type',
        severity: 'Severity',
        sent: 'Sent',
        show_details: 'Show details',
        hide_details: 'Hide details',
        unknown: 'Unknown',
      },
      sv: {
        no_alerts: 'Inga varningar',
        area: 'Område',
        type: 'Typ',
        severity: 'Allvarlighetsgrad',
        sent: 'Skickat',
        show_details: 'Visa detaljer',
        hide_details: 'Dölj detaljer',
        unknown: 'Okänt',
      },
    };
    return (dict[lang] || dict.en)[key] || key;
  }

  _markdown(content) {
    const text = String(content || '');
    try {
      // If ha-markdown is available, use it. Set both property and attribute to be safe.
      // eslint-disable-next-line no-undef
      if (customElements && customElements.get && customElements.get('ha-markdown')) {
        return html`<ha-markdown breaks .content=${text} content=${text}></ha-markdown>`;
      }
    } catch (_) {
      // ignore and fallback
    }
    return html`<div class="details-text">${text}</div>`;
  }

  // Normalize alerts coming from CAP-like structure to the card's expected shape
  _normalizeCapAlerts(alerts) {
    if (!Array.isArray(alerts)) return [];
    const langPref = (this.hass?.language || this.hass?.locale?.language || 'sv').toLowerCase();
    return alerts
      .map((a) => {
        // If it's already in the expected shape (legacy), keep as-is with a small area normalization
        if (!this._isCapAlert(a)) {
          const area = a.area || a.areas || '';
          return { ...a, area, areas: area };
        }

        const info = this._pickInfo(a.info, langPref);
        const areaList = Array.isArray(info?.area) ? info.area : [];
        const areaNames = this._joinUnique(areaList.map((x) => this._stringOrEmpty(x?.areaDesc)));
        const areaStr = areaNames.join(', ');
        const headline = this._stringOrEmpty(info?.headline);
        const description = this._stringOrEmpty(info?.description);
        const instruction = this._stringOrEmpty(info?.instruction);
        const detailsParts = [];
        if (description) detailsParts.push(description);
        if (instruction) detailsParts.push(instruction);
        if (info?.web) detailsParts.push(String(info.web));

        return {
          // primary fields used by the card
          severity: this._stringOrEmpty(info?.severity) || 'Unknown',
          event: this._stringOrEmpty(info?.event),
          area: areaStr,
          areas: areaStr,
          sent: a.sent || info?.sent || info?.effective || info?.onset || null,
          published: a.sent || info?.effective || info?.onset || null,
          headline,
          description,
          details: detailsParts.join('\n\n'),
          // optional extras preserved for future use
          identifier: a.identifier,
          url: info?.web || null,
          source: a.sender || null,
          expires: info?.expires || null,
          urgency: info?.urgency || null,
          certainty: info?.certainty || null,
        };
      })
      .filter((x) => x && (x.severity || x.event || x.area || x.details || x.description));
  }

  _isCapAlert(a) {
    if (!a || typeof a !== 'object') return false;
    // Heuristic: CAP alert objects have top-level fields like 'identifier', 'sender', 'msgType', and nested 'info'
    return !!(a.info || a.msgType || a.sender || a.identifier);
  }

  _pickInfo(info, langPref) {
    if (!info) return {};
    if (Array.isArray(info)) {
      const lp = String(langPref || '').toLowerCase();
      const candidates = [lp, lp.split('-')[0], 'sv-se', 'sv', 'en-us', 'en'];
      for (const c of candidates) {
        const found = info.find((i) => String(i?.language || '').toLowerCase() === c);
        if (found) return found;
      }
      return info[0] || {};
    }
    return info || {};
  }

  _stringOrEmpty(v) {
    return v == null ? '' : String(v);
  }

  _joinUnique(list) {
    const set = new Set();
    for (const item of list || []) {
      const s = this._stringOrEmpty(item).trim();
      if (s) set.add(s);
    }
    return Array.from(set);
  }

  _normalizeConfig(config) {
    const normalized = { ...config };
    // Backwards compatibility
    if (normalized.show_areas !== undefined && normalized.show_area === undefined) {
      normalized.show_area = normalized.show_areas;
    }
    // Defaults
    if (normalized.show_header === undefined) normalized.show_header = true;
    if (normalized.show_icon === undefined) normalized.show_icon = true;
    if (normalized.severity_background === undefined) normalized.severity_background = false;
    if (normalized.max_items === undefined) normalized.max_items = 0;
    if (normalized.sort_order === undefined) normalized.sort_order = 'time_desc';
    if (normalized.date_format === undefined) normalized.date_format = 'locale';
    if (normalized.group_by === undefined) normalized.group_by = 'none';
    const allowedDateFormats = ['locale', 'day_month_time', 'weekday_time', 'day_month_time_year'];
    if (!allowedDateFormats.includes(normalized.date_format)) {
      normalized.date_format = 'locale';
    }
    if (!Array.isArray(normalized.filter_severities)) normalized.filter_severities = [];
    if (!Array.isArray(normalized.filter_areas)) normalized.filter_areas = [];
    if (normalized.collapse_details === undefined) normalized.collapse_details = true;
    if (normalized.show_area === undefined) normalized.show_area = true;
    if (normalized.show_type === undefined) normalized.show_type = true;
    if (normalized.show_severity === undefined) normalized.show_severity = true;
    if (normalized.show_sent === undefined) normalized.show_sent = true;
    if (normalized.show_details === undefined) normalized.show_details = true;
    // Back-compat: if legacy show_description was set, treat it as show_details
    if (normalized.show_details === undefined && normalized.show_description !== undefined) {
      normalized.show_details = normalized.show_description;
    }
    // Remove legacy field from normalized config to avoid confusion
    if (Object.prototype.hasOwnProperty.call(normalized, 'show_description')) {
      delete normalized.show_description;
    }
    if (Object.prototype.hasOwnProperty.call(normalized, 'hide_when_empty')) delete normalized.hide_when_empty;
    if (normalized.show_border === undefined) normalized.show_border = true; // compat, but unused
    if (!Array.isArray(normalized.meta_order) || normalized.meta_order.length === 0) {
      // Default to putting text in the details section (after divider)
      normalized.meta_order = ['area', 'type', 'severity', 'sent', 'divider', 'text'];
    } else {
      // Ensure divider and text exist
      if (!normalized.meta_order.includes('divider')) normalized.meta_order = [...normalized.meta_order, 'divider'];
      if (!normalized.meta_order.includes('text')) normalized.meta_order = [...normalized.meta_order, 'text'];
    }
    return normalized;
  }

  static getConfigElement() {
    return document.createElement('krisinformation-alert-card-editor');
  }

  static getStubConfig(hass, entities) {
    return {
      entity: (entities || []).find((e) => e && e.startsWith('sensor.')) || '',
      title: '',
      show_header: true,
      show_icon: true,
      severity_background: false,
      icon: 'mdi:alert-circle-outline',
      max_items: 0,
      sort_order: 'time_desc',
      date_format: 'locale',
      group_by: 'none',
      filter_severities: [],
      filter_areas: [],
      collapse_details: true,
      show_area: true,
      show_type: true,
      show_severity: true,
      show_sent: true,
      show_details: true,
      // collapse inferred by divider; default puts text in details (after divider)
      meta_order: ['area', 'type', 'severity', 'sent', 'divider', 'text'],
    };
  }
}

if (!customElements.get('krisinformation-alert-card')) {
  customElements.define('krisinformation-alert-card', KrisinformationAlertCard);
}

class KrisinformationAlertCardEditor extends LitElement {
  static properties = {
    hass: {},
    _config: {},
  };

  static styles = css`
    .container { padding: 8px 0 0 0; }
    .meta-fields { margin: 12px 0; padding: 8px 12px; }
    .meta-fields-title { color: var(--secondary-text-color); margin-bottom: 6px; }
    .meta-row { display: grid; grid-template-columns: 1fr auto auto; align-items: center; gap: 8px; padding: 6px 0; }
    .meta-name { color: var(--primary-text-color); }
    .order-actions { display: flex; gap: 6px; }
    .order-btn { background: var(--secondary-background-color); color: var(--primary-text-color); border: 1px solid var(--divider-color); border-radius: 4px; padding: 2px 6px; cursor: pointer; }
    .order-btn[disabled] { opacity: 0.4; cursor: default; }
    .meta-divider-row { display: grid; grid-template-columns: 1fr auto; align-items: center; gap: 8px; padding: 6px 0; color: var(--secondary-text-color); }
    .meta-divider {
      height: 0;
      border-top: 1px dashed var(--divider-color);
      margin: 6px 0 0 0;
    }
  `;

  setConfig(config) {
    this._config = config;
  }

  render() {
    if (!this.hass || !this._config) return html``;
    const lang = (this.hass?.language || this.hass?.locale?.language || 'en').toLowerCase();
    const dateFormatOptions = lang.startsWith('sv')
      ? [
          { value: 'locale', label: 'Systemstandard' },
          { value: 'day_month_time', label: '14 januari 13:00' },
          { value: 'weekday_time', label: 'Onsdag 13:00' },
          { value: 'day_month_time_year', label: '14 januari 2026 13:00' },
        ]
      : [
          { value: 'locale', label: 'System default' },
          { value: 'day_month_time', label: '14 January 13:00' },
          { value: 'weekday_time', label: 'Wednesday 13:00' },
          { value: 'day_month_time_year', label: '14 January 2026 13:00' },
        ];
    const dateFormatLabel = lang.startsWith('sv') ? 'Datumformat' : 'Date format';
    const schema = [
      { name: 'entity', label: 'Entity', required: true, selector: { entity: { domain: 'sensor' } } },
      { name: 'title', label: 'Title', selector: { text: {} } },
      { name: 'show_header', label: 'Show header', selector: { boolean: {} } },
      { name: 'show_icon', label: 'Show icon', selector: { boolean: {} } },
      { name: 'severity_background', label: 'Severity background', selector: { boolean: {} } },
      { name: 'icon', label: 'Icon (mdi:...)', selector: { text: {} } },
      { name: 'icon_color', label: 'Icon color (CSS)', selector: { text: {} } },
      { name: 'max_items', label: 'Max items', selector: { number: { min: 0, mode: 'box' } } },
      { name: 'sort_order', label: 'Sort order', selector: { select: { mode: 'dropdown', options: [
        { value: 'time_desc', label: 'Time (newest first)' },
        { value: 'severity_then_time', label: 'Severity then time' },
        { value: 'type_then_time', label: 'Type then time' },
      ] } } },
      { name: 'date_format', label: dateFormatLabel, selector: { select: { mode: 'dropdown', options: dateFormatOptions } } },
      { name: 'group_by', label: 'Group by', selector: { select: { mode: 'dropdown', options: [
        { value: 'none', label: 'No grouping' },
        { value: 'area', label: 'By area' },
        { value: 'severity', label: 'By severity' },
        { value: 'type', label: 'By type' },
      ] } } },
      { name: 'filter_severities', label: 'Filter severities', selector: { select: { multiple: true, options: [
        { value: 'Minor', label: 'Minor' },
        { value: 'Moderate', label: 'Moderate' },
        { value: 'Severe', label: 'Severe' },
        { value: 'Extreme', label: 'Extreme' },
        { value: 'Unknown', label: 'Unknown' },
      ] } } },
      { name: 'filter_areas', label: 'Filter areas (comma-separated)', selector: { text: {} } },
      { name: 'collapse_details', label: 'Collapse details', selector: { boolean: {} } },
      // show_details is controlled as a meta toggle (text)
      // actions (use ui_action selector like in smhi-alert-card)
      { name: 'tap_action', label: 'Tap action', selector: { ui_action: {} } },
      { name: 'double_tap_action', label: 'Double tap action', selector: { ui_action: {} } },
      { name: 'hold_action', label: 'Hold action', selector: { ui_action: {} } },
    ];

    const data = {
      entity: this._config.entity || '',
      title: this._config.title || '',
      show_header: this._config.show_header !== undefined ? this._config.show_header : true,
      show_icon: this._config.show_icon !== undefined ? this._config.show_icon : true,
      severity_background: this._config.severity_background !== undefined ? this._config.severity_background : false,
      icon: this._config.icon || 'mdi:alert-circle-outline',
      icon_color: this._config.icon_color || '',
      max_items: this._config.max_items ?? 0,
      sort_order: this._config.sort_order || 'time_desc',
      date_format: this._config.date_format || 'locale',
      group_by: this._config.group_by || 'none',
      filter_severities: this._config.filter_severities || [],
      filter_areas: (this._config.filter_areas || []).join(', '),
      collapse_details: this._config.collapse_details !== undefined ? this._config.collapse_details : true,
      show_area: this._config.show_area !== undefined ? this._config.show_area : true,
      show_type: this._config.show_type !== undefined ? this._config.show_type : true,
      show_severity: this._config.show_severity !== undefined ? this._config.show_severity : true,
      show_sent: this._config.show_sent !== undefined ? this._config.show_sent : true,
      show_details: this._config.show_details !== undefined ? this._config.show_details : true,
      tap_action: this._config.tap_action || {},
      double_tap_action: this._config.double_tap_action || {},
      hold_action: this._config.hold_action || {},
    };

    const allowed = ['area','type','severity','sent'];
    const special = ['divider','text'];
    const allowedWithSpecial = [...allowed, ...special];
    const currentOrderRaw = (this._config.meta_order && Array.isArray(this._config.meta_order) && this._config.meta_order.length)
      ? this._config.meta_order.filter((k) => allowedWithSpecial.includes(k))
      : ['area','type','severity','sent','divider','text'];
    // ensure presence
    let currentOrder = [...currentOrderRaw];
    if (!currentOrder.includes('divider')) currentOrder.push('divider');
    if (!currentOrder.includes('text')) currentOrder.push('text');
    const filledOrder = [...currentOrder, ...allowedWithSpecial.filter((k) => !currentOrder.includes(k))];

    const schemaTop = schema.filter((s) => !['tap_action','double_tap_action','hold_action'].includes(s.name));
    const schemaActions = schema.filter((s) => ['tap_action','double_tap_action','hold_action'].includes(s.name));

    return html`
      <div class="container">
        <ha-form
          .hass=${this.hass}
          .data=${data}
          .schema=${schemaTop}
          .computeLabel=${this._computeLabel}
          @value-changed=${this._valueChanged}
        ></ha-form>
        <div class="meta-fields">
          ${filledOrder.map((key, index) => {
            if (key === 'divider') {
              return html`
                <ha-settings-row class="meta-divider-row">
                  <span slot="heading">— Details —</span>
                  <div class="order-actions">
                    <mwc-icon-button @click=${() => this._moveMeta(key, -1)} .disabled=${index === 0} aria-label="Move up">
                      <ha-icon icon="mdi:chevron-up"></ha-icon>
                    </mwc-icon-button>
                    <mwc-icon-button @click=${() => this._moveMeta(key, 1)} .disabled=${index === filledOrder.length - 1} aria-label="Move down">
                      <ha-icon icon="mdi:chevron-down"></ha-icon>
                    </mwc-icon-button>
                  </div>
                  <div class="meta-divider"></div>
                </ha-settings-row>
              `;
            }
            return html`
              <ha-settings-row class="meta-row">
                <span slot="heading">${this._labelForMeta(key)}</span>
                <span slot="description"></span>
                <div class="order-actions">
                  <mwc-icon-button @click=${() => this._moveMeta(key, -1)} .disabled=${index === 0} aria-label="Move up">
                    <ha-icon icon="mdi:chevron-up"></ha-icon>
                  </mwc-icon-button>
                  <mwc-icon-button @click=${() => this._moveMeta(key, 1)} .disabled=${index === filledOrder.length - 1} aria-label="Move down">
                    <ha-icon icon="mdi:chevron-down"></ha-icon>
                  </mwc-icon-button>
                </div>
                <ha-switch
                  .checked=${this._isMetaShown(key)}
                  @change=${(e) => this._toggleMeta(key, e)}
                ></ha-switch>
              </ha-settings-row>`;
          })}
        </div>
        <ha-form
          .hass=${this.hass}
          .data=${data}
          .schema=${schemaActions}
          .computeLabel=${this._computeLabel}
          @value-changed=${this._valueChanged}
        ></ha-form>
      </div>
    `;
  }

  _valueChanged = (ev) => {
    if (!this._config || !this.hass) return;
    const value = ev.detail?.value || {};
    const next = { ...this._config, ...value };
    if (typeof next.filter_areas === 'string') {
      next.filter_areas = next.filter_areas
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
    }
    this._config = next;
    this.dispatchEvent(new CustomEvent('config-changed', { detail: { config: next } }));
  };

  _isMetaShown(key) {
    if (key === 'area') return this._config.show_area !== false;
    if (key === 'type') return this._config.show_type !== false;
    if (key === 'severity') return this._config.show_severity !== false;
    if (key === 'sent') return this._config.show_sent !== false;
    if (key === 'text') return this._config.show_details !== false;
    if (key === 'divider') return true;
    return true;
  }

  _toggleMeta(key, ev) {
    const on = ev?.target?.checked ?? true;
    let next = { ...this._config };
    if (key === 'area') next.show_area = on;
    else if (key === 'type') next.show_type = on;
    else if (key === 'severity') next.show_severity = on;
    else if (key === 'sent') next.show_sent = on;
    else if (key === 'text') next.show_details = on;
    this._config = next;
    this.dispatchEvent(new CustomEvent('config-changed', { detail: { config: next } }));
  }

  _moveMeta(key, delta) {
    // Normalize to the same order the UI renders (includes 'divider' and 'text' and all allowed keys)
    const baseKeys = ['area','type','severity','sent'];
    const specialKeys = ['divider','text'];
    const allKeys = [...baseKeys, ...specialKeys];
    const raw = (this._config.meta_order && Array.isArray(this._config.meta_order) && this._config.meta_order.length)
      ? this._config.meta_order.filter((k) => allKeys.includes(k))
      : [...allKeys];
    // Deduplicate while preserving first occurrence
    let current = raw.filter((k, i) => raw.indexOf(k) === i);
    // Ensure presence of divider/text
    if (!current.includes('divider')) current.push('divider');
    if (!current.includes('text')) current.push('text');
    // Ensure all allowed keys are present so their relative order is explicit
    const filled = [...current, ...allKeys.filter((k) => !current.includes(k))];

    const idx = filled.indexOf(key);
    if (idx < 0) return;
    const newIdx = Math.max(0, Math.min(filled.length - 1, idx + delta));
    if (newIdx === idx) return;
    const next = [...filled];
    next.splice(idx, 1);
    next.splice(newIdx, 0, key);
    this._config = { ...this._config, meta_order: next };
    this.dispatchEvent(new CustomEvent('config-changed', { detail: { config: this._config } }));
  }

  _labelForMeta(key) {
    const map = { area: 'Area', type: 'Type', severity: 'Severity', sent: 'Sent', text: 'Text', divider: '— Details —' };
    return map[key] || key;
  }

  _computeLabel = (schema) => {
    if (schema.label) return schema.label;
    const labels = {
      entity: 'Entity',
      title: 'Title',
      show_header: 'Show header',
      show_icon: 'Show icon',
      severity_background: 'Severity background',
      icon: 'Icon',
      icon_color: 'Icon color',
      max_items: 'Max items',
      sort_order: 'Sort order',
      date_format: 'Date format',
      group_by: 'Group by',
      filter_severities: 'Filter severities',
      filter_areas: 'Filter areas (comma-separated)',
      collapse_details: 'Collapse details',
      show_area: 'Show area',
      show_type: 'Show type',
      show_severity: 'Show severity',
      show_sent: 'Show sent',
      tap_action: 'Tap action',
      double_tap_action: 'Double tap action',
      hold_action: 'Hold action',
    };
    return labels[schema.name] || schema.name;
  };
}

if (!customElements.get('krisinformation-alert-card-editor')) {
  customElements.define('krisinformation-alert-card-editor', KrisinformationAlertCardEditor);
}

// Register the card so it appears in the "Add card" dialog
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'krisinformation-alert-card',
  name: 'Krisinformation Alert Card',
  description: 'Displays Krisinformation alerts using the Krisinformation integration with configurable attributes',
  preview: true,
});


// Actions support (same behavior as SMHI card)
KrisinformationAlertCard.prototype._onRowAction = function (e, item) {
  const tag = (e.composedPath?.()[0]?.tagName || '').toLowerCase();
  if (tag === 'ha-markdown' || (e.target && e.target.classList && e.target.classList.contains('details-toggle'))) {
    return;
  }
  const action = this.config?.tap_action || { action: 'more-info' };
  this._runAction(action, item);
};

KrisinformationAlertCard.prototype._runAction = function (action, item) {
  const a = action?.action || 'more-info';
  if (a === 'none') return;
  if (a === 'more-info') {
    const ev = new CustomEvent('hass-more-info', { bubbles: true, composed: true, detail: { entityId: this.config.entity } });
    this.dispatchEvent(ev);
    return;
  }
  if (a === 'navigate' && action.navigation_path) {
    history.pushState(null, '', action.navigation_path);
    const ev = new Event('location-changed', { bubbles: true, composed: true });
    this.dispatchEvent(ev);
    return;
  }
  if (a === 'url' && action.url_path) {
    window.open(action.url_path, '_blank');
    return;
  }
  if (a === 'call-service' && action.service) {
    const [domain, service] = action.service.split('.');
    this.hass.callService(domain, service, action.service_data || {});
    return;
  }
};
