"""Constants for the DynGridPrices integration."""



ENTSOE_DAYAHEAD_URL = "https://web-api.tp.entsoe.eu/api?securityToken={TOKEN}&documentType=A44&in_Domain={AREA}&out_Domain={AREA}&periodStart={START}&periodEnd={END}"


ENTSOE_HEADERS = {"Content-type": "application/xml; charset=UTF-8"}


ATTRIBUTION = '@infradom'

NAME = "DynGridPrices"
DEFAULT_NAME = "Dynamic_grid_prices"
DOMAIN = "dynamic_grid_prices"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "0.3.0"
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
CONF_VAT_INJ         = "vat_inj"
CONF_VAT_CONS        = "vat_cons" 
CONF_NAME            = "name"
CONF_BACKUP          = "backup_flag"
CONF_BACKUP_SOURCE   = "backup_source"

DEFAULT_FACTOR_A = 0.001 * 1.02      # consumption price scale to kWh
DEFAULT_FACTOR_B = 0.004 + 0.0378329 + 0.0019 + 0.0475+ +0.0165 + 0.0028 # consumption price extra per kWh, see your electricity bill
DEFAULT_FACTOR_C = 0.001 * 0.85      # injection price scale scale to kWh
DEFAULT_FACTOR_D = 0.004             # injection price extra cost per kWh
DEFAULT_VAT_INJ  = 1.0               # VAT tax scaling on injection
DEFAULT_VAT_CONS = 1.06              # VAT tax scaling on consumption
DEFAULT_ENTSOE_AREA = '10YBE----------2'

SENSOR = "sensor"
PLATFORMS = [SENSOR]
ICON = "mdi:format-quote-close"


