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

This integration is possible to install as a custom component via HACS (Home Assistant Community Store).


> [!WARNING]
> This is an early alpha release and will be continuously developed and improved.


## Contributing

Contributions, bug reports, and feedback are welcome. Please feel free to open issues or pull requests on GitHub.

## License

This project is licensed under the [MIT License](LICENSE).