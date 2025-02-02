# Krisinformation Sensor

Krisinformation Sensor is a custom component for Home Assistant that retrieves crisis alerts (VMA) from the Krisinformation API i Sweden. It allows you to filter alerts by county or view all alerts for the entire country. 

[Krisinformation Alert Card](https://github.com/Nicxe/krisinformation-alert-card).

## Features

- Retrieve crisis alerts from the Krisinformation API
- Filter alerts by county or view all alerts for the whole of Sweden
- Summary attributes include key fields such as:
  - **Identifier**
  - **Headline**
  - **PushMessage**
  - **Published**
  - **Preamble**
  - **Area** (with Description and Coordinates)
- Configurable via the Home Assistant UI with a dropdown to select the desired county
- Unique sensor ID generation to allow multiple instances of the integration

## Installation

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


> [!WARNING]
> This is an early alpha release and will be continuously developed and improved.


## Contributing

Contributions, bug reports, and feedback are welcome. Please feel free to open issues or pull requests on GitHub.

## License

This project is licensed under the [MIT License](LICENSE).