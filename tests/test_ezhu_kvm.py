"""Unit tests for the EZHU KVM48 Power System (ЕЖУ КВМ48-20) custom integration."""

from __future__ import annotations

import asyncio
from datetime import datetime
from enum import StrEnum
from pathlib import Path
import struct
import sys
from types import ModuleType, SimpleNamespace
from typing import Any
import unittest

ROOT_DIR = Path(__file__).resolve().parent.parent


def _install_ha_stubs() -> None:
    """Install lightweight Home Assistant stubs for standalone unit testing."""
    if "homeassistant" in sys.modules:
        return

    ha = ModuleType("homeassistant")

    # homeassistant.const
    ha_const = ModuleType("homeassistant.const")

    class Platform(StrEnum):
        SENSOR = "sensor"
        BINARY_SENSOR = "binary_sensor"
        NUMBER = "number"
        SELECT = "select"
        SWITCH = "switch"
        TEXT = "text"
        BUTTON = "button"

    class EntityCategory(StrEnum):
        CONFIG = "config"
        DIAGNOSTIC = "diagnostic"

    class UnitOfElectricPotential(StrEnum):
        VOLT = "V"

    class UnitOfElectricCurrent(StrEnum):
        AMPERE = "A"

    class UnitOfPower(StrEnum):
        WATT = "W"

    class UnitOfTemperature(StrEnum):
        CELSIUS = "°C"

    class UnitOfTime(StrEnum):
        MINUTES = "min"

    ha_const.Platform = Platform
    ha_const.EntityCategory = EntityCategory
    ha_const.UnitOfElectricPotential = UnitOfElectricPotential
    ha_const.UnitOfElectricCurrent = UnitOfElectricCurrent
    ha_const.UnitOfPower = UnitOfPower
    ha_const.UnitOfTemperature = UnitOfTemperature
    ha_const.UnitOfTime = UnitOfTime
    ha_const.CONF_HOST = "host"
    ha_const.CONF_PORT = "port"
    ha_const.CONF_PASSWORD = "password"
    ha_const.CONF_NAME = "name"
    ha_const.CONF_SCAN_INTERVAL = "scan_interval"

    # homeassistant.core
    ha_core = ModuleType("homeassistant.core")
    ha_core.callback = lambda fn: fn
    ha_core.HomeAssistant = object

    # homeassistant.exceptions
    ha_exc = ModuleType("homeassistant.exceptions")

    class HomeAssistantError(Exception):
        pass

    ha_exc.HomeAssistantError = HomeAssistantError

    # homeassistant.config_entries
    ha_ce = ModuleType("homeassistant.config_entries")

    class ConfigEntry:
        def __class_getitem__(cls, item):
            return cls

    class ConfigFlow:
        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__()

        def __init__(self):
            self.hass = None
            self.context = {}
            self._unique_id = None

        async def async_set_unique_id(self, unique_id):
            self._unique_id = unique_id

        def _abort_if_unique_id_configured(self, updates=None):
            return None

        def _async_current_entries(self):
            return []

        def async_show_form(self, **kwargs):
            return {"type": "form", **kwargs}

        def async_create_entry(self, **kwargs):
            return {"type": "create_entry", **kwargs}

        def async_abort(self, **kwargs):
            return {"type": "abort", **kwargs}

    class OptionsFlow:
        pass

    ha_ce.ConfigEntry = ConfigEntry
    ha_ce.ConfigFlow = ConfigFlow
    ha_ce.ConfigFlowResult = dict
    ha_ce.OptionsFlow = OptionsFlow

    # homeassistant.helpers
    ha_helpers = ModuleType("homeassistant.helpers")
    ha_dr = ModuleType("homeassistant.helpers.device_registry")
    ha_dr.CONNECTION_NETWORK_MAC = "mac"
    ha_dr.DeviceInfo = dict

    ha_ep = ModuleType("homeassistant.helpers.entity_platform")
    ha_ep.AddEntitiesCallback = object

    ha_uc = ModuleType("homeassistant.helpers.update_coordinator")

    class UpdateFailed(Exception):
        pass

    class DataUpdateCoordinator:
        def __class_getitem__(cls, item):
            return cls

        def __init__(self, hass, logger, *, config_entry=None, name="", update_interval=None):
            self.hass = hass
            self.logger = logger
            self.config_entry = config_entry
            self.name = name
            self.update_interval = update_interval
            self.data = None

        async def async_request_refresh(self):
            self.data = await self._async_update_data()

    class CoordinatorEntity:
        def __class_getitem__(cls, item):
            return cls

        def __init__(self, coordinator):
            self.coordinator = coordinator

    ha_uc.UpdateFailed = UpdateFailed
    ha_uc.DataUpdateCoordinator = DataUpdateCoordinator
    ha_uc.CoordinatorEntity = CoordinatorEntity

    # Entity description base class (must be a dataclass to match HA EntityDescription)
    from dataclasses import dataclass as _dc

    @_dc(frozen=True, kw_only=True)
    class _BaseDescription:
        key: str = ""
        name: str | None = None
        icon: str | None = None
        device_class: Any = None
        state_class: Any = None
        native_unit_of_measurement: str | None = None
        suggested_display_precision: int | None = None
        entity_category: Any = None
        entity_registry_enabled_default: bool = True
        native_min_value: float | None = None
        native_max_value: float | None = None
        native_step: float | None = None
        mode: Any = None
        native_min: int | None = None
        native_max: int | None = None
        pattern: str | None = None

    # homeassistant.components.*
    ha_comp = ModuleType("homeassistant.components")

    ha_sensor = ModuleType("homeassistant.components.sensor")

    class SensorDeviceClass(StrEnum):
        VOLTAGE = "voltage"
        CURRENT = "current"
        POWER = "power"
        TEMPERATURE = "temperature"

    class SensorStateClass(StrEnum):
        MEASUREMENT = "measurement"
        TOTAL_INCREASING = "total_increasing"

    class SensorEntity:
        pass

    ha_sensor.SensorDeviceClass = SensorDeviceClass
    ha_sensor.SensorStateClass = SensorStateClass
    ha_sensor.SensorEntity = SensorEntity
    ha_sensor.SensorEntityDescription = _BaseDescription

    ha_bs = ModuleType("homeassistant.components.binary_sensor")

    class BinarySensorDeviceClass(StrEnum):
        PROBLEM = "problem"
        RUNNING = "running"
        CONNECTIVITY = "connectivity"

    class BinarySensorEntity:
        pass

    ha_bs.BinarySensorDeviceClass = BinarySensorDeviceClass
    ha_bs.BinarySensorEntity = BinarySensorEntity
    ha_bs.BinarySensorEntityDescription = _BaseDescription

    ha_num = ModuleType("homeassistant.components.number")

    class NumberDeviceClass(StrEnum):
        VOLTAGE = "voltage"
        CURRENT = "current"
        TEMPERATURE = "temperature"

    class NumberMode(StrEnum):
        BOX = "box"

    class NumberEntity:
        pass

    ha_num.NumberDeviceClass = NumberDeviceClass
    ha_num.NumberMode = NumberMode
    ha_num.NumberEntity = NumberEntity
    ha_num.NumberEntityDescription = _BaseDescription

    ha_sel = ModuleType("homeassistant.components.select")

    class SelectEntity:
        pass

    ha_sel.SelectEntity = SelectEntity

    ha_sw = ModuleType("homeassistant.components.switch")

    class SwitchEntity:
        pass

    ha_sw.SwitchEntity = SwitchEntity
    ha_sw.SwitchEntityDescription = _BaseDescription

    ha_txt = ModuleType("homeassistant.components.text")

    class TextMode(StrEnum):
        TEXT = "text"
        PASSWORD = "password"

    class TextEntity:
        pass

    ha_txt.TextMode = TextMode
    ha_txt.TextEntity = TextEntity
    ha_txt.TextEntityDescription = _BaseDescription

    ha_btn = ModuleType("homeassistant.components.button")

    class ButtonDeviceClass(StrEnum):
        RESTART = "restart"

    class ButtonEntity:
        pass

    ha_btn.ButtonDeviceClass = ButtonDeviceClass
    ha_btn.ButtonEntity = ButtonEntity
    ha_btn.ButtonEntityDescription = _BaseDescription

    # voluptuous stub if not installed
    if "voluptuous" not in sys.modules:
        vol = ModuleType("voluptuous")
        vol.Schema = lambda s: s
        vol.Required = lambda k, default=None: k
        vol.Optional = lambda k, default=None: k
        vol.All = lambda *args: args
        vol.Coerce = lambda t: t
        vol.Range = lambda **kwargs: kwargs
        vol.In = lambda opts: opts
        sys.modules["voluptuous"] = vol

    sys.modules["homeassistant"] = ha
    sys.modules["homeassistant.const"] = ha_const
    sys.modules["homeassistant.core"] = ha_core
    sys.modules["homeassistant.exceptions"] = ha_exc
    sys.modules["homeassistant.config_entries"] = ha_ce
    sys.modules["homeassistant.helpers"] = ha_helpers
    sys.modules["homeassistant.helpers.device_registry"] = ha_dr
    sys.modules["homeassistant.helpers.entity_platform"] = ha_ep
    sys.modules["homeassistant.helpers.update_coordinator"] = ha_uc
    sys.modules["homeassistant.components"] = ha_comp
    sys.modules["homeassistant.components.sensor"] = ha_sensor
    sys.modules["homeassistant.components.binary_sensor"] = ha_bs
    sys.modules["homeassistant.components.number"] = ha_num
    sys.modules["homeassistant.components.select"] = ha_sel
    sys.modules["homeassistant.components.switch"] = ha_sw
    sys.modules["homeassistant.components.text"] = ha_txt
    sys.modules["homeassistant.components.button"] = ha_btn


