"""Configure Tiny Refuel without accounts, API keys or YAML."""
import voluptuous as vol
from homeassistant import config_entries
from .const import CONF_SCAN_HOURS, DEFAULT_SCAN_HOURS, DOMAIN


class TinyRefuelConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="Tiny Refuel", data=user_input)
        return self.async_show_form(step_id="user", data_schema=vol.Schema({
            vol.Required(CONF_SCAN_HOURS, default=DEFAULT_SCAN_HOURS): vol.All(vol.Coerce(int), vol.Range(min=1, max=24))
        }))
