"""The EZHU KVM48 Power System (ЕЖУ И 14000 Б 48-160-хД / КВМ48-20) integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    Platform,
)
from homeassistant.core import HomeAssistant

from .const import (
    CONF_FACTORY_PASSWORD,
    DEFAULT_FACTORY_PASSWORD,
    DEFAULT_HOST,
    DEFAULT_PASSWORD,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import EzhuKvmDataUpdateCoordinator
from .wake_client import EzhuKvmClient

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.TEXT,
    Platform.BUTTON,
]

type EzhuKvmConfigEntry = ConfigEntry[EzhuKvmDataUpdateCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: EzhuKvmConfigEntry) -> bool:
    """Set up EZHU KVM48 Power System from a config entry."""
    cfg = {**entry.data, **entry.options}
    client = EzhuKvmClient(
        host=cfg.get(CONF_HOST, DEFAULT_HOST),
        port=int(cfg.get(CONF_PORT, DEFAULT_PORT)),
        password=cfg.get(CONF_PASSWORD, DEFAULT_PASSWORD),
        factory_password=cfg.get(CONF_FACTORY_PASSWORD, DEFAULT_FACTORY_PASSWORD),
    )
    scan_interval = int(cfg.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))

    coordinator = EzhuKvmDataUpdateCoordinator(
        hass=hass,
        config_entry=entry,
        client=client,
        scan_interval=scan_interval,
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: EzhuKvmConfigEntry
) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: EzhuKvmConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
