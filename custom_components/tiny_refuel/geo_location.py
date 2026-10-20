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


def map_sites(rows):
    """One company marker per address/coordinate; retain every source variant."""
    parents=list(range(len(rows)))
    tokens={}
    def root(index):
        while parents[index]!=index:
            parents[index]=parents[parents[index]]
            index=parents[index]
        return index
    for index,row in enumerate(rows):
        brand=str(row.get("brand","")).strip().casefold()
        keys=[]
        address=" ".join(str(row.get("address") or "").casefold().split())
        if address:keys.append(("address",brand,address))
        position=coordinates(row)
        if position:keys.append(("position",brand,round(position[0],6),round(position[1],6)))
        if not keys:keys.append(("id",row["id"]))
        for key in keys:
            if key in tokens:parents[root(index)]=root(tokens[key])
            else:tokens[key]=index
    groups={}
    for index,row in enumerate(rows):
        groups.setdefault(root(index),[]).append(row)
    sites=[]
    for variants in groups.values():
        variants=sorted(variants,key=lambda r:(r["kind"]!="fuel",r["id"]))
        primary=next((r for r in variants if coordinates(r)),variants[0])
        site=dict(primary)
        site["id"]=variants[0]["id"]
        site["member_ids"]=sorted(r["id"] for r in variants)
        site["variants"]=variants
        site["current"]=all(r["current"] for r in variants)
        kinds=sorted({r["charger_kind"] for r in variants if r.get("charger_kind")})
        site["charger_kind"]=" / ".join(kinds) or None
        # Different AC/DC prices stay separate; never invent one price for the site.
        prices={}
        for field in ("p95","p100","diesel","kwh"):
            priced=[r for r in variants if field in r["prices"]]
            values={r["prices"][field] for r in priced}
            if len(values)==1 and all(r["current"] for r in priced):
                prices[field]=next(iter(values))
        site["prices"]=prices
        sites.append(site)
    return sites


def site_information(row):
    labels={"p95":"Benzin 95","p100":"Benzin 100","diesel":"Diesel","kwh":"El"}
    parts=[]
    addresses=sorted({r["address"] for r in row.get("variants",[row]) if r.get("address")})
    if addresses:parts.append("Adresse: "+" / ".join(addresses))
    for variant in row.get("variants",[row]):
        title=variant.get("charger_kind") or ("Brændstof" if variant["kind"]=="fuel" else "Opladning")
        prices=[labels[field]+": "+format(value,".2f").replace(".",",")+(" kr/kWh" if field=="kwh" else " kr/L")
                for field,value in variant["prices"].items()]
        detail=title+" · "+(", ".join(prices) if prices else "Pris ikke oplyst")
        if not variant["current"]:detail+=" · gemte data"
        if detail not in parts:parts.append(detail)
    if row.get("updated"):parts.append("Hentet: "+str(row["updated"]))
    return "\n".join(parts)


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
    for row in map_sites(manager.station_snapshot()['stations']):
        if not coordinates(row) or (brands and row['brand'].casefold() not in brands):continue
        if options.get('map_selected_only') and not selected.intersection([row['id'],*row['member_ids']]):continue
        km=distance_km(origin,coordinates(row))
        if km<=radius:rows.append({**row,'distance':km})
    rows.sort(key=lambda row:(row['distance'],row['id']))
    limit=options.get('map_limit',100)
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
                'oplysninger':site_information(self.row),
                'station_ids':self.row.get('member_ids',[self.row['id']]),
                'ladeformer_og_priser':[{k:r.get(k) for k in ('id','kind','charger_kind','prices','current','updated','source')} for r in self.row.get('variants',[self.row])],
                **{('el_kr_kwh' if k=='kwh' else {'p95':'benzin_95_kr_l','p100':'benzin_100_kr_l','diesel':'diesel_kr_l'}[k]):v
                   for k,v in self.row['prices'].items()}}
