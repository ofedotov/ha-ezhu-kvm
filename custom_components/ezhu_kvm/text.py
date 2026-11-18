"""Read/write text entities for the EZHU KVM48 Power System integration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.text import TextEntity, TextEntityDescription, TextMode
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EzhuKvmConfigEntry
from .const import ADC_CHANNEL_DESCRIPTIONS
from .coordinator import EzhuKvmDataUpdateCoordinator, EzhuKvmSnapshot
from .entity import EzhuKvmEntity


@dataclass(frozen=True, kw_only=True)
class EzhuKvmTextDescription(TextEntityDescription):
    """Describe an EZHU KVM48 modifiable text/IP/MAC/PIN parameter."""

    value_fn: Callable[[EzhuKvmSnapshot], str]
    set_value_fn: Callable[[EzhuKvmDataUpdateCoordinator, str], Awaitable[None]]


def _set_trap_server(
    coordinator: EzhuKvmDataUpdateCoordinator, index: int, ip_value: str
) -> Awaitable[None]:
    servers = list(coordinator.data.snmp_params.trap_servers)
    while len(servers) < 5:
        servers.append("0.0.0.0")
    servers[index] = ip_value.strip()
    return coordinator.async_update_snmp_params(trap_servers=servers)


def _build_text_descriptions() -> tuple[EzhuKvmTextDescription, ...]:
    descriptions: list[EzhuKvmTextDescription] = [
        # 1. System Location (0x1E SetSysLocation)
        EzhuKvmTextDescription(
            key="sys_location",
            name="System Location (SysLocation)",
            icon="mdi:map-marker-outline",
            native_min=0,
            native_max=31,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.info_ex.sys_location,
            set_value_fn=lambda c, val: c.async_set_sys_location(val),
        ),
        # 2. Factory Device Identification Strings (0x1F SetSysInfo)
        EzhuKvmTextDescription(
            key="sys_info_hardware_id",
            name="Factory Hardware ID",
            icon="mdi:chip",
            native_min=1,
            native_max=15,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.info_ex.hardware_id,
            set_value_fn=lambda c, val: c.async_update_sys_info(hardware_id=val),
        ),
        EzhuKvmTextDescription(
            key="sys_info_dev_name",
            name="Factory Device Name",
            icon="mdi:identifier",
            native_min=1,
            native_max=15,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.info_ex.dev_name,
            set_value_fn=lambda c, val: c.async_update_sys_info(dev_name=val),
        ),
        EzhuKvmTextDescription(
            key="sys_info_serial_number",
            name="Factory Serial Number",
            icon="mdi:barcode",
            native_min=1,
            native_max=15,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.info_ex.serial_number,
            set_value_fn=lambda c, val: c.async_update_sys_info(serial_number=val),
        ),
        EzhuKvmTextDescription(
            key="sys_info_customer",
            name="Factory Customer",
            icon="mdi:domain",
            native_min=1,
            native_max=19,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.info_ex.customer,
            set_value_fn=lambda c, val: c.async_update_sys_info(customer=val),
        ),
        # 3. System User Password / PIN (0x0F / 0x10 TSysParams.Password_User)
        EzhuKvmTextDescription(
            key="sys_password_user",
            name="System User Password (6-digit PIN)",
            icon="mdi:lock-outline",
            native_min=6,
            native_max=6,
            pattern=r"^\d{6}$",
            mode=TextMode.PASSWORD,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.sys_params.password_user,
            set_value_fn=lambda c, val: c.async_update_sys_params(password_user=val),
        ),
        # 4. Ethernet Parameters (0x11 / 0x12 TEthParams)
        EzhuKvmTextDescription(
            key="eth_hostname",
            name="Ethernet HostName",
            icon="mdi:dns-outline",
            native_min=1,
            native_max=15,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.eth_params.hostname,
            set_value_fn=lambda c, val: c.async_update_eth_params(hostname=val),
        ),
        EzhuKvmTextDescription(
            key="eth_mac_addr",
            name="Ethernet MAC Address",
            icon="mdi:ethernet",
            native_min=17,
            native_max=17,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.eth_params.mac_addr,
            set_value_fn=lambda c, val: c.async_update_eth_params(mac_addr=val),
        ),
        EzhuKvmTextDescription(
            key="eth_ip_addr",
            name="Ethernet IPv4 Address",
            icon="mdi:ip-network-outline",
            native_min=7,
            native_max=15,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.eth_params.ip_addr,
            set_value_fn=lambda c, val: c.async_update_eth_params(ip_addr=val),
        ),
        EzhuKvmTextDescription(
            key="eth_def_gw",
            name="Ethernet Default Gateway",
            icon="mdi:router-network",
            native_min=7,
            native_max=15,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.eth_params.def_gw,
            set_value_fn=lambda c, val: c.async_update_eth_params(def_gw=val),
        ),
        EzhuKvmTextDescription(
            key="eth_net_mask",
            name="Ethernet Subnet Mask",
            icon="mdi:ip-outline",
            native_min=7,
            native_max=15,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.eth_params.net_mask,
            set_value_fn=lambda c, val: c.async_update_eth_params(net_mask=val),
        ),
        EzhuKvmTextDescription(
            key="eth_pri_dns",
            name="Ethernet Primary DNS",
            icon="mdi:server-network",
            native_min=7,
            native_max=15,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.eth_params.pri_dns,
            set_value_fn=lambda c, val: c.async_update_eth_params(pri_dns=val),
        ),
        EzhuKvmTextDescription(
            key="eth_sec_dns",
            name="Ethernet Secondary DNS",
            icon="mdi:server-network-outline",
            native_min=7,
            native_max=15,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.eth_params.sec_dns,
            set_value_fn=lambda c, val: c.async_update_eth_params(sec_dns=val),
        ),
        # 5. SNMP Parameters (0x13 / 0x14 TSNMPParams)
        EzhuKvmTextDescription(
            key="snmp_community_name",
            name="SNMP Community Name",
            icon="mdi:key-outline",
            native_min=1,
            native_max=15,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.snmp_params.community_name,
            set_value_fn=lambda c, val: c.async_update_snmp_params(
                community_name=val
            ),
        ),
    ]

    for idx in range(5):
        descriptions.append(
            EzhuKvmTextDescription(
                key=f"snmp_trap_server_{idx + 1}",
                name=f"SNMP Trap Server {idx + 1} IP",
                icon="mdi:server-network",
                native_min=7,
                native_max=15,
                entity_category=EntityCategory.CONFIG,
                value_fn=lambda d, i=idx: d.snmp_params.trap_servers[i],
                set_value_fn=lambda c, val, i=idx: _set_trap_server(c, i, val),
            )
        )

    # 6. ADC Channel Names for Channels 0..7 (0x07 / 0x08 TADCParams.ChannelName)
    for ch_idx, (ch_key, ch_label, _unit) in ADC_CHANNEL_DESCRIPTIONS.items():
        descriptions.append(
            EzhuKvmTextDescription(
                key=f"adc_ch{ch_idx}_{ch_key}_name",
                name=f"ADC Ch{ch_idx} ({ch_label}) Label",
                icon="mdi:tag-text-outline",
                native_min=1,
                native_max=7,
                entity_category=EntityCategory.CONFIG,
                value_fn=lambda d, ch=ch_idx: d.adc_params[ch].channel_name,
                set_value_fn=lambda c, val, ch=ch_idx: c.async_update_adc_params(
                    ch, channel_name=val
                ),
            )
        )

    return tuple(descriptions)


TEXT_DESCRIPTIONS = _build_text_descriptions()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EzhuKvmConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EZHU KVM48 modifiable text entities."""
    coordinator = entry.runtime_data
    async_add_entities(
        EzhuKvmText(coordinator, desc) for desc in TEXT_DESCRIPTIONS
    )


class EzhuKvmText(EzhuKvmEntity, TextEntity):
    """Representation of an EZHU KVM48 read/write text parameter."""

    entity_description: EzhuKvmTextDescription

    def __init__(
        self,
        coordinator: EzhuKvmDataUpdateCoordinator,
        description: EzhuKvmTextDescription,
    ) -> None:
        super().__init__(coordinator, f"text_{description.key}")
        self.entity_description = description

    @property
    def native_value(self) -> str:
        """Return the current text value."""
        return self.entity_description.value_fn(self.coordinator.data)

    async def async_set_value(self, value: str) -> None:
        """Write the updated text value to the controller."""
        await self.entity_description.set_value_fn(self.coordinator, value)
