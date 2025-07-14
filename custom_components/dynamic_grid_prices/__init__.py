"""The DynGridPricesSolar integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryNotReady
import async_timeout
import aiohttp, asyncio
import xmltodict
import json
import logging
from datetime import datetime, timezone, timedelta
import time, pytz
from collections.abc import Mapping
from .const import ENTSOE_DAYAHEAD_URL, ENTSOE_HEADERS,STARTUP_MESSAGE, CONF_ENTSOE_AREA, CONF_ENTSOE_TOKEN, CONF_BACKUP_SOURCE, CONF_BACKUP
from .const import DOMAIN, PLATFORMS, SENSOR

# TODO List the platforms that you want to support.

SCAN_INTERVAL = timedelta(seconds=10)
UPDATE_INTERVAL = 900  # update data entities and addtibutes aligned to X seconds interval
TIMEOUT = 10
RESOLUTION = 3600 # may become 900
RETRY  = 3600

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: Config):
    """Set up this integration using YAML is not supported."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DynGridPrices from a config entry."""
    # TODO Store an API object for your platforms to access
    # hass.data[DOMAIN][entry.entry_id] = MyApi(...)
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)
    config = entry.options
    entsoe_client   = None
    entsoe_token = config.get(CONF_ENTSOE_TOKEN)
    area = config.get(CONF_ENTSOE_AREA)
    if entsoe_token: # deliberately string None since paramter is required
        entsoe_session = async_get_clientsession(hass)
        entsoe_client = EntsoeApiClient(entsoe_session, entsoe_token, area)

    coordinator = DynPriceUpdateCoordinator(hass, entsoe_client= entsoe_client, entry = entry)
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][entry.entry_id] = coordinator

    hass.async_create_task(hass.config_entries.async_forward_entry_setups(entry, PLATFORMS ))
    #for platform in PLATFORMS:
    #    if config.get(platform, True):
    #        coordinator.platforms.append(platform)
    #        hass.async_add_job(
    #            hass.config_entries.async_forward_entry_setup(entry, platform)
    #        )

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


class EntsoeApiClient:
    def __init__(self, session: aiohttp.ClientSession, token: str, area: str) -> None:
        self._token   = token
        self._area    = area
        self._session = session
        self.status  = "Unknown"
        self.count    = 0

    async def async_get_data(self) -> dict:
        #today = datetime.now()               # exceptionally in localtime
        #tomorrow = today + timedelta(days=1) # exceptionally in localtime
        now = datetime.now(timezone.utc)
        start = (now + timedelta(days=0)).strftime("%Y%m%d0000") #"202206152200"
        end   = (now + timedelta(days=1) ).strftime("%Y%m%d0000") #"202206202200"
        url = ENTSOE_DAYAHEAD_URL.format(TOKEN = self._token, AREA = self._area, START = start, END = end)
        _LOGGER.info(f"entsoe interval {start} {end} fetchingurl = {url}")
        try:
            count = 0
            async with async_timeout.timeout(TIMEOUT):
                response = await self._session.get(url, headers=ENTSOE_HEADERS)
                if response.status != 200:
                    _LOGGER.error(f'invalid response code from entsoe: {response.status}')
                    self.status = f"Error: response code: {response.status}"
                    return None
                xml = await response.text()
                xpars = xmltodict.parse(xml)
                xpars = xpars['Publication_MarketDocument']
                jsond = json.dumps(xpars, indent=2)
                _LOGGER.debug(jsond)
                series = xpars['TimeSeries']
                if isinstance(series, Mapping): series = [series]
                res = { 'firstepoch' : 0, 'lastepoch': 0, 'points': {} }
                #res = {}
                count = 0
                firstepoch = time.time() + 10*86400 
                lastepoch  = 0
                for ts in series:
                    start = ts['Period']['timeInterval']['start']
                    startts = datetime.strptime(start,'%Y-%m-%dT%H:%MZ').replace(tzinfo=timezone.utc).timestamp()
                    end = ts['Period']['timeInterval']['end']
                    if ts['Period']['resolution'] == 'PT60M': seconds = RESOLUTION
                    else: seconds = None
                    for point in ts['Period']['Point']:
                        count = count + 1
                        offset = seconds * (int(point['position'])-1)
                        timestamp = startts + offset
                        zulutime  = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                        localtime = datetime.fromtimestamp(timestamp)
                        price = float(point['price.amount'])
                        _LOGGER.info(f"{(zulutime.day, zulutime.hour, zulutime.minute,)} zulutime={datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()}Z localtime={datetime.fromtimestamp(timestamp).isoformat()} price={price}" )
                        if timestamp < firstepoch: firstepoch = timestamp
                        if timestamp > lastepoch:  lastepoch = timestamp
                        res['points'][(zulutime.day, zulutime.hour, zulutime.minute,)] = {"price": price, "interval": seconds, "zulutime":  datetime.fromtimestamp(timestamp, tz=timezone.utc), "localtime": datetime.fromtimestamp(timestamp)}
                res['firstepoch'] = firstepoch
                res['lastepoch'] = lastepoch
                _LOGGER.info(f"fetched from entsoe: {res}")
                self.status = "OK"
                self.count = count
                return res             
        except Exception as exception:
            self.status = f"Error: {exception}"
            _LOGGER.exception(f"cannot fetch api data from entsoe: {exception}") 




class DynPriceUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(  self, hass: HomeAssistant, entsoe_client: EntsoeApiClient, entry: ConfigEntry) -> None:
        """Initialize."""
        self.entsoeapi   = entsoe_client
        self.platforms = []
        self.lastentsoefetch = 0
        self.lastbackupfetch = 0
        self.entsoecache = None
        self.entsoelastday = 0
        self.backuplastday = 0
        self.cache = None # merged entsoe and ecopower data
        self.backupcache = None # nordpol data
        self.lastcheck = 0
        self.backupenabled = entry.options.get(CONF_BACKUP)
        self.backupentity = entry.options.get(CONF_BACKUP_SOURCE)
        self.sources = []
        self.hass = hass
        self.entry = entry
        self.cyclecount = 0
        self.statusdata = {}
        self.merge_errorcount = 0
        if self.entsoeapi: self.sources.append("entsoe")
        if self.backupenabled and self.backupentity: self.sources.append("backup")

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)

    async def _async_update_data(self):
        """Update data via library."""
        now = time.time()
        gmtime = time.gmtime(now)
        self.cyclecount = self.cyclecount+1
        slot = int(now)//UPDATE_INTERVAL # integer division in python3.x

        if (slot > self.lastcheck) or (self.backupenabled and self.backupentity and not self.backupcache) : # do nothing unless we are in a new time slot
            self.lastcheck = slot 
            retry = (self.merge_errorcount > 0)
            if self.entsoeapi: 
                _LOGGER.info(f"checking if entsoe api update is needed or data can be retrieved from cache at zulutime: {gmtime}")
                # reduce number of cloud fetches
                if (not self.entsoecache) or retry or ((now - self.lastentsoefetch >= RETRY) and (gmtime.tm_hour >= 11) and (self.entsoelastday <= now + 43200)):
                    entsoecount = 0
                    entsoestatus = "Unknown"
                    try:
                        res1 = await self.entsoeapi.async_get_data()
                        if res1:
                            self.lastfetch = now
                            self.entsoelastday = res1['lastepoch']
                            nonsorted = res1['points']
                            entsoestatus = self.entsoeapi.status
                            entsoecount = self.entsoeapi.count
                            self.merge_errorcount = 0 # reset
                    except Exception as exception:
                        entsoestatus = f"Error: entsoe read {exception}"
                        raise UpdateFailed() from exception
                    
                    if res1:
                        # fill the holes with previous data
                        prev = None
                        ts = res1['firstepoch']
                        while ts < res1['lastepoch'] + 0.1:
                            zulutime  = datetime.fromtimestamp(ts, tz=timezone.utc)
                            val = nonsorted.get((zulutime.day, zulutime.hour, zulutime.minute,))
                            if val == None: 
                                nonsorted[(zulutime.day, zulutime.hour, zulutime.minute,)] = prev.copy()
                                nonsorted[(zulutime.day, zulutime.hour, zulutime.minute,)]['localtime'] = datetime.fromtimestamp(ts)
                                nonsorted[(zulutime.day, zulutime.hour, zulutime.minute,)]['zulutime']  = datetime.fromtimestamp(ts, tz=timezone.utc)
                            else: prev = val
                            ts = ts + RESOLUTION
                        self.entsoecache = dict(sorted(nonsorted.items())) # sort by (day, hour, minute,)

                    self.statusdata["entsoestatus"] = entsoestatus
                    self.statusdata["entsoecount"]  = entsoecount
            if self.backupenabled and self.backupentity: # fetch nordpool style data
                firstepoch = now + 10*86400 
                lastepoch  = 0
                if (not self.backupcache) or retry or ((now - self.lastbackupfetch >= RETRY) and (gmtime.tm_hour >= 11) and (self.backuplastday <= now + 43200)):
                    backupstate = self.hass.states.get(self.backupentity)
                    if backupstate:
                        day = 0
                        nonsorted  = {}
                        count = 0
                        for inday in ['raw_today', 'raw_tomorrow']:
                            backupdata = backupstate.attributes[inday] 
                            for val in backupdata:
                                value = val['value']
                                if value:
                                    count = count + 1
                                    localstart = val['start']
                                    zulustart = val['start'].astimezone(pytz.utc)
                                    day = zulustart.day
                                    hour = zulustart.hour
                                    minute = zulustart.minute
                                    epoch = zulustart.timestamp()
                                    if epoch < firstepoch: firstepoch = epoch
                                    if epoch > lastepoch: lastepoch = epoch

                                    interval = RESOLUTION
                                    nonsorted[(day, hour, minute,)]   = {"price": value, "interval": interval, "zulutime": zulustart, "localtime": localstart}
                            
                            # fill the holes with previous data
                            prev = None
                            ts = firstepoch
                            while ts < lastepoch + 0.1:
                                zulutime  = datetime.fromtimestamp(ts, tz=timezone.utc)
                                val = nonsorted.get((zulutime.day, zulutime.hour, zulutime.minute,))
                                if val == None: 
                                    nonsorted[(zulutime.day, zulutime.hour, zulutime.minute,)] = prev.copy()
                                    nonsorted[(zulutime.day, zulutime.hour, zulutime.minute,)]['localtime'] = datetime.fromtimestamp(ts)
                                    nonsorted[(zulutime.day, zulutime.hour, zulutime.minute,)]['zulutime']  = datetime.fromtimestamp(ts, tz=timezone.utc)
                                else: prev = val
                                ts = ts + RESOLUTION
                        self.backupcache = dict(sorted(nonsorted.items())) # sort by (day, hour, minute,)
                            
                        self.statusdata["backupstatus"] = "OK"
                        self.statusdata["backupcount"]  = count
                        self.merge_errorcount = 0 # reset
                        lastbackupfetch = now
         

        # return combined cache dictionaries
        return {'entsoe': self.entsoecache,
                'backup': self.backupcache }



