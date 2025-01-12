"""Sensor platform for integration_blueprint."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
#from homeassistant.const import CURRENCY_EURO, ENERGY_KILO_WATT_HOUR, ENERGY_MEGA_WATT_HOUR
from homeassistant.const import CURRENCY_EURO
from homeassistant.helpers.entity import EntityCategory
from homeassistant.util import dt
from dataclasses import dataclass
from statistics import mean
from homeassistant.components.sensor import SensorEntityDescription
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
#from homeassistant.const import (DEVICE_CLASS_MONETARY,)
from .const import NAME, VERSION, ATTRIBUTION
from .const import DEFAULT_NAME, DOMAIN, ICON, SENSOR
from .const import PEAKHOURS, OFFPEAKHOURS1, OFFPEAKHOURS2
from .const import CONF_ENTSOE_TOKEN, CONF_ENTSOE_AREA, CONF_ENTSOE_FACTOR_A, CONF_ENTSOE_FACTOR_B, CONF_ENTSOE_FACTOR_C, CONF_ENTSOE_FACTOR_D, CONF_VAT_INJ, CONF_VAT_CONS
from .const import CONF_NAME, CONF_BACKUP_SOURCE, CONF_BACKUP
import logging

_LOGGER = logging.getLogger(__name__)

PRECISION = 0.001

class DynPriceEntity(CoordinatorEntity):
    def __init__(self, coordinator): #, id):
        super().__init__(coordinator)

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "attribution": ATTRIBUTION,
            "id": str(self.coordinator.data.get("id")),
            "integration": DOMAIN,
        }

@dataclass
class DynPriceSensorDescription(SensorEntityDescription):
    # add additional attributes if applicable
    scale: float = None    # scaling factor 
    extra: float = None    # scaling factor : result = scale * value + extra
    minus: float = None    # scaling factor : result = scale * value - minus
    vat:   float = None    # final stcaling: result = value * vat 
    static_value:  float = None # fixed static value from config entry
    with_attribs:   bool = False # add time series as attributes
    statusdata:     str = None # string containing name of statusdata field
    source: str = None # source of information: entsoe or 'backup' or 'any'



class DynPriceSensor(DynPriceEntity, SensorEntity):
    """Sensor class."""
    def __init__(self, coordinator, device_info, description: DynPriceSensorDescription):
        DynPriceEntity.__init__(self, coordinator)
        #self._id = id
        self.entity_description: DynPriceSensorDescription = description
        self._attr_device_info = device_info
        self._platform_name = 'sensor'
        self.count_entsoe = 0
        self.count_backup = 0
        self.count_any    = 0
        """self._value = value # typically a static value from config entry
        self._scale = scale # scaling factor 
        self._extro = extra # extra cost"""

    @property
    def name(self):
        """Return the name."""
        #return f"{self._platform_name} {self.entity_description.name}"
        return f"{self.entity_description.name}"

    @property
    def unique_id(self) -> Optional[str]:
        return f"{self._platform_name}_{self.entity_description.key}"  


    def _calc_price(self, price):
        res = price
        if self.entity_description.scale: res = res * self.entity_description.scale 
        if self.entity_description.extra: res = res + self.entity_description.extra
        if self.entity_description.minus: res = res - self.entity_description.minus
        if self.entity_description.vat:   res = res * self.entity_description.vat
        return res


    def _calc_price_rec(self, rec):
        rec['price'] = self._calc_price(rec["price"])
        return rec


    @property
    def native_value(self):
        error  = None
        error1 = None
        error2 = None
        """Return the native value of the sensor."""
        if   self.entity_description.static_value: return self.entity_description.static_value # static config variable
        elif self.entity_description.statusdata:   return self.coordinator.statusdata.get(self.entity_description.statusdata)
        else:
            #_LOGGER.error(f"no error - coordinator data in sensor native value: {self.coordinator.data}")
            now = datetime.utcnow()
            nowday = now.day
            nextday = (now + timedelta(days=1)).day
            nowhour = now.hour
            rec = None
            prices = {} 
            if self.coordinator.data:
                source = self.entity_description.source
                if source == "any": sources = self.coordinator.sources
                else: sources = [source]  
                
                firstprice = None 
                nextprice  = None
                if len(sources) > 0:
                    firstsource = sources[0]
                    rec = None
                    #_LOGGER.warning(f"firstsource {firstsource} data : {self.coordinator.data}")
                    if self.coordinator.data[firstsource]: rec = self.coordinator.data[firstsource].get((nowday, nowhour, 0,) , None)
                    if rec: firstprice = rec["price"]
                    else: 
                        if self.coordinator.cyclecount > 6:
                            error1 = f"Warning: no data from {firstsource} for now: day={nowday} hour={nowhour}"
                            _LOGGER.warning(error1)

                if len(sources) > 1:
                    nextsource = sources[1]
                    rec = None
                    if self.coordinator.data[nextsource]: rec = self.coordinator.data[nextsource].get((nowday, nowhour, 0,) , None)
                    if rec: nextprice = rec["price"]
                    else: 
                        if self.coordinator.cyclecount > 6: 
                            error2 = f"Warning: no data from {nextsource} for now: day={nowday} hour={nowhour}"
                            _LOGGER.warning(error2)

                if (firstprice != None) and (nextprice != None) and abs(firstprice - nextprice) > PRECISION: 
                    error = f"Error: sources inconsistent {firstsource}: {firstprice}, {nextsource}: {nextprice}"
                    _LOGGER.warning(error)
                    price = max(firstprice, nextprice)
                elif (firstprice == None) and (nextprice != None): price = nextprice
                else: price = firstprice
            if error  and not self.coordinator.statusdata["mergestatus"]:          self.coordinator.statusdata["mergestatus"] = error
            if error1 and not self.coordinator.statusdata[f"{firstsource}status"]: self.coordinator.statusdata[f"{firstsource}status"] = error1
            if error2 and not self.coordinator.statusdata[f"{nextsource}status"]:  self.coordinator.statusdata[f"{nextsource}status"]  = error2
            return self._calc_price(price)


    
    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if self.entity_description.with_attribs:
            localday = datetime.now().day
            #localtomorrow = (datetime.now() + timedelta(days=1)).day

            thismin = 9999
            thismax = -9999
            #raw_today[source] = []
            #today[source] = []
            peak = []
            off_peak_1 = []
            off_peak_2 = []
            raw_today = []
            today = []
            self._attrs = {}
            error_count = 0
            count = 0
            if self.coordinator.data: # probably useless teest
                source = self.entity_description.source
                if source == "any": sources = self.coordinator.sources
                else: sources = [source]
                error  = None
                firstprice = {}
                nextprice  = {}
                if len(sources) > 0:
                    firstsource = sources[0]
                    #_LOGGER.warning(f"firstsource {firstsource} data : {self.coordinator.data}")
                    if self.coordinator.data[firstsource]: 
                        for (day, hour, minute,), rec in self.coordinator.data[firstsource].items():
                            newrec = rec.copy()
                            newrec["price"] = self._calc_price(rec["price"])
                            firstprice[(day, hour, minute,)] = newrec
                    #_LOGGER.warning(f"firstprice: {firstsource} {firstprice}")
                if len(sources) > 1:
                    nextsource = sources[1]
                    if self.coordinator.data[nextsource]:
                        for (day, hour, minute,), rec in self.coordinator.data[nextsource].items():
                            newrec = rec.copy()
                            newrec["price"] = self._calc_price(rec["price"])
                            nextprice[(day, hour, minute,)] = newrec
                    #_LOGGER.warning(f"nextprice: {nextsource} {nextprice}")

                for (day, hour, minute,), nextvalue in nextprice.items(): # merge into firstprice
                    firstvalue = firstprice.get((day, hour, minute,), None)
                    error = None
                    if firstvalue:
                        if (firstvalue.get("price") != None) and (nextvalue.get("price") != None) and  abs(nextvalue["price"] - firstvalue["price"]) > PRECISION:
                            error = f"Error: sources inconsistent day/hour data {firstsource}: {firstprice}, {nextsource}: {nextprice}"
                            error_count = error_count + 1
                            firstprice[(day, hour, minute,)]["price"] = max(firstvalue["price"], nextvalue["price"])
                    else: 
                        error =  f"Error: no firstsource day/hour data {firstsource}: {firstprice}, {nextsource}: {nextprice}"
                        error_count = error_count +1
                    if error:  
                        if error_count < 3: _LOGGER.warning(error)
                        else:_LOGGER.debug(error)
                    if (firstvalue == None) and (nextvalue != None): firstprice[(day, hour, minute,)] = nextvalue

                #_LOGGER.warning(f"firstprice merged {source}: {firstprice}")
                for (day, hour, minute,), value in firstprice.items(): # scan merged items
                    price = value["price"]
                    if price != None:  
                        count = count + 1
                        if price < thismin: thismin = price
                        if price > thismax: thismax = price
                        zulutime = value["zulutime"]
                        localtime = dt.as_local( value["localtime"] )
                        interval = value["interval"]

                        if localtime.hour in PEAKHOURS: peak.append(price)
                        if localtime.hour in OFFPEAKHOURS1: off_peak_1.append(price)
                        if localtime.hour in OFFPEAKHOURS2: off_peak_2.append(price)
                        today.append(price)
                        raw_today.append( {"start": localtime, "end": localtime + timedelta(seconds=interval) , "value": price } )
                if not error: error = f"OK"

                if len(today) > 0: self._attrs = { 
                        'current_price': self.native_value,
                        'average': mean(today),
                        'off_peak_1': mean(off_peak_1) if off_peak_1 else 0,
                        'off_peak_2': mean(off_peak_2) if off_peak_2 else 0,
                        'peak': mean(peak) if peak else 0,
                        'min': thismin,
                        'max': thismax,
                        'unit':  "kWh",
                        'currency' : CURRENCY_EURO,
                        'country': None,
                        'region': 'BE',
                        'low_price': False,
                        #'tomorrow_valid': False,
                        'today': today,
                        #'tomorrow': tomorrow,
                        'raw_today': raw_today,
                        #'raw_tomorrow': raw_tomorrow,
                    }
            self.coordinator.statusdata["mergecount"] = count - error_count
            self.coordinator.merge_errorcount = error_count
            if error  and not self.coordinator.statusdata.get("mergestatus"): self.coordinator.statusdata["mergestatus"] = error
            return self._attrs
        else: return None    



