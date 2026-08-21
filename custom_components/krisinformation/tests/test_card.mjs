import assert from 'node:assert/strict';
import { pathToFileURL } from 'node:url';

const tag = (strings, ...values) => ({ strings, values });
class LitElement {
  disconnectedCallback() {}
  dispatchEvent() { return true; }
}

const registry = new Map();
globalThis.customElements = {
  define: (name, constructor) => registry.set(name, constructor),
  get: (name) => registry.get(name),
};
globalThis.document = { createElement: (name) => ({ name }) };
globalThis.window = {
  LitElement,
  litHtml: { html: tag, css: tag },
  customCards: [],
  open: () => {},
};
globalThis.history = { pushState: () => {} };
globalThis.CustomEvent = class {
  constructor(type, options = {}) {
    this.type = type;
    this.detail = options.detail;
  }
};

const cardModuleUrl = process.env.KRISINFORMATION_CARD_MODULE_PATH
  ? pathToFileURL(process.env.KRISINFORMATION_CARD_MODULE_PATH)
  : new URL('../www/krisinformation-alert-card.js', import.meta.url);
await import(cardModuleUrl);

const Card = customElements.get('krisinformation-alert-card');
assert.ok(Card, 'card should register as a custom element');

const card = new Card();
card.hass = {
  language: 'en',
  states: {
    'sensor.vma': {
      attributes: {
        friendly_name: 'VMA',
        alerts: [
          {
            identifier: 'vma-1',
            sent: '2026-08-21T10:00:00+02:00',
            info: {
              language: 'sv-SE',
              event: 'Viktigt meddelande',
              severity: 'Severe',
              headline: 'VMA headline',
              description: 'VMA details',
              area: [{ areaDesc: 'Göteborg' }],
            },
          },
        ],
      },
    },
    'sensor.news': {
      attributes: {
        items: [
          {
            identifier: 'news-1',
            headline: 'News headline',
            preamble: 'News preamble',
            body_text: 'News body',
            updated: '2026-08-21T12:00:00+02:00',
            sender_name: 'Krisinformation.se',
            web_url: 'https://example.com/news',
            areas: [{ type: 'County', description: 'Västra Götalands län' }],
            links: [{ text: 'Read more', url: 'https://example.com/source' }],
          },
        ],
      },
    },
    'sensor.notices': {
      attributes: {
        items: [
          {
            identifier: 'notice-1',
            headline: 'Notice headline',
            preamble: 'Notice preamble',
            body_text: 'Notice body',
            changed: '2026-08-21T11:00:00+02:00',
            notice_type: 1,
            areas: [],
            links: [],
            layout: { icon: 'notices_announcement' },
          },
        ],
      },
    },
  },
};

card.setConfig({
  entity: 'sensor.vma',
  news_entity: 'sensor.news',
  notices_entity: 'sensor.notices',
  group_by: 'source',
});

const combined = card._alerts();
assert.deepEqual(combined.map((item) => item.source_type), ['vma', 'news', 'notices']);
assert.equal(combined[1].area, 'Västra Götalands län');
assert.match(combined[1].details, /\[Read more\]\(https:\/\/example.com\/source\)/);
assert.equal(combined[2]._source_icon, 'mdi:bullhorn-outline');
assert.deepEqual(card._visibleAlerts().map((item) => item.identifier), [
  'news-1',
  'notice-1',
  'vma-1',
]);
const sourceGroups = card._renderGrouped(combined);
assert.deepEqual(sourceGroups.map((group) => group.values[0]), ['VMA', 'News', 'Notices']);

card._activeSource = 'news';
assert.deepEqual(card._visibleAlerts().map((item) => item.identifier), ['news-1']);

card.setConfig({ entity: 'sensor.vma' });
assert.equal(card._alerts().length, 1, 'legacy single-entity configuration should remain valid');
assert.equal(card._alerts()[0].source_type, 'vma');
assert.throws(() => card.setConfig({}), /at least one Krisinformation entity/);

assert.equal(window.customCards[0].type, 'krisinformation-alert-card');
const styles = Card.styles.strings.join('');
assert.match(styles, /--kris-alert-item-gap:\s*8px/);
assert.match(styles, /\.area-group\s*>\s*\.alert\s*\+\s*\.alert/);
console.log('Krisinformation card tests passed');
