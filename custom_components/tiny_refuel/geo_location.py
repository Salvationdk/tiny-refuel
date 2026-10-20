"""Opt-in physical stations on Home Assistant's standard map."""
from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change_event
from .const import DOMAIN, STATIC_URL
from .entity_data import coordinates, distance_km, vehicle_origin
from .sensor import device_info


# Only bundled assets: map markers never contact third-party logo hosts.
BRAND_LOGOS = {
    "circle k": "circle-k", "ingo": "ingo", "q8": "q8", "f24": "f24",
    "go'on": "goon", "shell": "shell", "uno-x": "uno-x", "ok": "ok",
    "oil": "oil", "clever": "clever", "e.on": "eon", "ionity": "ionity",
}


def map_selection(hass, manager, options):
    if not options.get('map_enabled'):
        return [],{'enabled':False,'count':0}
    entity=options.get('map_location_entity')
    origin=vehicle_origin(hass,{'location_entity':entity}) if entity else coordinates(
        {'lat':hass.config.latitude,'lon':hass.config.longitude})
    if origin is None:
        return [],{'enabled':True,'count':0,'origin_available':False}
    brands={b.casefold() for b in options.get('map_brands',[])}
    selected=set(options.get('map_station_ids',[]))
    radius=options.get('map_radius_km',25)
    rows=[]
    for row in manager.station_snapshot()['stations']:
        if not coordinates(row) or (brands and row['brand'].casefold() not in brands):continue
        if options.get('map_selected_only') and row['id'] not in selected:continue
        km=distance_km(origin,coordinates(row))
        if km<=radius:rows.append({**row,'distance':km})
    rows.sort(key=lambda row:(row['distance'],row['id']))
    limit=options.get('map_limit',10)
    return rows[:limit],{'enabled':True,'count':min(len(rows),limit),'matched':len(rows),
                        'limit':limit,'radius_km':radius,'origin_available':True}


async def async_setup_entry(hass, entry, async_add_entities):
    manager=entry.runtime_data
    options=dict(entry.options)
    entities={}
    active=True
    dirty=False
    task=None

    async def refresh():
        nonlocal dirty
        while active and dirty:
            dirty=False
            # Read position on HA's event loop; the station scan itself runs off-loop.
            position=options.get('map_location_entity')
            origin=vehicle_origin(hass,{'location_entity':position}) if position else coordinates(
                {'lat':hass.config.latitude,'lon':hass.config.longitude})
            # Frozen state facade avoids reading HA states from an executor thread.
            from types import SimpleNamespace
            frozen=SimpleNamespace(config=SimpleNamespace(latitude=origin[0] if origin else None,
                                                          longitude=origin[1] if origin else None))
            frozen_options={**options,'map_location_entity':None}
            rows,status=await hass.async_add_executor_job(map_selection,frozen,manager,frozen_options)
            if not active:return
            hass.data[DOMAIN]['map_status']=status
            selected={row['id']:row for row in rows}
            for uid in list(entities):
                if uid not in selected:
                    entity=entities.pop(uid)
                    await entity.async_remove()
            added=[]
            for uid,row in selected.items():
                if uid not in entities:
                    entities[uid]=StationMapEntity(row)
                    added.append(entities[uid])
                else:
                    entities[uid].row=row
                    if entities[uid].hass is not None:entities[uid].async_write_ha_state()
            if added:async_add_entities(added)

    @callback
    def schedule(*_):
        nonlocal dirty,task
        dirty=True
        if task is None or task.done():
            task=hass.async_create_background_task(refresh(),'Tiny Refuel map stations')

    unsubscribe=manager.subscribe(schedule)
    untrack=(async_track_state_change_event(hass,[options['map_location_entity']],schedule)
             if options.get('map_enabled') and options.get('map_location_entity') else lambda:None)
    @callback
    def stop():
        nonlocal active
        active=False;unsubscribe();untrack()
        if task is not None and not task.done():task.cancel()
    entry.async_on_unload(stop)
    schedule()


class StationMapEntity(GeolocationEvent):
    _attr_should_poll=False
    _attr_source=DOMAIN
    _attr_unit_of_measurement='km'
    _attr_has_entity_name=True
    _attr_device_info=device_info()

    def __init__(self,row):
        self.row=row
        self._attr_unique_id=DOMAIN+'_map_'+row['id']
        self._attr_icon='mdi:ev-station' if row['kind']=='ev' else 'mdi:gas-station'

    @property
    def name(self):return self.row['brand']+' · '+self.row['name']+(' · '+self.row['charger_kind'] if self.row.get('charger_kind') else '')

    @property
    def entity_picture(self):
        logo = BRAND_LOGOS.get(str(self.row.get("brand", "")).strip().casefold())
        return STATIC_URL + "/logos/logo-" + logo + ".svg" if logo else None

    @property
    def latitude(self):return self.row['lat']
    @property
    def longitude(self):return self.row['lon']
    @property
    def distance(self):return self.row['distance']
    @property
    def extra_state_attributes(self):
        return {'station_id':self.row['id'],'selskab':self.row['brand'],
                'adresse':self.row.get('address'),'aktuelle_priser':self.row['current'],
                'hentet':self.row.get('updated'),'ladeform':self.row.get('charger_kind'),
                **{('el_kr_kwh' if k=='kwh' else {'p95':'benzin_95_kr_l','p100':'benzin_100_kr_l','diesel':'diesel_kr_l'}[k]):v
                   for k,v in self.row['prices'].items()}}
