"""Action button entities for the EZHU KVM48 Power System integration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EzhuKvmConfigEntry
from .coordinator import EzhuKvmDataUpdateCoordinator
from .entity import EzhuKvmEntity


@dataclass(frozen=True, kw_only=True)
class EzhuKvmButtonDescription(ButtonEntityDescription):
    """Describe an EZHU KVM48 remote command button entity."""

    press_fn: Callable[[EzhuKvmDataUpdateCoordinator], Awaitable[None]]


BUTTON_DESCRIPTIONS: tuple[EzhuKvmButtonDescription, ...] = (
    EzhuKvmButtonDescription(
        key="refresh_all",
        name="Refresh All Parameters",
        icon="mdi:refresh",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda c: c.async_force_full_refresh(),
    ),
    EzhuKvmButtonDescription(
        key="sync_datetime",
        name="Sync Controller Clock (SetDateTime)",
        icon="mdi:clock-check-outline",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda c: c.async_sync_datetime(),
    ),
    EzhuKvmButtonDescription(
        key="start_battery_test",
        name="Start Battery Discharge Test",
        icon="mdi:play-circle-outline",
        press_fn=lambda c: c.async_set_test_state(True),
    ),
    EzhuKvmButtonDescription(
        key="stop_battery_test",
        name="Stop Battery Discharge Test",
        icon="mdi:stop-circle-outline",
        press_fn=lambda c: c.async_set_test_state(False),
    ),
    EzhuKvmButtonDescription(
        key="clear_telemetry_log",
        name="Clear Telemetry Archive Log",
        icon="mdi:database-remove-outline",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda c: c.async_clear_log(),
    ),
    EzhuKvmButtonDescription(
        key="clear_battery_test_log",
        name="Clear Battery Test Log",
        icon="mdi:playlist-remove",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda c: c.async_clear_test_ab_record(),
    ),
    EzhuKvmButtonDescription(
        key="send_test_snmp_trap",
        name="Send Test SNMP Trap",
        icon="mdi:bell-ring-outline",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda c: c.async_send_snmp_trap(0, 0),
    ),
    EzhuKvmButtonDescription(
        key="reboot_controller",
        name="Reboot Controller (ResetDevice)",
        device_class=ButtonDeviceClass.RESTART,
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda c: c.async_reset_device(),
    ),
    EzhuKvmButtonDescription(
        key="restore_factory_defaults",
        name="Restore Factory Defaults",
        icon="mdi:factory",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        press_fn=lambda c: c.async_set_factory_defaults(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EzhuKvmConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EZHU KVM48 action button entities."""
    coordinator = entry.runtime_data
    async_add_entities(
        EzhuKvmButton(coordinator, desc) for desc in BUTTON_DESCRIPTIONS
    )


class EzhuKvmButton(EzhuKvmEntity, ButtonEntity):
    """Representation of an EZHU KVM48 one-shot command button."""

    entity_description: EzhuKvmButtonDescription

    def __init__(
        self,
        coordinator: EzhuKvmDataUpdateCoordinator,
        description: EzhuKvmButtonDescription,
    ) -> None:
        super().__init__(coordinator, f"button_{description.key}")
        self.entity_description = description

    async def async_press(self) -> None:
        """Execute the button command."""
        await self.entity_description.press_fn(self.coordinator)
