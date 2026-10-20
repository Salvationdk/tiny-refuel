"""Configure Tiny Refuel without accounts, API keys or YAML."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import CONF_SCAN_HOURS, DEFAULT_SCAN_HOURS, DOMAIN
from .entity_data import positive
from .catalog_store import CATALOG_FILES

TYPE_LABELS = {"personbil":"Personbil", "varebil":"Varebil", "lastbil":"Lastbil", "motorcykel":"Motorcykel", "knallert":"Knallert", "bus":"Bus", "traktor":"Traktor", "andet":"Andet"}


class TinyRefuelConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return TinyRefuelOptionsFlow()

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="Tiny Refuel", data=user_input)
        return self.async_show_form(step_id="user", data_schema=vol.Schema({
            vol.Required(CONF_SCAN_HOURS, default=DEFAULT_SCAN_HOURS): vol.All(vol.Coerce(int), vol.Range(min=1, max=24))
        }))


class TinyRefuelOptionsFlow(config_entries.OptionsFlow):
    """Manage shared vehicles without changing existing dashboard configurations."""

    def _options(self):
        return dict(self.config_entry.options)

    def _vehicles(self):
        return [dict(vehicle) for vehicle in self.config_entry.options.get("vehicles", [])]

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(step_id="init", menu_options=["settings", "station_sensors", "map", "catalog_vehicle", "vehicle", "edit_vehicle", "remove_vehicle"])

    async def async_step_settings(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data={**self._options(), **user_input})
        hours = self.config_entry.options.get(CONF_SCAN_HOURS, self.config_entry.data.get(CONF_SCAN_HOURS, DEFAULT_SCAN_HOURS))
        return self.async_show_form(step_id="settings", data_schema=vol.Schema({
            vol.Required(CONF_SCAN_HOURS, default=hours): vol.All(vol.Coerce(int), vol.Range(min=1, max=24)),
            vol.Optional("history_days",default=self.config_entry.options.get("history_days",90)):
                vol.All(vol.Coerce(int),vol.Range(min=0,max=365))}))


    async def async_step_station_sensors(self, user_input=None):
        from homeassistant.helpers import selector
        from .data_services import STATION_ID
        if user_input is not None:
            ids = list(dict.fromkeys(user_input.get("station_sensor_ids", [])))
            vol.Schema([STATION_ID])(ids)
            if len(ids) > 50:
                return self.async_abort(reason="too_many_stations")
            return self.async_create_entry(title="", data={**self._options(), "station_sensor_ids": ids})
        manager = self.hass.data.get(DOMAIN, {}).get("manager")
        if manager is None:
            return self.async_abort(reason="stations_unavailable")
        snapshot = await self.hass.async_add_executor_job(manager.station_snapshot)
        rows = sorted(snapshot["stations"], key=lambda r: (r["brand"], r["name"], r["id"]))
        choices = {row["id"]: row["brand"] + " · " + row["name"] + (" · " + row["charger_kind"] if row.get("charger_kind") else "") for row in rows}
        saved = self._options().get("station_sensor_ids", [])
        for uid in saved:
            choices.setdefault(uid, uid + " · ikke i seneste hentning")
        return self.async_show_form(step_id="station_sensors", data_schema=vol.Schema({
            vol.Required("station_sensor_ids", default=saved): selector.SelectSelector(
                selector.SelectSelectorConfig(options=[{"value": k, "label": v} for k, v in choices.items()],
                                              multiple=True, mode=selector.SelectSelectorMode.DROPDOWN))}))

    async def async_step_map(self, user_input=None):
        from homeassistant.helpers import selector
        from .entity_data import BRANDS
        if user_input is not None:
            user_input={**user_input,'map_location_entity':user_input.get('map_location_entity','')}
            self._map_options=user_input
            if user_input.get('map_enabled') and user_input.get('map_selected_only'):
                return await self.async_step_map_stations()
            return self.async_create_entry(title='',data={**self._options(),**user_input})
        options=self._options()
        fields={vol.Required('map_enabled',default=options.get('map_enabled',False)):bool,
                vol.Required('map_radius_km',default=options.get('map_radius_km',25)):
                    vol.All(vol.Coerce(float),vol.Range(min=1,max=500)),
                vol.Required('map_limit',default=options.get('map_limit',100)):
                    vol.All(vol.Coerce(int),vol.Range(min=1,max=250)),
                vol.Required('map_brands',default=options.get('map_brands',[])):
                    selector.SelectSelector(selector.SelectSelectorConfig(options=list(BRANDS),multiple=True)),
                vol.Required('map_selected_only',default=options.get('map_selected_only',False)):bool}
        key=(vol.Optional('map_location_entity',default=options['map_location_entity'])
             if options.get('map_location_entity') else vol.Optional('map_location_entity'))
        fields[key]=selector.EntitySelector(selector.EntitySelectorConfig(domain=['person','device_tracker','zone']))
        return self.async_show_form(step_id='map',data_schema=vol.Schema(fields))

    async def async_step_map_stations(self, user_input=None):
        from homeassistant.helpers import selector
        from .geo_location import map_selection, map_sites
        manager=self.hass.data.get(DOMAIN,{}).get('manager')
        if manager is None:return self.async_abort(reason='stations_unavailable')
        if user_input is not None:
            return self.async_create_entry(title='',data={**self._options(),**self._map_options,**user_input})
        # Apply the selected area/brands first; HA's dropdown can search labels.
        rows,_=map_selection(self.hass,manager,{**self._map_options,'map_selected_only':False,'map_limit':1000})
        saved=set(self._options().get('map_station_ids',[]))
        rows.extend(row for row in map_sites(manager.station_snapshot()['stations']) if saved.intersection(row['member_ids']) and row['id'] not in {r['id'] for r in rows})
        if not rows:return self.async_abort(reason='stations_unavailable')
        options=[{'value':r['id'],'label':r['brand']+' · '+r['name']+(' · '+r['charger_kind'] if r.get('charger_kind') else '')} for r in rows]
        defaults=[r['id'] for r in rows if saved.intersection(r['member_ids'])]
        return self.async_show_form(step_id='map_stations',data_schema=vol.Schema({
            vol.Required('map_station_ids',default=defaults):vol.All(
                selector.SelectSelector(selector.SelectSelectorConfig(options=options,multiple=True)),vol.Length(min=1))}))

    async def _choose_vehicle(self, step, user_input):
        vehicles = self._vehicles()
        if not vehicles:
            return self.async_abort(reason="no_vehicles")
        if user_input is not None:
            self._vehicle_id = user_input["vehicle_id"]
            if step == "remove_vehicle":
                return self.async_create_entry(title="", data={**self._options(), "vehicles": [v for v in vehicles if v["id"] != self._vehicle_id]})
            return await self.async_step_vehicle()
        return self.async_show_form(step_id=step, data_schema=vol.Schema({
            vol.Required("vehicle_id"): vol.In({v["id"]: v["navn"] for v in vehicles})}))

    async def async_step_edit_vehicle(self, user_input=None):
        return await self._choose_vehicle("edit_vehicle", user_input)

    async def async_step_remove_vehicle(self, user_input=None):
        return await self._choose_vehicle("remove_vehicle", user_input)

    async def async_step_catalog_vehicle(self, user_input=None):
        if user_input is not None:
            type_ = user_input.get("koeretoejstype")
            if type_ not in CATALOG_FILES:
                return self.async_abort(reason="catalog_unavailable")
            store = self.hass.data.get(DOMAIN, {}).get("catalogs")
            if store is None:return self.async_abort(reason="catalog_unavailable")
            self._catalog_type = type_
            self._selected_catalog = await store.get(type_)
            if not self._selected_catalog.get("brands"):return self.async_abort(reason="catalog_unavailable")
            return await self.async_step_catalog_make()
        return self.async_show_form(step_id="catalog_vehicle", data_schema=vol.Schema({
            vol.Required("koeretoejstype"):vol.In(TYPE_LABELS)}))

    async def async_step_catalog_make(self, user_input=None):
        from homeassistant.helpers import selector
        brands = self._selected_catalog['brands']
        if user_input is not None:
            self._catalog_make = next((b for b in brands if b['mærke']==user_input.get('mærke')),None)
            if self._catalog_make is None:return self.async_abort(reason="catalog_unavailable")
            return await self.async_step_catalog_model()
        return self.async_show_form(step_id="catalog_make",data_schema=vol.Schema({
            vol.Required("mærke"):selector.SelectSelector(selector.SelectSelectorConfig(
                options=[b['mærke'] for b in brands],mode=selector.SelectSelectorMode.DROPDOWN))}))

    async def async_step_catalog_model(self, user_input=None):
        from homeassistant.helpers import selector
        models = self._catalog_make['modeller']
        if user_input is not None:
            self._catalog_model = next((m for m in models if m['model']==user_input.get('model')),None)
            if self._catalog_model is None:return self.async_abort(reason="catalog_unavailable")
            variants=self._catalog_model.get('variants',[])
            if variants:return await self.async_step_catalog_variant()
            self._set_catalog_defaults(self._catalog_model)
            return await self.async_step_vehicle()
        return self.async_show_form(step_id="catalog_model",data_schema=vol.Schema({
            vol.Required("model"):selector.SelectSelector(selector.SelectSelectorConfig(
                options=[m['model'] for m in models],mode=selector.SelectSelectorMode.DROPDOWN))}))

    async def async_step_catalog_variant(self, user_input=None):
        variants=self._catalog_model.get('variants',[])
        if user_input is not None:
            chosen=next((v for i,v in enumerate(variants) if str(i)==user_input.get('variant_choice')),None)
            if chosen is None and user_input.get('variant_choice')!='manual':return self.async_abort(reason="catalog_unavailable")
            self._set_catalog_defaults(chosen, manual=chosen is None)
            return await self.async_step_vehicle()
        return self.async_show_form(step_id="catalog_variant",data_schema=vol.Schema({
            vol.Required("variant_choice"):vol.In({"manual":"Indtast kapacitet selv",**{str(i):self._variant_label(v) for i,v in enumerate(variants)}})}))

    @staticmethod
    def _variant_label(variant):
        parts = [variant['name']]
        scope = variant.get('capacity_scope') or {}
        start, end = scope.get('production_start'), scope.get('production_end')
        if start or end:
            parts.append(f"produktion {start or '?'}–{end or '?'}")
        if scope.get('market'):
            parts.append(str(scope['market']))
        fuels = variant.get('fuel_types') or [variant.get('brændstof')]
        parts.extend(str(fuel) for fuel in fuels if fuel)
        for key, unit in [('tank_l', 'L'), ('batteri_kwh', 'kWh')]:
            if positive(variant.get(key)):
                parts.append(f"{variant[key]:g} {unit}")
        if variant.get('capacity_status') == 'needs_review':
            parts.append('mangler tjek')
        return ' · '.join(parts)

    def _set_catalog_defaults(self, source, manual=False):
        model=self._catalog_model; make=self._catalog_make['mærke']
        source=source or {}
        values={"mærke":make,"model":model['model'],"koeretoejstype":self._catalog_type,"navn":make+' '+model['model']}
        # A scoped variant never inherits a conflicting model-level capacity/fuel.
        fuel=source.get('brændstof')
        if not fuel:
            fuels=source.get('fuel_types',[])
            if len(fuels)==1:fuel={'benzin':'benzin','diesel':'diesel','el':'el'}.get(fuels[0].casefold())
        if fuel:values['brændstof']=fuel
        if not manual:
            for field,target in [('tank_l','tank_liters'),('batteri_kwh','batteri_kwh')]:
                if positive(source.get(field)):values[target]=source[field]
        if source is not model and source.get('name'):values['variant']=source['name']
        self._catalog_defaults=values
        self._catalog_evidence={k:source[k] for k in ('capacity_status','capacity_source_urls','capacity_checked_at','capacity_scope') if k in source}

    async def async_step_vehicle(self, user_input=None):
        from uuid import uuid4
        from homeassistant.helpers import selector
        vehicles = self._vehicles()
        vehicle_id = getattr(self, "_vehicle_id", None)
        old = next((v for v in vehicles if v["id"] == vehicle_id), {})
        defaults = getattr(self,"_catalog_defaults",None) or old
        if user_input is not None:
            vehicle = {key: value.strip() if isinstance(value, str) else value for key, value in user_input.items()
                       if value is not None and value != ""}
            invalid = {key: "invalid_capacity" for key in ("tank_liters", "batteri_kwh")
                       if key in vehicle and not positive(vehicle[key])}
            if invalid:
                return self.async_show_form(step_id="vehicle", data_schema=self._vehicle_schema(defaults, selector), errors=invalid)
            if not vehicle.get("navn"):
                return self.async_show_form(step_id="vehicle", data_schema=self._vehicle_schema(user_input, selector), errors={"navn": "required_name"})
            evidence=getattr(self,'_catalog_evidence',None) or {k:old[k] for k in (
                'capacity_status','capacity_source_urls','capacity_checked_at','capacity_scope') if k in old}
            basis=getattr(self,'_catalog_defaults',None) or old
            changed=any(vehicle.get(k)!=basis.get(k) for k in ('tank_liters','batteri_kwh','brændstof','variant','aargang'))
            if evidence:
                vehicle.update(evidence)
                if changed:vehicle['capacity_status']='needs_review'
            elif not old:vehicle['capacity_status']='user_entered'
            vehicle["id"] = vehicle_id or uuid4().hex
            fuel = vehicle["brændstof"]
            vehicle["vis"] = {"benzin": fuel in ("benzin", "hybrid", "plug_in_hybrid"),
                              "diesel": fuel == "diesel", "el": fuel in ("el", "plug_in_hybrid"), "andet": True}
            vehicles = [vehicle if v["id"] == vehicle["id"] else v for v in vehicles]
            if not old:
                vehicles.append(vehicle)
            return self.async_create_entry(title="", data={**self._options(), "vehicles": vehicles})
        return self.async_show_form(step_id="vehicle", data_schema=self._vehicle_schema(defaults, selector))

    @staticmethod
    def _vehicle_schema(vehicle, selector):
        def optional(key):
            return vol.Optional(key, default=vehicle[key]) if key in vehicle else vol.Optional(key)
        return vol.Schema({
            vol.Required("navn", default=vehicle.get("navn", "")): str,
            optional("koeretoejstype"): vol.In(TYPE_LABELS),
            optional("mærke"): str,
            optional("model"): str,
            optional("variant"): str,
            optional("aargang"): vol.All(vol.Coerce(int),vol.Range(min=1886,max=2100)),
            (vol.Required("brændstof", default=vehicle["brændstof"]) if vehicle.get("brændstof") else vol.Required("brændstof")): vol.In({
                "benzin": "Benzin", "diesel": "Diesel", "el": "El", "hybrid": "Hybrid uden stik", "plug_in_hybrid": "Plug-in-hybrid"}),
            optional("tank_liters"): vol.All(vol.Coerce(float), vol.Range(min=0.01)),
            optional("batteri_kwh"): vol.All(vol.Coerce(float), vol.Range(min=0.01)),
            optional("location_entity"): selector.EntitySelector(selector.EntitySelectorConfig(domain=["device_tracker", "person", "zone"])),
            optional("notify_service"): str,
        })

