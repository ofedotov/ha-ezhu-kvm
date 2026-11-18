"""Read/write switch entities for the EZHU KVM48 Power System integration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EzhuKvmConfigEntry
from .const import ADC_CHANNEL_DESCRIPTIONS, ALARM_DEFINITIONS, RELAY_OUTPUT_GROUPS
from .coordinator import EzhuKvmDataUpdateCoordinator, EzhuKvmSnapshot
from .entity import EzhuKvmEntity


@dataclass(frozen=True, kw_only=True)
class EzhuKvmSwitchDescription(SwitchEntityDescription):
    """Describe an EZHU KVM48 modifiable switch parameter."""

    is_on_fn: Callable[[EzhuKvmSnapshot], bool]
    set_fn: Callable[[EzhuKvmDataUpdateCoordinator, bool], Awaitable[None]]


def _build_switch_descriptions() -> tuple[EzhuKvmSwitchDescription, ...]:
    descriptions: list[EzhuKvmSwitchDescription] = [
        # 1. Battery Discharge Test Control (0x19 SetTestState)
        EzhuKvmSwitchDescription(
            key="battery_discharge_test",
            name="Battery Discharge Test",
            icon="mdi:battery-heart-variant",
            is_on_fn=lambda d: bool(d.state.testing),
            set_fn=lambda c, val: c.async_set_test_state(val),
        ),
        # 2. System Audible Buzzer / Voice (0x0F / 0x10 TSysParams.Voice)
        EzhuKvmSwitchDescription(
            key="sys_voice",
            name="System Audible Alarm (Voice)",
            icon="mdi:volume-high",
            entity_category=EntityCategory.CONFIG,
            is_on_fn=lambda d: d.sys_params.voice,
            set_fn=lambda c, val: c.async_update_sys_params(voice=val),
        ),
        # 3. Ethernet DHCP Enabled (0x11 / 0x12 TEthParams.DHCPEnabled)
        EzhuKvmSwitchDescription(
            key="eth_dhcp_enabled",
            name="Ethernet DHCP Enabled",
            icon="mdi:ip-network",
            entity_category=EntityCategory.CONFIG,
            is_on_fn=lambda d: d.eth_params.dhcp_enabled,
            set_fn=lambda c, val: c.async_update_eth_params(dhcp_enabled=val),
        ),
    ]

    # 4. ADC Channel Enabled Flags for Channels 0..7 (0x07 / 0x08 TADCParams.ChannelEnabled)
    for ch_idx, (ch_key, ch_label, _unit) in ADC_CHANNEL_DESCRIPTIONS.items():
        descriptions.append(
            EzhuKvmSwitchDescription(
                key=f"adc_ch{ch_idx}_{ch_key}_enabled",
                name=f"ADC Ch{ch_idx} ({ch_label}) Enabled",
                icon="mdi:check-circle-outline",
                entity_category=EntityCategory.CONFIG,
                is_on_fn=lambda d, ch=ch_idx: d.adc_params[ch].channel_enabled,
                set_fn=lambda c, val, ch=ch_idx: c.async_update_adc_params(
                    ch, channel_enabled=val
                ),
            )
        )

    # 5. 40 Relay & Sound Alarm Routing Matrix Switches (0x0D / 0x0E TRelayConfiguration: 4 x 10)
    for group_idx, group_key, group_label in RELAY_OUTPUT_GROUPS:
        for alarm_idx, alarm_key, alarm_label in ALARM_DEFINITIONS:
            descriptions.append(
                EzhuKvmSwitchDescription(
                    key=f"relay_cfg_{group_key}_{alarm_key}",
                    name=f"{group_label} on {alarm_label}",
                    icon="mdi:bell-ring-outline"
                    if group_idx == 3
                    else "mdi:electric-switch",
                    entity_category=EntityCategory.CONFIG,
                    is_on_fn=lambda d, g=group_idx, a=alarm_idx: d.relay_params.get_flag(
                        g, a
                    ),
                    set_fn=lambda c, val, g=group_idx, a=alarm_idx: c.async_update_relay_flag(
                        g, a, val
                    ),
                )
            )

    return tuple(descriptions)


SWITCH_DESCRIPTIONS = _build_switch_descriptions()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EzhuKvmConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EZHU KVM48 modifiable switch entities."""
    coordinator = entry.runtime_data
    async_add_entities(
        EzhuKvmSwitch(coordinator, desc) for desc in SWITCH_DESCRIPTIONS
    )


class EzhuKvmSwitch(EzhuKvmEntity, SwitchEntity):
    """Representation of an EZHU KVM48 read/write boolean parameter."""

    entity_description: EzhuKvmSwitchDescription

    def __init__(
        self,
        coordinator: EzhuKvmDataUpdateCoordinator,
        description: EzhuKvmSwitchDescription,
    ) -> None:
        super().__init__(coordinator, f"switch_{description.key}")
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.entity_description.is_on_fn(self.coordinator.data)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        await self.entity_description.set_fn(self.coordinator, True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        await self.entity_description.set_fn(self.coordinator, False)
