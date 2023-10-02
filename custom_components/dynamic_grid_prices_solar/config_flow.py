"""Config flow for DynGridPricesSolar integration."""
from __future__ import annotations

import logging
from typing import Any, cast

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
import json
import time
import xmltodict

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.core import async_get_hass
#from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import DOMAIN, CONF_NAME
from .const import CONF_ENTSOE_TOKEN, CONF_ENTSOE_AREA, CONF_ENTSOE_FACTOR_A, CONF_ENTSOE_FACTOR_B, CONF_ENTSOE_FACTOR_C, CONF_ENTSOE_FACTOR_D, CONF_VAT_INJ, CONF_VAT_CONS
from .const import PLATFORMS
from .const import DEFAULT_NAME, DEFAULT_FACTOR_A, DEFAULT_FACTOR_B, DEFAULT_FACTOR_C, DEFAULT_FACTOR_D, DEFAULT_ENTSOE_AREA, DEFAULT_VAT_INJ, DEFAULT_VAT_CONS
from .__init__ import EntsoeApiClient

from homeassistant.helpers.schema_config_entry_flow import (
    SchemaCommonFlowHandler,
    SchemaConfigFlowHandler,
    SchemaFlowError,
    SchemaFlowFormStep,
    SchemaFlowMenuStep,
)

_LOGGER = logging.getLogger(__name__)



user_input = {}
# Provide defaults for form
user_input[CONF_NAME]            = DEFAULT_NAME
user_input[CONF_ENTSOE_TOKEN]    = ""
user_input[CONF_ENTSOE_AREA]     = DEFAULT_ENTSOE_AREA
user_input[CONF_ENTSOE_FACTOR_A] = DEFAULT_FACTOR_A
user_input[CONF_ENTSOE_FACTOR_B] = DEFAULT_FACTOR_B
user_input[CONF_ENTSOE_FACTOR_C] = DEFAULT_FACTOR_C
user_input[CONF_ENTSOE_FACTOR_D] = DEFAULT_FACTOR_D
user_input[CONF_VAT_INJ]         = DEFAULT_VAT_INJ
user_input[CONF_VAT_CONS]        = DEFAULT_VAT_CONS



async def _validate_base(handler: SchemaCommonFlowHandler, user_input: dict[str, Any]) -> dict[str, Any] :
    hass = async_get_hass()
    try:
        session = async_create_clientsession(hass)
        client = EntsoeApiClient(session, user_input[CONF_ENTSOE_TOKEN], user_input[CONF_ENTSOE_AREA])
        response = await client.async_get_data()
        if response: return user_input
        else: raise SchemaFlowError("Entsoe credentaials failed")
    except Exception:  # pylint: disable=broad-except
        _LOGGER.error("Entsoe communication failed")
        raise SchemaFlowError("Entsoe communication failed")




async def _next_step(user_input: Any) -> str:
    return None #user_input[CONF_INTERFACE] # eitheer "tcp" or "serial"


CONFIG_SCHEMA = vol.Schema(
                {   vol.Required(CONF_NAME,            default = user_input[CONF_NAME]): cv.string,
                    vol.Optional(CONF_ENTSOE_TOKEN,    default = user_input[CONF_ENTSOE_TOKEN]): cv.string,
                    vol.Required(CONF_ENTSOE_AREA,     default = user_input[CONF_ENTSOE_AREA]): cv.string,
                    vol.Required(CONF_ENTSOE_FACTOR_A, default = user_input[CONF_ENTSOE_FACTOR_A]): cv.positive_float,
                    vol.Required(CONF_ENTSOE_FACTOR_B, default = user_input[CONF_ENTSOE_FACTOR_B]): cv.positive_float,  
                    vol.Required(CONF_VAT_CONS,        default = user_input[CONF_VAT_CONS]): cv.positive_float,                    
                    vol.Required(CONF_ENTSOE_FACTOR_C, default = user_input[CONF_ENTSOE_FACTOR_C]): cv.positive_float,
                    vol.Required(CONF_ENTSOE_FACTOR_D, default = user_input[CONF_ENTSOE_FACTOR_D]): cv.positive_float,
                    vol.Required(CONF_VAT_INJ,        default = user_input[CONF_VAT_INJ]): cv.positive_float,  
                } )

OPTION_SCHEMA = vol.Schema(
                {   vol.Optional(CONF_ENTSOE_TOKEN,    default = user_input[CONF_ENTSOE_TOKEN]): cv.string,
                    vol.Required(CONF_ENTSOE_AREA,     default = user_input[CONF_ENTSOE_AREA]): cv.string,
                    vol.Required(CONF_ENTSOE_FACTOR_A, default = user_input[CONF_ENTSOE_FACTOR_A]): cv.positive_float,
                    vol.Required(CONF_ENTSOE_FACTOR_B, default = user_input[CONF_ENTSOE_FACTOR_B]): cv.positive_float,  
                    vol.Required(CONF_VAT_CONS,        default = user_input[CONF_VAT_CONS]): cv.positive_float,                    
                    vol.Required(CONF_ENTSOE_FACTOR_C, default = user_input[CONF_ENTSOE_FACTOR_C]): cv.positive_float,
                    vol.Required(CONF_ENTSOE_FACTOR_D, default = user_input[CONF_ENTSOE_FACTOR_D]): cv.positive_float,
                    vol.Required(CONF_VAT_INJ,        default = user_input[CONF_VAT_INJ]): cv.positive_float,  
                } )

CONFIG_FLOW: dict[str, SchemaFlowFormStep | SchemaFlowMenuStep] = {
       "user":   SchemaFlowFormStep(CONFIG_SCHEMA, validate_user_input=_validate_base, next_step = _next_step),
    }
OPTIONS_FLOW: dict[str, SchemaFlowFormStep | SchemaFlowMenuStep] = {
       "init":   SchemaFlowFormStep(OPTION_SCHEMA, next_step = _next_step),
    }

class ConfigFlowHandler(SchemaConfigFlowHandler, domain=DOMAIN):
    #Handle a config or options flow for Utility Meter.

    _LOGGER.info(f"starting configflow - domain = {DOMAIN}")
    config_flow  = CONFIG_FLOW
    options_flow = OPTIONS_FLOW


    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        _LOGGER.info(f"title configflow {DOMAIN} {CONF_NAME}: {options}")
        # Return config entry title
        return cast(str, options[CONF_NAME]) if CONF_NAME in options else ""




