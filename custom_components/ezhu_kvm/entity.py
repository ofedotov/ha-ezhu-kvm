"""Base entity for the EZHU KVM48 Power System integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EzhuKvmDataUpdateCoordinator


class EzhuKvmEntity(CoordinatorEntity[EzhuKvmDataUpdateCoordinator]):
    """Base entity representing a parameter or action on the EZHU KVM48-20 controller."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EzhuKvmDataUpdateCoordinator,
        unique_key: str,
    ) -> None:
        super().__init__(coordinator)
        info = coordinator.data.info_ex
        eth = coordinator.data.eth_params
        serial = info.serial_number or coordinator.client.host
        self._attr_unique_id = f"{serial}_{unique_key}"

        connections: set[tuple[str, str]] = set()
        if eth.mac_addr and eth.mac_addr != "00:00:00:00:00:00":
            connections.add((CONNECTION_NETWORK_MAC, eth.mac_addr))

        display_name = info.dev_name or "KVM48-20"
        if info.hostname:
            display_name = f"{display_name} ({info.hostname})"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            connections=connections,
            name=display_name,
            manufacturer=info.customer or "INTEGRAL",
            model=f"ЕЖУ И 14000 Б 48-160-хД ({info.dev_name or 'КВМ48-20'})",
            hw_version=info.hardware_id or None,
            sw_version=f"{info.fw_version_str} [{info.fw_build_datetime}]",
            serial_number=info.serial_number or None,
            suggested_area=info.sys_location or None,
        )
