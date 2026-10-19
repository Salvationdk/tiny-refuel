"""Configure Tiny Refuel without accounts, API keys or YAML."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import CONF_SCAN_HOURS, DEFAULT_SCAN_HOURS, DOMAIN
from .entity_data import positive


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
        return self.async_show_menu(step_id="init", menu_options=["settings", "vehicle", "edit_vehicle", "remove_vehicle"])

    async def async_step_settings(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data={**self._options(), **user_input})
        hours = self.config_entry.options.get(CONF_SCAN_HOURS, self.config_entry.data.get(CONF_SCAN_HOURS, DEFAULT_SCAN_HOURS))
        return self.async_show_form(step_id="settings", data_schema=vol.Schema({
            vol.Required(CONF_SCAN_HOURS, default=hours): vol.All(vol.Coerce(int), vol.Range(min=1, max=24))}))

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

    async def async_step_vehicle(self, user_input=None):
        from uuid import uuid4
        from homeassistant.helpers import selector
        vehicles = self._vehicles()
        vehicle_id = getattr(self, "_vehicle_id", None)
        old = next((v for v in vehicles if v["id"] == vehicle_id), {})
        if user_input is not None:
            vehicle = {key: value.strip() if isinstance(value, str) else value for key, value in user_input.items()
                       if value is not None and value != ""}
            invalid = {key: "invalid_capacity" for key in ("tank_liters", "batteri_kwh")
                       if key in vehicle and not positive(vehicle[key])}
            if invalid:
                return self.async_show_form(step_id="vehicle", data_schema=self._vehicle_schema(old, selector), errors=invalid)
            if not vehicle.get("navn"):
                return self.async_show_form(step_id="vehicle", data_schema=self._vehicle_schema(user_input, selector), errors={"navn": "required_name"})
            vehicle["id"] = vehicle_id or uuid4().hex
            fuel = vehicle["brændstof"]
            vehicle["vis"] = {"benzin": fuel in ("benzin", "hybrid", "plug_in_hybrid"),
                              "diesel": fuel == "diesel", "el": fuel in ("el", "plug_in_hybrid"), "andet": True}
            vehicles = [vehicle if v["id"] == vehicle["id"] else v for v in vehicles]
            if not old:
                vehicles.append(vehicle)
            return self.async_create_entry(title="", data={**self._options(), "vehicles": vehicles})
        return self.async_show_form(step_id="vehicle", data_schema=self._vehicle_schema(old, selector))

    @staticmethod
    def _vehicle_schema(vehicle, selector):
        def optional(key):
            return vol.Optional(key, default=vehicle[key]) if key in vehicle else vol.Optional(key)
        return vol.Schema({
            vol.Required("navn", default=vehicle.get("navn", "")): str,
            optional("mærke"): str,
            optional("model"): str,
            vol.Required("brændstof", default=vehicle.get("brændstof", "benzin")): vol.In({
                "benzin": "Benzin", "diesel": "Diesel", "el": "El", "hybrid": "Hybrid uden stik", "plug_in_hybrid": "Plug-in-hybrid"}),
            optional("tank_liters"): vol.All(vol.Coerce(float), vol.Range(min=0.01)),
            optional("batteri_kwh"): vol.All(vol.Coerce(float), vol.Range(min=0.01)),
            optional("location_entity"): selector.EntitySelector(selector.EntitySelectorConfig(domain=["device_tracker", "person", "zone"])),
            optional("notify_service"): str,
        })
