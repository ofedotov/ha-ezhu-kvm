"""DataUpdateCoordinator for the EZHU KVM48 Power System integration."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_CONFIG_REFRESH_CYCLES, DEFAULT_SCAN_INTERVAL, DOMAIN
from .wake_client import (
    EzhuKvmClient,
    EzhuKvmError,
    KvmAbParams,
    KvmAdcParams,
    KvmCtrlParams,
    KvmEthParams,
    KvmInfoEx,
    KvmLogRecord,
    KvmRelayParams,
    KvmSnmpParams,
    KvmState,
    KvmSysParams,
    KvmTestAbRecord,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class EzhuKvmSnapshot:
    """Complete snapshot of all live telemetry and configuration parameters."""

    info_ex: KvmInfoEx
    state: KvmState
    ab_params: KvmAbParams
    ctrl_params: KvmCtrlParams
    relay_params: KvmRelayParams
    sys_params: KvmSysParams
    eth_params: KvmEthParams
    snmp_params: KvmSnmpParams
    adc_params: dict[int, KvmAdcParams]
    log_record: KvmLogRecord | None = None
    test_ab_record: KvmTestAbRecord | None = None


class EzhuKvmDataUpdateCoordinator(DataUpdateCoordinator[EzhuKvmSnapshot]):
    """Coordinator managing polling and serialized TCP WAKE commands to the KVM48-20."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: EzhuKvmClient,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=f"{DOMAIN}_{client.host}",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self._io_lock = asyncio.Lock()
        self._cycle_count = 0
        self._force_config_refresh = True

    async def _async_update_data(self) -> EzhuKvmSnapshot:
        """Fetch live telemetry on every poll, and full configuration periodically."""
        include_config = (
            self.data is None
            or self._force_config_refresh
            or (self._cycle_count % DEFAULT_CONFIG_REFRESH_CYCLES == 0)
        )
        async with self._io_lock:
            try:
                raw = await self.hass.async_add_executor_job(
                    self.client.fetch_snapshot, include_config
                )
            except EzhuKvmError as err:
                raise UpdateFailed(f"Error communicating with EZHU KVM48: {err}") from err

        self._cycle_count += 1
        self._force_config_refresh = False

        if include_config or self.data is None:
            return EzhuKvmSnapshot(
                info_ex=raw["info_ex"],
                state=raw["state"],
                ab_params=raw["ab_params"],
                ctrl_params=raw["ctrl_params"],
                relay_params=raw["relay_params"],
                sys_params=raw["sys_params"],
                eth_params=raw["eth_params"],
                snmp_params=raw["snmp_params"],
                adc_params=raw["adc_params"],
                log_record=raw.get("log_record"),
                test_ab_record=raw.get("test_ab_record"),
            )

        return replace(self.data, state=raw["state"])

    async def _async_execute_write(
        self, func: Callable[..., Any], *args: Any, refresh_config: bool = True
    ) -> Any:
        """Execute a serialized write command and refresh coordinator state."""
        async with self._io_lock:
            try:
                res = await self.hass.async_add_executor_job(func, *args)
            except (EzhuKvmError, ValueError) as err:
                raise HomeAssistantError(f"EZHU KVM48 command failed: {err}") from err
        if refresh_config:
            self._force_config_refresh = True
        await self.async_request_refresh()
        return res

    async def async_force_full_refresh(self) -> None:
        """Force a full refresh of all live and configuration parameters."""
        self._force_config_refresh = True
        await self.async_request_refresh()

    async def async_update_ab_params(self, **changes: Any) -> None:
        """Update one or more fields of TABParams and write to controller flash."""
        updated = replace(self.data.ab_params, **changes)
        await self._async_execute_write(self.client.set_ab_params, updated)

    async def async_update_ctrl_params(self, **changes: Any) -> None:
        """Update one or more fields of TCtrlParams and write to controller flash."""
        updated = replace(self.data.ctrl_params, **changes)
        await self._async_execute_write(self.client.set_ctrl_params, updated)

    async def async_update_relay_flag(
        self, group_idx: int, alarm_idx: int, enabled: bool
    ) -> None:
        """Update a single (group_idx, alarm_idx) flag in TRelayConfiguration and save."""
        updated = self.data.relay_params.with_flag(group_idx, alarm_idx, enabled)
        await self._async_execute_write(self.client.set_relay_params, updated)

    async def async_update_sys_params(self, **changes: Any) -> None:
        """Update one or more fields of TSysParams and write to controller flash."""
        updated = replace(self.data.sys_params, **changes)
        await self._async_execute_write(self.client.set_sys_params, updated)

    async def async_update_eth_params(self, **changes: Any) -> None:
        """Update one or more fields of TEthParams and write to controller flash."""
        updated = replace(self.data.eth_params, **changes)
        await self._async_execute_write(self.client.set_eth_params, updated)

    async def async_update_snmp_params(self, **changes: Any) -> None:
        """Update one or more fields of TSNMPParams and write to controller flash."""
        updated = replace(self.data.snmp_params, **changes)
        await self._async_execute_write(self.client.set_snmp_params, updated)

    async def async_update_adc_params(self, channel: int, **changes: Any) -> None:
        """Update one or more fields of TADCParams[channel] and write to controller flash."""
        current = self.data.adc_params[channel]
        updated = replace(current, **changes)
        await self._async_execute_write(self.client.set_adc_params, updated)

    async def async_set_sys_location(self, location: str) -> None:
        """0x1E SetSysLocation: Update 32-byte system location string."""
        await self._async_execute_write(self.client.set_sys_location, location)

    async def async_update_sys_info(self, **changes: str) -> None:
        """0x1F SetSysInfo: Update HardwareID, DevName, SerialNumber, or Customer."""
        info = self.data.info_ex
        hw_id = changes.get("hardware_id", info.hardware_id)
        dev_name = changes.get("dev_name", info.dev_name)
        serial_num = changes.get("serial_number", info.serial_number)
        customer = changes.get("customer", info.customer)

        def _write() -> None:
            self.client.set_sys_info(
                hardware_id=hw_id,
                dev_name=dev_name,
                serial_number=serial_num,
                customer=customer,
            )

        await self._async_execute_write(_write)

    async def async_set_test_state(self, active: bool) -> None:
        """0x19 SetTestState: Start or stop battery discharge test."""
        await self._async_execute_write(
            self.client.set_test_state, active, refresh_config=False
        )

    async def async_sync_datetime(self, dt: datetime | None = None) -> None:
        """0x06 SetDateTime: Synchronize controller RTC to Home Assistant clock."""
        await self._async_execute_write(
            self.client.set_datetime, dt or datetime.now(), refresh_config=False
        )

    async def async_clear_log(self) -> None:
        """0x16 ClearLog: Clear telemetry archive log."""
        await self._async_execute_write(self.client.clear_log)

    async def async_clear_test_ab_record(self) -> None:
        """0x18 ClearTestABRecord: Clear battery test archive log."""
        await self._async_execute_write(self.client.clear_test_ab_record)

    async def async_send_snmp_trap(self, trap_code: int = 0, param: int = 0) -> None:
        """0x1D SendSNMPTrap: Send test SNMP trap."""
        await self._async_execute_write(
            self.client.send_snmp_trap, trap_code, param, refresh_config=False
        )

    async def async_reset_device(self) -> None:
        """0x1B ResetDevice: Reboot controller."""
        await self._async_execute_write(self.client.reset_device, refresh_config=True)

    async def async_set_factory_defaults(self) -> None:
        """0x1A SetFactoryDefaults: Restore controller parameters to factory defaults."""
        await self._async_execute_write(
            self.client.set_factory_defaults, refresh_config=True
        )