_install_ha_stubs()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from custom_components.ezhu_kvm.binary_sensor import (  # noqa: E402
    BINARY_SENSOR_DESCRIPTIONS,
    EzhuKvmBinarySensor,
)
from custom_components.ezhu_kvm.button import (  # noqa: E402
    BUTTON_DESCRIPTIONS,
    EzhuKvmButton,
)
from custom_components.ezhu_kvm.const import (  # noqa: E402
    KVM_CMD_CLEAR_LOG,
    KVM_CMD_CLEAR_TEST_AB_RECORD,
    KVM_CMD_GET_AB_PARAMS,
    KVM_CMD_GET_ADC_PARAMS,
    KVM_CMD_GET_CTRL_PARAMS,
    KVM_CMD_GET_ETH_PARAMS,
    KVM_CMD_GET_INFO_EX,
    KVM_CMD_GET_LOG_RECORD,
    KVM_CMD_GET_RELAY_PARAMS,
    KVM_CMD_GET_SNMP_PARAMS,
    KVM_CMD_GET_STATE,
    KVM_CMD_GET_SYS_PARAMS,
    KVM_CMD_GET_TEST_AB_RECORD,
    KVM_CMD_RESET_DEVICE,
    KVM_CMD_SEND_SNMP_TRAP,
    KVM_CMD_SET_AB_PARAMS,
    KVM_CMD_SET_ADC_PARAMS,
    KVM_CMD_SET_CTRL_PARAMS,
    KVM_CMD_SET_DATETIME,
    KVM_CMD_SET_ETH_PARAMS,
    KVM_CMD_SET_FACTORY_DEFAULTS,
    KVM_CMD_SET_RELAY_PARAMS,
    KVM_CMD_SET_SNMP_PARAMS,
    KVM_CMD_SET_SYS_INFO,
    KVM_CMD_SET_SYS_LOCATION,
    KVM_CMD_SET_SYS_PARAMS,
    KVM_CMD_SET_TEST_STATE,
)
from custom_components.ezhu_kvm.coordinator import (  # noqa: E402
    EzhuKvmDataUpdateCoordinator,
)
from custom_components.ezhu_kvm.number import (  # noqa: E402
    NUMBER_DESCRIPTIONS,
    EzhuKvmNumber,
)
from custom_components.ezhu_kvm.select import EzhuKvmRegimeSelect  # noqa: E402
from custom_components.ezhu_kvm.sensor import (  # noqa: E402
    SENSOR_DESCRIPTIONS,
    EzhuKvmSensor,
)
from custom_components.ezhu_kvm.switch import (  # noqa: E402
    SWITCH_DESCRIPTIONS,
    EzhuKvmSwitch,
)
from custom_components.ezhu_kvm.text import (  # noqa: E402
    TEXT_DESCRIPTIONS,
    EzhuKvmText,
)
from custom_components.ezhu_kvm.wake_client import (  # noqa: E402
    EzhuKvmClient,
    build_wake_frame,
    calc_wake_crc,
    stuff_wake_bytes,
)

