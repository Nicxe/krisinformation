# Krisinformation

![HACS](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=)
![Maintenance](https://img.shields.io/maintenance/yes/2026)
![GitHub last commit](https://img.shields.io/github/last-commit/Nicxe/krisinformation)
![GitHub stars](https://img.shields.io/github/stars/Nicxe/krisinformation)
![GitHub downloads](https://img.shields.io/github/downloads/nicxe/krisinformation/latest/total)

Krisinformation is a custom Home Assistant integration for verified Swedish crisis information. It keeps VMA alerts on the original [Sveriges Radio VMA API](https://vmaapi.sr.se/index.html?urls.primaryName=v3.0-beta) and adds news and notices from the official [Krisinformation API v3](https://api.krisinformation.se/v3).

The repository contains both the Home Assistant integration and the bundled `krisinformation-alert-card.js` Lovelace card.

<a href="https://buymeacoffee.com/niklasv" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee"></a>

## Data sources

| Content | Source | Default refresh | Home Assistant output |
| --- | --- | --- | --- |
| VMA | Sveriges Radio VMA API v3 | 60 seconds | Count sensor, active binary sensor, lifecycle events |
| News | Krisinformation API v3 `/news` | 10 minutes | Count sensor, normalized items, lifecycle events |
| Notices | Krisinformation API v3 `/notices` | 5 minutes | Count sensor, normalized items, lifecycle events |

The integration deliberately does not use Krisinformation's editorial `/notifications` endpoint because Krisinformation is retiring it on 21 September 2026. The supported `/notices` endpoint is used instead.

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Nicxe&repository=krisinformation&category=integration)

You can also add `https://github.com/Nicxe/krisinformation` manually in HACS as an integration.

### Manual installation

1. Download `krisinformation.zip` from the [latest release](https://github.com/Nicxe/krisinformation/releases).
2. Extract the `krisinformation` folder to `config/custom_components/`.
3. Restart Home Assistant.

Add the integration with this button:

<p>
  <a href="https://my.home-assistant.io/redirect/config_flow_start?domain=krisinformation" class="my badge" target="_blank">
    <img src="https://my.home-assistant.io/badges/config_flow_start.svg" alt="Add Krisinformation to Home Assistant">
  </a>
</p>

You can also use **Settings > Devices & services > Add integration** and search for Krisinformation.

## Configuration and filtering

The location selection has source-specific precision:

- VMA continues to use the selected municipality or county directly against the SR API.
- Krisinformation news and notices use county-level filtering. A selected municipality is automatically mapped to its county.
- **Include national content** controls items tagged for all of Sweden.
- **Include content without a geographic tag** controls items where Krisinformation supplies no area. This is enabled by default because geographic tagging is not complete for every item.

The integration options also control whether news and notices are enabled, the number of news-history days, the maximum displayed items per source, language, VMA severity, Update/Cancel visibility, and the SR production/test environment. Polling intervals are managed by the integration and are not user configurable.

Krisinformation also republishes SMHI weather warnings as notices. **Include SMHI weather warnings in notices** is enabled by default so the integration remains complete when used on its own. Turn it off during setup or later under **Settings > Devices & services > Krisinformation > Configure** when the dedicated SMHI Alerts integration supplies your weather warnings. The filter is applied before sensor state and lifecycle events are created, so disabling it removes duplicates from dashboards, templates, and automations rather than only hiding them in the bundled card.

Only notices explicitly identified by Krisinformation with an SMHI warning layout are filtered. Weather-related editorial news remains available in the news sensor. If Krisinformation changes the layout metadata, an unrecognized item remains visible instead of being silently discarded.

Existing installations migrate automatically. The original VMA entity IDs are retained, even if the configured location changes.

## Entities

The exact entity IDs depend on the configured name and location. The integration creates:

- A VMA count sensor with the normalized CAP messages in the `alerts` attribute.
- An active VMA binary sensor.
- A news count sensor with `items` and `latest` attributes when news is enabled.
- A notices count sensor with `items` and `latest` attributes when notices are enabled.

News and notice item attributes include their identifier, headline, preamble, safe plain-text body, timestamps, geographic areas, links, and source-specific metadata. Notice items also expose `is_smhi_weather_warning`, which can be used in templates and diagnostics even when SMHI warnings are included. Large collection attributes are excluded from recorder history while remaining available to dashboards and templates.

Each source has independent availability. A Krisinformation news outage therefore does not make VMA or notices unavailable.

## Lovelace card

The integration copies its bundled card to `config/www/krisinformation-alert-card.js` and maintains a cache-busted Lovelace module resource automatically. Reload the browser once after installing or updating.

Add **Custom: Krisinformation Alert Card** in the dashboard editor. The original single VMA entity configuration remains supported. To create a combined source-aware feed, select the VMA, news, and notices entities in the visual editor or use YAML:

```yaml
type: custom:krisinformation-alert-card
entity: sensor.krisinformation_hela_sverige
news_entity: sensor.krisinformation_hela_sverige_news
notices_entity: sensor.krisinformation_hela_sverige_notices
title: Krisinformation
show_source_filter: true
filter_sources:
  - vma
  - news
  - notices
group_by: none
max_items: 10
```

The source chips switch the visible feed without changing the integration filters. Card-level source, severity, and area filters are available in the editor. When content is grouped by source, groups are shown in priority order: **VMA, News, Notices**. Leaving the icon override blank uses a source-specific icon.

Consecutive items have a consistent 8-pixel gap, including items inside the same group. Advanced themes or card styling can override this through the `--kris-alert-item-gap` CSS variable.

If automatic resource setup is unavailable, add `/local/krisinformation-alert-card.js` manually as a JavaScript module.

## Events and notifications

The integration fires Home Assistant events after it has established an initial snapshot. Content fingerprints persist across restarts, so genuine changes that occurred while Home Assistant was offline can still be detected. Changing filters or enabling/disabling a source reseeds the snapshot without producing misleading event bursts.

| Source | New | Updated | Removed/cancelled |
| --- | --- | --- | --- |
| VMA | `krisinformation_new_alert` | `krisinformation_updated_alert` | `krisinformation_canceled_alert` |
| News | `krisinformation_new_news` | `krisinformation_updated_news` | `krisinformation_removed_news` |
| Notices | `krisinformation_new_notice` | `krisinformation_updated_notice` | `krisinformation_removed_notice` |

New and updated news/notice events contain the normalized item fields plus `source`. Removed events contain `source` and `identifier`.

The integration does not create persistent or mobile notifications automatically. This avoids duplicate messages and lets each household choose the relevant destination, urgency, quiet hours, and actions. Example mobile notification for new Krisinformation news:

```yaml
automation:
  - alias: "Krisinformation new article"
    triggers:
      - trigger: event
        event_type: krisinformation_new_news
    actions:
      - action: notify.mobile_app_your_phone
        data:
          title: "{{ trigger.event.data.headline }}"
          message: >-
            {{ trigger.event.data.preamble
               or trigger.event.data.push_message
               or trigger.event.data.body_text }}
          data:
            url: "{{ trigger.event.data.web_url }}"
```

For VMA, use `krisinformation_new_alert` and the CAP fields in `trigger.event.data`.

## Release assets and migration

Each GitHub release publishes `krisinformation.zip`, including the integration and Lovelace card. If you previously used the separate `Nicxe/krisinformation-alert-card` repository, see [MIGRATION.md](./MIGRATION.md).

## Contributing

Contributions, bug reports, and feedback are welcome through GitHub issues and pull requests.
