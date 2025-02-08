# Krisinformation Sensor


## Overview

Krisinformation Sensor is a custom component for Home Assistant that retrieves crisis alerts (VMA) from the Krisinformation API i Sweden. It allows you to filter alerts by county or view all alerts for the entire country. 

There is also a dashboard card specifically for this integration, which can be found here: [Krisinformation Alert Card](https://github.com/Nicxe/krisinformation-alert-card).

<a href="https://buymeacoffee.com/niklasv" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: auto !important;width: auto !important;" ></a>


## Features

- Retrieve crisis alerts from the Krisinformation API
- Filter alerts by county or view all alerts for the whole of Sweden
- Sensor attributes:
  - **Headline**
  - **PushMessage**
  - **Published**
  - **Area** (with Description and Coordinates)
  - **map_url** 


## Installation

> [!WARNING]
> This is an early alpha release and will be continuously developed and improved.

You can install this integration as a custom repository by following one of these guides:

### With HACS (Recommended)

To install the custom component using HACS:

1. Click on the three dots in the top right corner of the HACS overview menu.
2. Select **Custom repositories**.
3. Add the repository URL: `https://github.com/Nicxe/krisinformation`.
4. Select type: **Integration**.
5. Click the **ADD** button.

<details>
<summary>Without HACS</summary>

1. Download the latest release of the SMHI Alert integration from **[GitHub Releases](https://github.com/Nicxe/krisinformation/releases)**.
2. Extract the downloaded files and place the `smhi_alerts` folder in your Home Assistant `custom_components` directory (usually located in the `config/custom_components` directory).
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
{% set alert = state_attr('sensor.krisinformation_norrbotten', 'alerts')[0] %}
{{ alert['Headline'] }}: {{ alert['PushMessage'] }}
```

### Example Automation

To send this as a notification via Home Assistant, you can use the following automation configuration:

```
automation:
  - alias: "Krisinformation Alert Notification"
    trigger:
      - platform: state
        entity_id: sensor.krisinformation_norrbotten
    condition: []
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "{{ state_attr('sensor.krisinformation_norrbotten', 'alerts')[0]['Headline'] }}"
          message: "{{ state_attr('sensor.krisinformation_norrbotten', 'alerts')[0]['PushMessage'] }}"
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

![Screenshot](https://github.com/Nicxe/krisinformation-alert-card/blob/main/screenshot.png)


## Contributing

Contributions, bug reports, and feedback are welcome. Please feel free to open issues or pull requests on GitHub.