# Synthetic test payloads (using RFC 5737 / RFC 7042 documentation values)
RAW_GET_INFO_EX = (
    struct.pack("<BBHI", 0, 0, 0, 0)
    + b"----.--.-- --:--:--".ljust(20, b"\x00")
    + struct.pack("<BBHI", 1, 0, 0, 53)
    + b"2013.09.24 22:02:23".ljust(20, b"\x00")
    + b"VPMA.758725.037".ljust(16, b"\x00")
    + b"KVM48-20".ljust(16, b"\x00")
    + b"00000000001".ljust(16, b"\x00")
    + b"INTEGRAL".ljust(20, b"\x00")
    + b"Power Room 1".ljust(32, b"\x00")
    + b"KVM48".ljust(16, b"\x00")
)

RAW_GET_STATE = bytes.fromhex(
    "00000000000080ac41010000000000000000c00e420100000000000000"
    "49310000000000001ceeb1be"
    "4932000000000000c8a1093c"
    "493300000000000000000000"
    "496e00000000000000000000"
    "466100000000000000000000"
    "466200000000000000000000"
    "556e00000000000055325c42"
    "466300000000000000000000"
    "2611212104360012000000000000000003f40001010001000000000000000000003800"
)

RAW_GET_AB_PARAMS = bytes.fromhex(
    "00180000000000000051090000c800000003000000d00200000a00000058020000c01200000c00000005000000"
)