async def async_setup_entry(hass, entry, async_add_entities):
    """Setup sensor platform."""
    entities = []
    coordinator = hass.data[DOMAIN][entry.entry_id]
    name = entry.options[CONF_NAME]
    _LOGGER.info(f"no error - device entry content {dir(entry)} entry_id: {entry.entry_id} data: {entry.data} options: {entry.options} state: {entry.state} source: {entry.source}")
    device_info = { "identifiers": {(DOMAIN,)},   "name" : NAME, }
    # entry.data is a dict that the config flow attributes
    if entry.options[CONF_ENTSOE_TOKEN]:
        descr = DynPriceSensorDescription( 
            name=f"{name} Entsoe Price",
            key=f"{name}_entsoe_price",
            native_unit_of_measurement=f"{CURRENCY_EURO}/MWh",
            #device_class = DEVICE_CLASS_MONETARY,
            with_attribs = True,
            source       = "entsoe",
        )
        sensor = DynPriceSensor(coordinator, device_info, descr)
        entities.append(sensor)
        
        descr = DynPriceSensorDescription( 
            name=f"{name} entsoe data quality",
            key=f"{name}_entsoe_data_quality",
            source = "entsoe",
            entity_category = EntityCategory.DIAGNOSTIC,
            statusdata = "entsoestatus",
        )
        sensor = DynPriceSensor(coordinator, device_info, descr)
        entities.append(sensor)
        
        descr = DynPriceSensorDescription( 
            name=f"{name} entsoe data count",
            key=f"{name}_entsoe_data_count",
            source = "entsoe",
            entity_category = EntityCategory.DIAGNOSTIC,
            statusdata = "entsoecount",
        )
        sensor = DynPriceSensor(coordinator, device_info, descr)
        entities.append(sensor)

    if entry.options[CONF_BACKUP] and entry.options[CONF_BACKUP_SOURCE]:
        descr = DynPriceSensorDescription( 
            name=f"{name} Backup Price",
            key=f"{name}_backup_price",
            native_unit_of_measurement=f"{CURRENCY_EURO}/MWh",
            #device_class = DEVICE_CLASS_MONETARY,
            with_attribs = True,
            source       = "backup",
        )
        sensor = DynPriceSensor(coordinator, device_info, descr)
        entities.append(sensor)

        descr = DynPriceSensorDescription( 
            name=f"{name} backup data quality",
            key=f"{name}_backup_data_quality",
            source = "backup",
            entity_category = EntityCategory.DIAGNOSTIC,
            statusdata = "backupstatus",
        )
        sensor = DynPriceSensor(coordinator, device_info, descr)
        entities.append(sensor)

        descr = DynPriceSensorDescription( 
            name=f"{name} backup data count",
            key=f"{name}_backup_data_count",
            source = "backup",
            entity_category = EntityCategory.DIAGNOSTIC,
            statusdata = "backupcount",
        )
        sensor = DynPriceSensor(coordinator, device_info, descr)
        entities.append(sensor)
    if True:
        descr = DynPriceSensorDescription( 
            name=f"{name} Consumption Price",
            key=f"{name}_consumption_price",
            native_unit_of_measurement=f"{CURRENCY_EURO}/kWh",
            #device_class = DEVICE_CLASS_MONETARY,
            scale=entry.options[CONF_ENTSOE_FACTOR_A],
            extra=entry.options[CONF_ENTSOE_FACTOR_B],
            vat=entry.options[CONF_VAT_CONS],
            with_attribs = True,
            source = "any",
        )
        sensor = DynPriceSensor(coordinator, device_info, descr)
        entities.append(sensor)

        descr = DynPriceSensorDescription( 
            name=f"{name} Injection Price",
            key=f"{name}_injection_price",
            native_unit_of_measurement=f"{CURRENCY_EURO}/kWh",
            #device_class = DEVICE_CLASS_MONETARY,
            scale=entry.options[CONF_ENTSOE_FACTOR_C],
            minus=entry.options[CONF_ENTSOE_FACTOR_D],
            vat=entry.options[CONF_VAT_INJ],
            with_attribs = True,
            source = "any"
        )
        sensor = DynPriceSensor(coordinator, device_info, descr)
        entities.append(sensor)

        descr = DynPriceSensorDescription( 
            name=f"{name} Factor A Consumption Scale",
            key=f"{name}_factor_a_consumption_scale",
            static_value = entry.options[CONF_ENTSOE_FACTOR_A],
            entity_category = EntityCategory.DIAGNOSTIC,
        )
        sensor = DynPriceSensor(coordinator, device_info, descr)
        entities.append(sensor)

        descr = DynPriceSensorDescription( 
            name=f"{name} Factor B Consumption Extracost",
            key=f"{name}_factor_b_consumption_extracost",
            native_unit_of_measurement=f"{CURRENCY_EURO}/MWh",
            #device_class = DEVICE_CLASS_MONETARY,
            static_value = entry.options[CONF_ENTSOE_FACTOR_B],
            entity_category = EntityCategory.DIAGNOSTIC,
        )
        sensor = DynPriceSensor(coordinator, device_info, descr)
        entities.append(sensor)

        descr = DynPriceSensorDescription( 
            name=f"{name} Factor C Production Scale",
            key=f"{name}_factor_c_production_scale",
            static_value = entry.options[CONF_ENTSOE_FACTOR_C],
            entity_category = EntityCategory.DIAGNOSTIC,
        )
        sensor = DynPriceSensor(coordinator, device_info, descr)
        entities.append(sensor)

        descr = DynPriceSensorDescription( 
            name=f"{name} Factor D Production Extrafee",
            key=f"{name}_factor_d_production_extrafee",
            native_unit_of_measurement=f"{CURRENCY_EURO}/MWh",
            #device_class = DEVICE_CLASS_MONETARY,
            static_value = entry.options[CONF_ENTSOE_FACTOR_D],
            entity_category = EntityCategory.DIAGNOSTIC,
        )
        sensor = DynPriceSensor(coordinator, device_info, descr)
        entities.append(sensor)

        descr = DynPriceSensorDescription( 
            name=f"{name} VAT scaling factor on injection",
            key=f"{name}_VAT_scaling_factor_on_injection",
            static_value = entry.options[CONF_VAT_INJ],
            entity_category = EntityCategory.DIAGNOSTIC,
        )
        sensor = DynPriceSensor(coordinator, device_info, descr)
        entities.append(sensor)

        descr = DynPriceSensorDescription( 
            name=f"{name} VAT scaling factor on consumption",
            key=f"{name}_VAT_scaling_factor_on_consumption",
            static_value = entry.options[CONF_VAT_CONS],
            entity_category = EntityCategory.DIAGNOSTIC,
        )
        sensor = DynPriceSensor(coordinator, device_info, descr)
        entities.append(sensor)

        descr = DynPriceSensorDescription( 
            name=f"{name} data merge quality",
            key=f"{name}_data_merge_quality",
            source = "any",
            entity_category = EntityCategory.DIAGNOSTIC,
            statusdata = "mergestatus",
        )
        sensor = DynPriceSensor(coordinator, device_info, descr)
        entities.append(sensor)

        descr = DynPriceSensorDescription( 
            name=f"{name} data merge count",
            key=f"{name}_data_merge_count",
            source = "any",
            entity_category = EntityCategory.DIAGNOSTIC,
            statusdata = "mergecount",
        )
        sensor = DynPriceSensor(coordinator, device_info, descr)
        entities.append(sensor)

    _LOGGER.info(f"coordinator data in setup entry: {coordinator.data}")   
    async_add_entities(entities)




