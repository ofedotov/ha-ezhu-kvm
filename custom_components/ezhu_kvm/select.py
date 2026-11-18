"""Read/write select entities for the EZHU KVM48 Power System integration."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EzhuKvmConfigEntry
from .const import REGIME_NAME_TO_ID, REGIME_OPTIONS
from .coordinator import EzhuKvmDataUpdateCoordinator
from .entity import EzhuKvmEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EzhuKvmConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EZHU KVM48 select entities."""
    coordinator = entry.runtime_data
    async_add_entities([EzhuKvmRegimeSelect(coordinator)])


class EzhuKvmRegimeSelect(EzhuKvmEntity, SelectEntity):
    """Select entity for TABParams.regime (0x09 / 0x0A Battery Charge Regime)."""

    _attr_name = "AB Charge Regime"
    _attr_icon = "mdi:car-battery"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = list(REGIME_OPTIONS.values())

    def __init__(self, coordinator: EzhuKvmDataUpdateCoordinator) -> None:
        super().__init__(coordinator, "select_ab_regime")

    @property
    def current_option(self) -> str | None:
        """Return currently configured charge regime."""
        regime_id = self.coordinator.data.ab_params.regime
        return REGIME_OPTIONS.get(regime_id, REGIME_OPTIONS[1])

    async def async_select_option(self, option: str) -> None:
        """Change the battery charge regime and write to controller flash."""
        if option not in REGIME_NAME_TO_ID:
            raise HomeAssistantError(f"Unsupported regime option: {option}")
        await self.coordinator.async_update_ab_params(
            regime=REGIME_NAME_TO_ID[option]
        )