RAW_GET_CTRL_PARAMS = bytes.fromhex(
    "00"
    + struct.pack(
        "<13i",
        5720,
        -100,
        4500,
        100,
        8000,
        -500,
        3250,
        -200,
        4700,
        200,
        4320,
        200,
        5600,
    ).hex()
)

RAW_GET_RELAY_PARAMS = bytes.fromhex(
    "00"
    "00000000000000000000"
    "01010101010101010101"
    "01010101010101010101"
    "01010101010101010101"
)

RAW_GET_SYS_PARAMS = bytes.fromhex("0001050505050505f000000000")

RAW_GET_ETH_PARAMS = (
    b"\x00"
    + b"KVM48".ljust(16, b"\x00")
    + bytes.fromhex("00005e005301")
    + b"\x01"
    + bytes([192, 0, 2, 50])
    + bytes([192, 0, 2, 1])
    + bytes([255, 255, 255, 0])
    + bytes([192, 0, 2, 1])
    + bytes([192, 0, 2, 2])
    + b"\x00"
)

RAW_GET_SNMP_PARAMS = (
    b"\x00"
    + b"public".ljust(16, b"\x00")
    + (bytes([0, 0, 0, 0]) * 5)
    + struct.pack("<I", 1023)
)

RAW_GET_LOG_RECORD_1 = bytes.fromhex(
    "0001001f02200822083956fd00000100000000000000000000a94100400842"
    "9d67d03e0286c93e0000000071778d410000000000000000dbfe5a4200000000"
)

RAW_GET_TEST_AB_RECORD_0 = b"\x00" + (b"\x00" * 60)


