# dynamic_grid_prices

Integration for the HomeAssistant platform

Work in progress ! 
Although I am using this software in my installation, recent versions may not always be proberly tested the first days after release.

# Version history:
* v0.4.0: adaptation to support 15 minute intervals (urgent update was needed)
* v0.3.0: fill gaps in entsoe and backup data; sort data so that graphs are not currupted when data is not sorted correctly
* v0.2.x: compatibility with HA 2025.6.x
* v0.1.x: initial versions

# This software:

This integration will periodically pull the dynamic grid prices from the https://transparency.entsoe.eu API platform.
Alternatively, or as a backup source, a Nordpool integration instance can be used as data source.
I know similar integrations exist, but this one wont need a dependency on node-red. The Nordpool integration is a good alternative, but has no simple options to scale injection and consumption prices in one instance. 


## Entsoe data source:
This integration uses entsoe as data source, so you will need to create a entsoe platform login and request an API token so that the integration can access the day-ahead-prices.
The Entsoe data source is generic and does not know your energy company's markup costs. Extra cost and scaling factors can be applied for both consumption and injection.  If you do not want to use Entsoe as data source, leave the API token field empty and select the backup source flag.

## Backup Nordpool data source:
This integration can use a Nordpool integration instance as backup data source. The Nordpool data souce can even be used as main source if no Entsoe API token is specified. You first need to install the Nordpool integration and configure an instance that expresses the cost in cost/Mwh, as the scaling factors are shared with the Entsoe source. Creating such additional sensors can be done in the Nordpool reconfiguration menu (add item button).

<img width="645" height="438" alt="image" src="https://github.com/user-attachments/assets/2389de5d-cc00-4d25-b684-79e4bd3a63cd" />



This will create the entity that needs to be used as backup source.

# Installation
This custom integration cannot be installed through HACS yet, as we feel it is still too experimental.
You can install it manually by copying the contents of the custom_components/dynamic_grid_prices folder to your home assistant's config/custom_components folder. A restart your HA software may be required.
Then under settings->devices&services, press the 'add integration button', type or select DynGridPrices 
A config dialog will be displayed.

# Configuration parameters:
- name of this integration instance (only tested with the default name for now)
- API authentication token for Entsoe. See https://transparency.entsoe.eu/content/static_content/Static%20content/web%20api/Guide.html#_authentication_and_authorisation for information on how to obtain a token. 
- area code (only relevant for entsoe): for Belgium this is 10YBE----------2 (for other areas, see https://transparency.entsoe.eu/content/static_content/Static%20content/web%20api/Guide.html#_areas.
- scaling/adaptation factors for injection and consumption:
   - energy companies may charge different prices than the ones published on entsoe. This integration allows to declare factors A, B, C, D and VAT levels to allow for some customization:
    - consume cost:   Cost = (factor_A * published_price + factor_B) * VAT_scaling_consumption
    - injection fee:  Fee  = (factor_C * published_price - factor_D) * VAT_scaling_injection

Note that depending on the taxation, these simple scaling formulas may not correctly provide the real price in your country. They just allow us to have rough feeling of the consumption and injection price.
The VAT scaling parameters are entered as 1.06 for 6% VAT



# Entities created:
This integration will create several entities for the different Entsoe price and the derived injection and consumption prices.
The entities contain an attribute list with the detailed day-ahead prices (per hour or per 15 minutes).
The attribute list is made compatible with the NordPool attributes, but the tomorrow entries have been added to the today list.
Additional entities will be created in future versions to make your automations easier.

# Apexchart Pricing Dashboard Card:
The integration makes it easy to create an apexchart graph using the raw_today attribute
For information on how to instaal custom:apexchart, see the appropriate website.
My very simple initial try uses this yaml code:

```
type: custom:apexcharts-card
experimental:
  color_threshold: true
graph_span: 48h
header:
  title: Electricity Price - Injection
  show: true
span:
  start: day
  offset: +0d
now:
  show: true
  label: Now
yaxis:
  - decimals: 2
series:
  - entity: sensor.dynamic_grid_prices_injection_price
    type: column
    float_precision: 3
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
