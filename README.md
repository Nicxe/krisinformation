# Krisinformation

![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=)
<img alt="Maintenance" src="https://img.shields.io/maintenance/yes/2025"> <img alt="GitHub last commit" src="https://img.shields.io/github/last-commit/Nicxe/krisinformation"><br><br>
<img alt="GitHub Repo stars" src="https://img.shields.io/github/stars/Nicxe/krisinformation">
![GitHub Downloads (all assets, latest release)](https://img.shields.io/github/downloads/nicxe/krisinformation/latest/total)

## Overview

Krisinformation is a custom Home Assistant integration that fetches VMA alerts from [Sveriges Radio](https://vmaapi.sr.se/index.html?urls.primaryName=v3.0-beta).

This repository now contains both:
- the Home Assistant integration (`krisinformation`)
- the Lovelace alert card (`krisinformation-alert-card.js`)

<a href="https://buymeacoffee.com/niklasv" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: auto !important;width: auto !important;" ></a>

## Installation

### Integration with HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Nicxe&repository=krisinformation&category=integration)

You can also add `https://github.com/Nicxe/krisinformation` manually in HACS as type **Integration**.

### Integration without HACS

1. Download `krisinformation.zip` from the [latest release](https://github.com/Nicxe/krisinformation/releases).
2. Extract the archive and place the `krisinformation` folder in `config/custom_components/`.
3. Restart Home Assistant.

### Alert card installation

The alert card is bundled with this integration.

When the integration starts, it automatically:
- syncs the bundled card to `config/www/krisinformation-alert-card.js`
- creates or updates a Lovelace `module` resource at `/local/krisinformation-alert-card.js?v=...` for cache-busting

If you have just installed or updated, reload the browser once to ensure the latest card resource is loaded.

## Card usage

1. Open your dashboard.
2. Select **Edit dashboard**.
3. Add a new card.
4. Choose **Custom: Krisinformation Alert Card**.

Manual card type:
- `custom:krisinformation-alert-card`

### Manual fallback (if needed)

Normally no manual Lovelace resource setup is required.

If your dashboard does not load the card automatically, add this resource manually:
- URL: `/local/krisinformation-alert-card.js`
- Type: `JavaScript Module`

## Configuration

To add the integration, use this button:

<p>
  <a href="https://my.home-assistant.io/redirect/config_flow_start?domain=krisinformation" class="my badge" target="_blank">
    <img src="https://my.home-assistant.io/badges/config_flow_start.svg" alt="Add Krisinformation to Home Assistant">
  </a>
</p>

If needed, add it manually via **Settings > Devices & Services > Add Integration**.

## Example: Notification from first alert

```jinja2
{% set alert = state_attr('sensor.krisinformation_hela_sverige', 'alerts')[0] %}
{{ alert['event'] }}: {{ alert['description'] }}
```

```yaml
automation:
  - alias: "Krisinformation Alert Notification"
    trigger:
      - platform: state
        entity_id: sensor.krisinformation_hela_sverige
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "{{ state_attr('sensor.krisinformation_hela_sverige', 'alerts')[0]['event'] }}"
          message: "{{ state_attr('sensor.krisinformation_hela_sverige', 'alerts')[0]['description'] }}"
```

## Release assets and versioning

Each GitHub release in this repository publishes:
- `krisinformation.zip` for integration installation

The bundled alert card is included inside `krisinformation.zip`.

## Migration from the old card repository

If you previously used `Nicxe/krisinformation-alert-card`, see [MIGRATION.md](./MIGRATION.md).

## Usage screenshots

<img width="482" height="287" alt="krisinfo_card_screenshoot" src="https://github.com/user-attachments/assets/4485a1ff-eb26-4235-8ddd-8d1405c0ca44" />

## Contributing

Contributions, bug reports, and feedback are welcome. Please open issues or pull requests on GitHub.
