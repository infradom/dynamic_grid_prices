# dynamic_grid_prices_solar


Work in progress ! This will become a HomeAssistant integration. 
FOR THE TIME BEING, IT IS VERY INCOMPLETE AND UNTESTED

This integration will periodically pull the dynamic grid prices from the https://transparency.entsoe.eu API platform (and/or the Belgian Ecopower trial API)
I know similar integrations exist, but this one wont need a dependency on node-red. The Nordpool integration is a good alternative, but has no knowledge of the ecopower prices.

## Entsoe data source:
If you want to use entsoe as data source, you will need to create a entsoe platform login and request an API token so that the integration can access the day-ahead-prices.
The Entsoe data source is generic and does not know your power providers markup costs. Extra cost and scaling factors can be applied for both consumption and injection.

## Ecopower trial data source (Ecopower customers only)
This API provides the actual day-ahead prices that Ecopower will charge for a dynamic contract.
Current implementation assumes you have a single tarif, no day/night meter.

# Installation
This custom integration cannot be installed through HACS yet, as we feel it is still too experimental.
You can install it manually by copying the contents of the dynamic_grid_prices folder to your home assistant's config/custom_components folder. A restart your HA software may be required.
Then under settings->devices&services, press the 'add integration button', type or select DynGridPricesSolar 
A config dialog will be displayed.

# Configuration parameters:
- API authentication token for Entsoe. See https://transparency.entsoe.eu/content/static_content/Static%20content/web%20api/Guide.html#_authentication_and_authorisation for information on how to obtain a token. If you only want to use the Ecopower price, leave this field empty. You must either provide an Entsoe token or an API token or both.
- area code (only relevant for entsoe): for Belgium this is 10YBE----------2 (for other areas, see https://transparency.entsoe.eu/content/static_content/Static%20content/web%20api/Guide.html#_areas.
- grid operators may charge different prices than the ones published on entsoe. This integration allows to declare factors A, B, C, D for some customization:
  - consume cost: Cost = A * (published_price + B)
  - injection fee:  Fee = C * (published_price - D)
Note that depending on the taxation, these simple scaling formulas may not correctly provide the real price in your country. They just allow us to have rough feeling of the consumption and injection price.

- (Optional) Authentication code for the Ecopower API: contact Ecopower to obtain a value for this token.


# Entities created:
This integration will create several entities for the different Entsoe and Ecopower injection and consumption prices.
The entities contain an attribute list with the detailed day-ahead prices (per hour or per 15 minutes).
The attribute list is made compatible with the NordPool attributes
Additional entities will be created in future versions to make your automations easier.

# Apex Pricing Dashboard Card:
The integration makes it easy to create an apexchart graph using the xxx_raw_data attribute

```
type: custom:apexcharts-card
experimental:
  color_threshold: true
graph_span: 24h
header:
  title: Electricity Price Today - Ecopower Injection
  show: true
span:
  start: day
  offset: +0d
now:
  show: true
  label: Now
series:
  - entity: sensor.ecopower_injection_price
    type: column
    data_generator: |
      return entity.attributes.raw_today.map((entry) => {
        return [new Date(entry.start), entry.value];
      });
    color_threshold:
      - value: 0
        color: green
        opacity: 1
      - value: 0.3
        color: yellow
      - value: 0.4
        color: red

```


# Disclaimer:
 Errors in this software can have a significant impact on your electricity bill.
 The authors cannot be held liable for any financial or other damage caused by the use of this software. 
