# Krisinformation integration

![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=)
<img alt="Maintenance" src="https://img.shields.io/maintenance/yes/2025"> <img alt="GitHub last commit" src="https://img.shields.io/github/last-commit/Nicxe/krisinformation"><br><br>
<img alt="GitHub Repo stars" src="https://img.shields.io/github/stars/Nicxe/krisinformation">

## Overview

Krisinformation integration is a custom component for Home Assistant that retrieves crisis alerts (VMA) from [Sveriges Radio's API for Important Public Announcements](https://vmaapi.sr.se/index.html?urls.primaryName=v3.0-beta). It allows you to filter alerts by municipalities, county or Sweden to view all alerts for the entire country.

There is also a dashboard card specifically for this integration, which can be found here: [Krisinformation Alert Card](https://github.com/Nicxe/krisinformation-alert-card).

<a href="https://buymeacoffee.com/niklasv" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: auto !important;width: auto !important;" ></a>




## Installation

You can install this integration as a custom repository by following one of these guides:

### With HACS (Recommended)

To install the custom component using HACS:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Nicxe&repository=krisinformation&category=integration)

or
1. Install HACS if you don't have it already
2. Open HACS in Home Assistant
3. Search for "Krisinformation"
4. Click the download button. ⬇️

<details>
<summary>Without HACS</summary>

1. Download the latest release of the Krisinformation integration from **[GitHub Releases](https://github.com/Nicxe/krisinformation/releases)**.
2. Extract the downloaded files and place the `krisinformation` folder in your Home Assistant `custom_components` directory (usually located in the `config/custom_components` directory).
3. Restart your Home Assistant instance to load the new integration.

</details>


## Configuration

To add the integration to your Home Assistant instance, use the button below:

<p>
    <a href="https://my.home-assistant.io/redirect/config_flow_start?domain=krisinformation" class="my badge" target="_blank">
        <img src="https://my.home-assistant.io/badges/config_flow_start.svg">
    </a>
</p>


> [!TIP]
> You can easily set up multiple sensors for different locations by clicking Add Entry on the Krisinformation integration page in Home Assistant. No YAML configuration is required, and each sensor can have its own unique setup.


### Manual Configuration

If the button above does not work, you can also perform the following steps manually:

1. Browse to your Home Assistant instance.
2. Go to **Settings > Devices & Services**.
3. In the bottom right corner, select the **Add Integration** button.
4. From the list, select **Krisinformation**.
5. Follow the on-screen instructions to complete the setup.





## Example: Sending Notifications with Alerts

This example demonstrates how to use the sensor.krisinformation_norrbotten to send a notification containing the Headline and PushMessage from the first alert in the sensor’s alerts attribute.

### Jinja2 Template for Notification

The following Jinja2 template extracts the Headline and PushMessage from the sensor’s alerts attribute:

```

{% set alert = state_attr('sensor.krisinformation_hela_sverige', 'alerts')[0] %}
{{ alert['event'] }}: {{ alert['description'] }}
```

### Example Automation

To send this as a notification via Home Assistant, you can use the following automation configuration:

```
automation:
  - alias: "Krisinformation Alert Notification"
    trigger:
      - platform: state
        entity_id: sensor.krisinformation_hela_sverige
    condition: []
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "{{ state_attr('sensor.krisinformation_hela_sverige', 'alerts')[0]['alerts'] }}"
          message: "{{ state_attr('sensor.krisinformation_hela_sverige', 'alerts')[0]['description'] }}"
```

**Explanation:**
* Trigger: The automation is triggered whenever the state of sensor.krisinformation_norrbotten changes.
* Action: The notify service sends a notification with:
    * Title: The Headline from the first alert in the alerts attribute.
    * Message: The PushMessage from the same alert.

This automation ensures you are immediately informed about important updates in the sensor.

> [!NOTE]
> Replace mobile_app_your_phone with the name of your mobile app notification service. If the alerts attribute contains multiple alerts and you want to handle them differently, you can modify the template to iterate over the list or select specific items.



## Usage Screenshots

Using the [Krisinformation Alert Card](https://github.com/Nicxe/krisinformation-alert-card) 

<img width="482" height="287" alt="krisinfo_card_screenshoot" src="https://github.com/user-attachments/assets/d3e34e0b-7f8f-4cfc-a881-76396084e885" />



## Contributing

Contributions, bug reports, and feedback are welcome. Please feel free to open issues or pull requests on GitHub.