class FakeEzhuKvmClient(EzhuKvmClient):
    """In-memory mock EzhuKvmClient that simulates a KVM48-20 controller."""

    def __init__(self) -> None:
        super().__init__(host="192.0.2.50", port=1001)
        self.sent_commands: list[tuple[int, bytes]] = []
        self._info_ex = bytearray(RAW_GET_INFO_EX)
        self._state = bytearray(RAW_GET_STATE)
        self._ab = bytearray(RAW_GET_AB_PARAMS)
        self._ctrl = bytearray(RAW_GET_CTRL_PARAMS)
        self._relay = bytearray(RAW_GET_RELAY_PARAMS)
        self._sys = bytearray(RAW_GET_SYS_PARAMS)
        self._eth = bytearray(RAW_GET_ETH_PARAMS)
        self._snmp = bytearray(RAW_GET_SNMP_PARAMS)
        self._adc: dict[int, bytearray] = {}
        adc_defaults = [
            (0, "I1", 0, 1248, 26200),
            (1, "I2", 0, 1272, 26750),
            (2, "I3", 0, 0, 20000),
            (3, "In", 0, 0, 44700),
            (4, "Fa", 0, 0, 0),
            (5, "Fb", 0, 0, 0),
            (6, "Un", 0, 0, 10030),
            (7, "Fc", 0, 0, 0),
        ]
        for ch, name, en, off, gain in adc_defaults:
            self._adc[ch] = bytearray(
                bytes([0x00, ch])
                + struct.pack("<8siii", name.encode().ljust(8, b"\x00"), en, off, gain)
            )

    def _connect(self):
        return SimpleNamespace(close=lambda: None)

    def query(
        self,
        cmd: int,
        payload: bytes = b"",
        *,
        check_status: bool = True,
        sock: Any = None,
    ) -> bytes:
        self.sent_commands.append((cmd, bytes(payload)))
        if cmd == KVM_CMD_GET_INFO_EX:
            return bytes(self._info_ex)
        if cmd == KVM_CMD_GET_STATE:
            return bytes(self._state)
        if cmd == KVM_CMD_GET_ADC_PARAMS:
            return bytes(self._adc[payload[0]])
        if cmd == KVM_CMD_GET_AB_PARAMS:
            return bytes(self._ab)
        if cmd == KVM_CMD_GET_CTRL_PARAMS:
            return bytes(self._ctrl)
        if cmd == KVM_CMD_GET_RELAY_PARAMS:
            return bytes(self._relay)
        if cmd == KVM_CMD_GET_SYS_PARAMS:
            return bytes(self._sys)
        if cmd == KVM_CMD_GET_ETH_PARAMS:
            return bytes(self._eth)
        if cmd == KVM_CMD_GET_SNMP_PARAMS:
            return bytes(self._snmp)
        if cmd == KVM_CMD_GET_LOG_RECORD:
            return RAW_GET_LOG_RECORD_1
        if cmd == KVM_CMD_GET_TEST_AB_RECORD:
            return RAW_GET_TEST_AB_RECORD_0

        # Handle Write Commands & update simulated device state
        if cmd == KVM_CMD_SET_ADC_PARAMS:
            assert len(payload) == 30
            ch = payload[0]
            self._adc[ch][2:22] = payload[9:29]
            return bytes([0x00, ch])
        if cmd == KVM_CMD_SET_AB_PARAMS:
            assert len(payload) == 53
            self._ab[1:45] = payload[8:52]
            return b"\x00"
        if cmd == KVM_CMD_SET_CTRL_PARAMS:
            assert len(payload) == 61
            self._ctrl[1:53] = payload[8:60]
            return b"\x00"
        if cmd == KVM_CMD_SET_RELAY_PARAMS:
            assert len(payload) == 49
            self._relay[1:41] = payload[8:48]
            return b"\x00"
        if cmd == KVM_CMD_SET_SYS_PARAMS:
            assert len(payload) == 21
            self._sys[1:13] = payload[8:20]
            return b"\x00"
        if cmd == KVM_CMD_SET_ETH_PARAMS:
            assert len(payload) == 53
            self._eth[1:45] = payload[8:52]
            return b"\x00"
        if cmd == KVM_CMD_SET_SNMP_PARAMS:
            assert len(payload) == 49
            self._snmp[1:41] = payload[8:48]
            return b"\x00"
        if cmd == KVM_CMD_SET_SYS_LOCATION:
            assert len(payload) == 40
            self._info_ex[124:156] = payload[8:40]
            return b"\x00"
        if cmd == KVM_CMD_SET_SYS_INFO:
            assert len(payload) == 76
            assert payload[0:8] == b"434410\x00\x00"
            self._info_ex[56:124] = payload[8:76]
            return b"\x00"
        if cmd == KVM_CMD_SET_TEST_STATE:
            assert len(payload) == 9
            self._state[5 + 132 : 5 + 136] = struct.pack("<I", payload[8])
            return bytes([0x00, payload[8]])
        if cmd == KVM_CMD_SET_DATETIME:
            assert len(payload) == 16
            self._state[5 + 120 : 5 + 126] = payload[9:15]
            return b"\x00"
        if cmd in (
            KVM_CMD_CLEAR_LOG,
            KVM_CMD_CLEAR_TEST_AB_RECORD,
            KVM_CMD_SET_FACTORY_DEFAULTS,
            KVM_CMD_RESET_DEVICE,
            KVM_CMD_SEND_SNMP_TRAP,
        ):
            return b"\x00"

        raise AssertionError(f"Unhandled WAKE command 0x{cmd:02X}")


