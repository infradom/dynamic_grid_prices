"""Constants for the DynGridPrices integration."""

DOMAIN = "dynamic_grid_prices_solar"

ENTSOE_DAYAHEAD_URL = "https://web-api.tp.entsoe.eu/api?securityToken={TOKEN}&documentType=A44&in_Domain={AREA}&out_Domain={AREA}&periodStart={START}&periodEnd={END}"
ECOPWR_DAYAHEAD_URL = "https://acc.ameo.app/api/v2/characteristics/{CURVE}"
ECOPWR_INJECTION = 590
ECOPWR_CONSUMPTION = 622
ECOPWR_CONSUMPTION_22_7 = 624
ECOPWR_CONSUMPTION_21_6 = 623

ENTSOE_HEADERS = {"Content-type": "application/xml; charset=UTF-8"}
ECOPWR_HEADERS = {"Content-type": "application/json; charset=UTF-8", "authorization": "Bearer {TOKEN}"}

ATTRIBUTION = '@infradom'

NAME = "DynGridPricesSolar"
DEFAULT_NAME = DOMAIN
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "0.0.1"
ISSUE_URL = "https://github.com/infradom/dynamic_grid_prices_solar/issues"

PEAKHOURS = range(8,20)
OFFPEAKHOURS1 = range(0,8)
OFFPEAKHOURS2 = range(20,24)

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""

# configuration options
CONF_ENTSOE_TOKEN    = "entsoe_token"
CONF_ENTSOE_AREA     = "entsoe_area"
CONF_ENTSOE_FACTOR_A = "entsoe_factor_A"
CONF_ENTSOE_FACTOR_B = "entsoe_factor_B"
CONF_ENTSOE_FACTOR_C = "entsoe_factor_C"
CONF_ENTSOE_FACTOR_D = "entsoe_factor_D"
CONF_NAME            = "name"
CONF_ECOPWR_TOKEN    = "ecopower_token"


SENSOR = "sensor"
PLATFORMS = [SENSOR]
ICON = "mdi:format-quote-close"