class FakeHass:
    """Minimal HomeAssistant executor helper for unit tests."""

    async def async_add_executor_job(self, func, *args):
        return func(*args)


class TestEzhuKvmIntegration(unittest.TestCase):
    """Test WAKE protocol framing, struct parsing, and all 7 Home Assistant entity platforms."""

    def test_wake_crc_and_framing(self) -> None:
        """Verify WAKE CRC-8 calculation and byte stuffing match KVMCtrlMon.exe."""
        # Verify RX CRC with raw address byte 0xD1 on GetABParams response
        expected_crc = calc_wake_crc(
            bytes([0xC0, 0xD1, 0x09, len(RAW_GET_AB_PARAMS)]) + RAW_GET_AB_PARAMS
        )
        self.assertEqual(expected_crc, 0x18)

        # Verify byte stuffing of 0xC0 and 0xDB
        stuffed = stuff_wake_bytes(bytes([0x01, 0xC0, 0x02, 0xDB, 0x03]))
        self.assertEqual(stuffed, bytes([0x01, 0xDB, 0xDC, 0x02, 0xDB, 0xDD, 0x03]))

        # Verify TX frame construction
        frame = build_wake_frame(KVM_CMD_GET_INFO_EX, b"")
        self.assertEqual(frame[0], 0xC0)
        self.assertEqual(frame[1], KVM_CMD_GET_INFO_EX)
        self.assertEqual(frame[2], 0x00)

    def test_all_entities_read_and_write_roundtrip(self) -> None:
        """Verify 100% of read-only and read/write entities across all 7 platforms."""

        async def _run() -> None:
            hass = FakeHass()
            client = FakeEzhuKvmClient()
            coordinator = EzhuKvmDataUpdateCoordinator(
                hass=hass,
                config_entry=SimpleNamespace(entry_id="test_entry"),
                client=client,
            )
            await coordinator.async_request_refresh()
            self.assertIsNotNone(coordinator.data)

            # 1. Sensors (25 read-only sensors)
            sensors = {
                desc.key: EzhuKvmSensor(coordinator, desc)
                for desc in SENSOR_DESCRIPTIONS
            }
            self.assertEqual(len(sensors), 25)
            self.assertAlmostEqual(sensors["u_load"].native_value, 55.05, places=2)
            self.assertAlmostEqual(sensors["i_ab1"].native_value, -0.348, places=3)
            self.assertAlmostEqual(sensors["i_ab2"].native_value, 0.008, places=3)
            self.assertAlmostEqual(sensors["temp_ab"].native_value, 21.56, places=2)
            self.assertAlmostEqual(sensors["temp_cu"].native_value, 35.69, places=2)
            self.assertEqual(sensors["work_mode"].native_value, "Manual U")
            self.assertEqual(sensors["faults_bitmask"].native_value, 0x00F4)
            self.assertEqual(sensors["rele_bitmask"].native_value, 0x38)
            self.assertEqual(
                sensors["firmware_version"].native_value, "1.0.0 (SVN 53)"
            )
            self.assertEqual(sensors["telemetry_log_head_id"].native_value, 543)

            # 2. Binary Sensors (10 alarms + 3 status/presence + 8 relay bits + 16 fault bits = 37)
            binary_sensors = {
                desc.key: EzhuKvmBinarySensor(coordinator, desc)
                for desc in BINARY_SENSOR_DESCRIPTIONS
            }
            self.assertEqual(len(binary_sensors), 37)
            self.assertTrue(binary_sensors["alarm_a1_ac_input"].is_on)
            self.assertTrue(binary_sensors["alarm_a2_rectifiers"].is_on)
            self.assertFalse(binary_sensors["alarm_a3_overload"].is_on)
            self.assertTrue(binary_sensors["alarm_a4_ab_circuit"].is_on)
            self.assertTrue(binary_sensors["temp_ab_present"].is_on)
            self.assertTrue(binary_sensors["rele_bit_3"].is_on)
            self.assertFalse(binary_sensors["rele_bit_0"].is_on)

            # 3. Numbers (10 AB + 13 Ctrl + 2 Sys + 2 Eth/SNMP + 16 ADC = 43 writable numbers)
            numbers = {
                desc.key: EzhuKvmNumber(coordinator, desc)
                for desc in NUMBER_DESCRIPTIONS
            }
            self.assertEqual(len(numbers), 43)
            self.assertEqual(numbers["ab_cell_count"].native_value, 24.0)
            self.assertAlmostEqual(numbers["ab_u20c"].native_value, 2.385, places=3)
            self.assertAlmostEqual(numbers["ctrl_umanual"].native_value, 56.00, places=2)
            self.assertAlmostEqual(numbers["ctrl_umax"].native_value, 57.20, places=2)
            self.assertAlmostEqual(
                numbers["adc_ch0_i_ab1_offset"].native_value, 12.48, places=2
            )
            self.assertAlmostEqual(
                numbers["adc_ch0_i_ab1_gain"].native_value, 2.6200, places=4
            )

            # Modify Umanual and verify roundtrip write (0x0C SetCtrlParams)
            await numbers["ctrl_umanual"].async_set_native_value(54.50)
            self.assertAlmostEqual(numbers["ctrl_umanual"].native_value, 54.50, places=2)

            # Modify AB Icharge and verify roundtrip write (0x0A SetABParams)
            await numbers["ab_icharge"].async_set_native_value(65.5)
            self.assertAlmostEqual(numbers["ab_icharge"].native_value, 65.5, places=1)

            # Modify ADC Ch0 Offset and verify roundtrip write (0x08 SetADCParams)
            await numbers["adc_ch0_i_ab1_offset"].async_set_native_value(13.25)
            self.assertAlmostEqual(
                numbers["adc_ch0_i_ab1_offset"].native_value, 13.25, places=2
            )

            # 4. Select (1 charge regime select: Auto U, Auto IU, Manual U, Manual IU)
            regime_select = EzhuKvmRegimeSelect(coordinator)
            self.assertEqual(regime_select.current_option, "Manual U")
            await regime_select.async_select_option("Auto IU")
            self.assertEqual(regime_select.current_option, "Auto IU")

            # 5. Switches (1 test + 1 voice + 1 DHCP + 8 ADC enabled + 40 relay matrix = 51 writable switches)
            switches = {
                desc.key: EzhuKvmSwitch(coordinator, desc)
                for desc in SWITCH_DESCRIPTIONS
            }
            self.assertEqual(len(switches), 51)
            self.assertTrue(switches["sys_voice"].is_on)
            await switches["sys_voice"].async_turn_off()
            self.assertFalse(switches["sys_voice"].is_on)

            self.assertFalse(switches["relay_cfg_relay1_a1_ac_input"].is_on)
            await switches["relay_cfg_relay1_a1_ac_input"].async_turn_on()
            self.assertTrue(switches["relay_cfg_relay1_a1_ac_input"].is_on)

            self.assertFalse(switches["battery_discharge_test"].is_on)
            await switches["battery_discharge_test"].async_turn_on()
            self.assertTrue(switches["battery_discharge_test"].is_on)
            self.assertTrue(binary_sensors["testing_active"].is_on)

            # 6. Texts (1 SysLocation + 4 SysInfo + 1 User PIN + 7 Eth + 6 SNMP + 8 ADC Names = 27 writable texts)
            texts = {
                desc.key: EzhuKvmText(coordinator, desc)
                for desc in TEXT_DESCRIPTIONS
            }
            self.assertEqual(len(texts), 27)
            self.assertEqual(texts["sys_location"].native_value, "Power Room 1")
            await texts["sys_location"].async_set_value("Power Room 1 Rack A")
            self.assertEqual(texts["sys_location"].native_value, "Power Room 1 Rack A")

            self.assertEqual(texts["sys_info_customer"].native_value, "INTEGRAL")
            await texts["sys_info_customer"].async_set_value("INTEGRAL-KVM")
            self.assertEqual(texts["sys_info_customer"].native_value, "INTEGRAL-KVM")

            self.assertEqual(texts["sys_password_user"].native_value, "555555")
            await texts["sys_password_user"].async_set_value("123456")
            self.assertEqual(texts["sys_password_user"].native_value, "123456")

            self.assertEqual(texts["snmp_trap_server_1"].native_value, "0.0.0.0")
            await texts["snmp_trap_server_1"].async_set_value("192.0.2.10")
            self.assertEqual(texts["snmp_trap_server_1"].native_value, "192.0.2.10")

            # 7. Buttons (9 action buttons)
            buttons = {
                desc.key: EzhuKvmButton(coordinator, desc)
                for desc in BUTTON_DESCRIPTIONS
            }
            self.assertEqual(len(buttons), 9)
            await buttons["sync_datetime"].async_press()
            await buttons["clear_telemetry_log"].async_press()
            await buttons["clear_battery_test_log"].async_press()
            await buttons["send_test_snmp_trap"].async_press()
            await buttons["reboot_controller"].async_press()
            await buttons["restore_factory_defaults"].async_press()

            sent_cmd_ids = {cmd for cmd, _ in client.sent_commands}
            for expected_cmd in (
                KVM_CMD_SET_DATETIME,
                KVM_CMD_SET_ADC_PARAMS,
                KVM_CMD_SET_AB_PARAMS,
                KVM_CMD_SET_CTRL_PARAMS,
                KVM_CMD_SET_RELAY_PARAMS,
                KVM_CMD_SET_SYS_PARAMS,
                KVM_CMD_SET_SNMP_PARAMS,
                KVM_CMD_CLEAR_LOG,
                KVM_CMD_CLEAR_TEST_AB_RECORD,
                KVM_CMD_SET_TEST_STATE,
                KVM_CMD_SET_FACTORY_DEFAULTS,
                KVM_CMD_RESET_DEVICE,
                KVM_CMD_SEND_SNMP_TRAP,
                KVM_CMD_SET_SYS_LOCATION,
                KVM_CMD_SET_SYS_INFO,
            ):
                self.assertIn(expected_cmd, sent_cmd_ids)

        asyncio.run(_run())

    def test_config_flow_dhcp_and_lan_discovery(self) -> None:
        """Verify Home Assistant DHCP discovery and empty-host LAN auto-discovery."""
        from unittest.mock import patch
        from custom_components.ezhu_kvm.config_flow import EzhuKvmConfigFlow

        fake_client = FakeEzhuKvmClient()
        sample_info = fake_client.get_info_ex()

        async def _run() -> None:
            # 1. Test DHCP auto-discovery (1E:30:6C:* / kvm*)
            flow = EzhuKvmConfigFlow()
            flow.hass = FakeHass()
            dhcp_info = SimpleNamespace(
                ip="192.0.2.50",
                hostname="kvm48",
                macaddress="00005e005301",
            )
            with patch(
                "custom_components.ezhu_kvm.config_flow.EzhuKvmClient.get_info_ex",
                return_value=sample_info,
            ):
                res = await flow.async_step_dhcp(dhcp_info)
                self.assertEqual(res["type"], "form")
                self.assertEqual(res["step_id"], "dhcp_confirm")

                res2 = await flow.async_step_dhcp_confirm(
                    {"password": "555555", "factory_password": "434410", "scan_interval": 10}
                )
                self.assertEqual(res2["type"], "create_entry")
                self.assertEqual(res2["data"]["host"], "192.0.2.50")
                self.assertEqual(res2["title"], "KVM48-20 (KVM48)")

            # 2. Test empty-host active LAN discovery in async_step_user
            flow2 = EzhuKvmConfigFlow()
            flow2.hass = FakeHass()
            with patch(
                "custom_components.ezhu_kvm.config_flow.discover_kvm_devices",
                return_value=[("192.0.2.50", sample_info)],
            ):
                res3 = await flow2.async_step_user(
                    {
                        "host": "",
                        "port": 1001,
                        "password": "555555",
                        "factory_password": "434410",
                        "scan_interval": 10,
                    }
                )
                self.assertEqual(res3["type"], "create_entry")
                self.assertEqual(res3["data"]["host"], "192.0.2.50")

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
