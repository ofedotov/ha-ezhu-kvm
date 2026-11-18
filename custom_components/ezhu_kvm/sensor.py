"""Read-only sensor entities for the EZHU KVM48 Power System integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EzhuKvmConfigEntry
from .coordinator import EzhuKvmDataUpdateCoordinator, EzhuKvmSnapshot
from .entity import EzhuKvmEntity


@dataclass(frozen=True, kw_only=True)
class EzhuKvmSensorDescription(SensorEntityDescription):
    """Describe an EZHU KVM48 read-only sensor entity."""

    value_fn: Callable[[EzhuKvmSnapshot], Any]
    attr_fn: Callable[[EzhuKvmSnapshot], dict[str, Any]] | None = None


SENSOR_DESCRIPTIONS: tuple[EzhuKvmSensorDescription, ...] = (
    # --- Primary Electrical & Thermal Telemetry (0x05 GetState) ---
    EzhuKvmSensorDescription(
        key="u_load",
        name="U load (DC Bus Voltage)",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda d: d.state.u_load,
        attr_fn=lambda d: {"adc_channel": 6, "channel_label": d.state.channels[6].name},
    ),
    EzhuKvmSensorDescription(
        key="i_ab1",
        name="I ab1 (Battery 1 Current)",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda d: d.state.i_ab1,
        attr_fn=lambda d: {"adc_channel": 0, "channel_label": d.state.channels[0].name},
    ),
    EzhuKvmSensorDescription(
        key="i_ab2",
        name="I ab2 (Battery 2 Current)",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda d: d.state.i_ab2,
        attr_fn=lambda d: {"adc_channel": 1, "channel_label": d.state.channels[1].name},
    ),
    EzhuKvmSensorDescription(
        key="i_ab_total",
        name="I ab Total (Total Battery Current)",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda d: d.state.i_ab_total,
    ),
    EzhuKvmSensorDescription(
        key="i_load",
        name="I load (Load Current)",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda d: d.state.i_load,
        attr_fn=lambda d: {"adc_channel": 3, "channel_label": d.state.channels[3].name},
    ),
    EzhuKvmSensorDescription(
        key="p_load",
        name="P load (Load Power)",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d.state.p_load,
    ),
    EzhuKvmSensorDescription(
        key="i3_unused",
        name="I3 (ADC Channel 2 Current)",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.state.i3_unused,
        attr_fn=lambda d: {"adc_channel": 2, "channel_label": d.state.channels[2].name},
    ),
    EzhuKvmSensorDescription(
        key="u_ph1",
        name="U ph1 (AC Phase A Voltage)",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d.state.u_ph1,
        attr_fn=lambda d: {"adc_channel": 4, "channel_label": d.state.channels[4].name},
    ),
    EzhuKvmSensorDescription(
        key="u_ph2",
        name="U ph2 (AC Phase B Voltage)",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d.state.u_ph2,
        attr_fn=lambda d: {"adc_channel": 5, "channel_label": d.state.channels[5].name},
    ),
    EzhuKvmSensorDescription(
        key="u_ph3",
        name="U ph3 (AC Phase C Voltage)",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: d.state.u_ph3,
        attr_fn=lambda d: {"adc_channel": 7, "channel_label": d.state.channels[7].name},
    ),
    EzhuKvmSensorDescription(
        key="temp_ab",
        name="T ab (Battery Temperature)",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda d: d.state.temp_sens_value,
        attr_fn=lambda d: {
            "presence": d.state.temp_sens_presence,
            "crc_error_count": d.state.temp_sens_crc_errors,
        },
    ),
    EzhuKvmSensorDescription(
        key="temp_cu",
        name="T cu (Controller Temperature)",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda d: d.state.temp_sens_proc_value,
        attr_fn=lambda d: {
            "presence": d.state.temp_sens_proc_presence,
            "crc_error_count": d.state.temp_sens_proc_crc_errors,
        },
    ),
    # --- Live Operating State & Bitmasks (0x05 GetState) ---
    EzhuKvmSensorDescription(
        key="work_mode",
        name="Work Mode (Active)",
        icon="mdi:state-machine",
        value_fn=lambda d: d.state.work_mode_str,
        attr_fn=lambda d: {"work_mode_code": d.state.work_mode},
    ),
    EzhuKvmSensorDescription(
        key="ucontrol",
        name="Ucontrol (DAC Control Voltage)",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.state.ucontrol_v,
        attr_fn=lambda d: {"raw": d.state.ucontrol_raw},
    ),
    EzhuKvmSensorDescription(
        key="faults_bitmask",
        name="Faults Bitmask",
        icon="mdi:alert-octagon-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.state.faults,
        attr_fn=lambda d: {
            "hex": f"0x{d.state.faults:04X}",
            "binary": f"{d.state.faults:016b}",
        },
    ),
    EzhuKvmSensorDescription(
        key="rele_bitmask",
        name="Relay State Bitmask",
        icon="mdi:electric-switch",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.state.rele,
        attr_fn=lambda d: {
            "hex": f"0x{d.state.rele:02X}",
            "binary": f"{d.state.rele:08b}",
        },
    ),
    EzhuKvmSensorDescription(
        key="access_level",
        name="Access Level",
        icon="mdi:shield-account",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.state.access_level,
    ),
    EzhuKvmSensorDescription(
        key="controller_datetime",
        name="Controller Clock (RTC)",
        icon="mdi:clock-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.state.datetime_str,
        attr_fn=lambda d: {"raw_bcd": d.state.datetime_bcd.hex()},
    ),
    EzhuKvmSensorDescription(
        key="next_test_ab_datetime",
        name="Next Scheduled Battery Test",
        icon="mdi:calendar-clock",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.state.next_test_ab_str,
        attr_fn=lambda d: {"raw_bcd": d.state.next_test_ab_bcd.hex()},
    ),
    EzhuKvmSensorDescription(
        key="temp_ab_crc_errors",
        name="T ab Sensor CRC Errors",
        icon="mdi:counter",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.state.temp_sens_crc_errors,
    ),
    EzhuKvmSensorDescription(
        key="temp_cu_crc_errors",
        name="T cu Sensor CRC Errors",
        icon="mdi:counter",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.state.temp_sens_proc_crc_errors,
    ),
    # --- Read-Only Version & Archive Info (0x04, 0x15, 0x17) ---
    EzhuKvmSensorDescription(
        key="firmware_version",
        name="Firmware Version",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.info_ex.fw_version_str,
        attr_fn=lambda d: {
            "build_datetime": d.info_ex.fw_build_datetime,
            "major": d.info_ex.fw_version[0],
            "minor": d.info_ex.fw_version[1],
            "build": d.info_ex.fw_version[2],
            "svn": d.info_ex.fw_version[3],
        },
    ),
    EzhuKvmSensorDescription(
        key="bootloader_version",
        name="Bootloader Version",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.info_ex.bl_version_str,
        attr_fn=lambda d: {
            "build_datetime": d.info_ex.bl_build_datetime,
            "major": d.info_ex.bl_version[0],
            "minor": d.info_ex.bl_version[1],
            "build": d.info_ex.bl_version[2],
            "svn": d.info_ex.bl_version[3],
        },
    ),
    EzhuKvmSensorDescription(
        key="telemetry_log_head_id",
        name="Telemetry Log Head Index",
        icon="mdi:database-clock",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.log_record.head_id if d.log_record else 0,
        attr_fn=lambda d: (
            {
                "record_1_datetime": d.log_record.datetime_str,
                "record_1_alarms": d.log_record.alarms,
                "record_1_values": d.log_record.values,
            }
            if d.log_record
            else {}
        ),
    ),
    EzhuKvmSensorDescription(
        key="battery_test_log_last_id",
        name="Battery Test Log Count",
        icon="mdi:battery-clock",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.test_ab_record.last_id if d.test_ab_record else 0,
        attr_fn=lambda d: (
            {
                "record_id": d.test_ab_record.record_id,
                "start_datetime": d.test_ab_record.start_datetime_str,
                "end_datetime": d.test_ab_record.end_datetime_str,
                "state_code": d.test_ab_record.state_code,
                "floats": d.test_ab_record.floats,
            }
            if d.test_ab_record
            else {}
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EzhuKvmConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EZHU KVM48 read-only sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        EzhuKvmSensor(coordinator, desc) for desc in SENSOR_DESCRIPTIONS
    )


class EzhuKvmSensor(EzhuKvmEntity, SensorEntity):
    """Representation of an EZHU KVM48 read-only sensor."""

    entity_description: EzhuKvmSensorDescription

    def __init__(
        self,
        coordinator: EzhuKvmDataUpdateCoordinator,
        description: EzhuKvmSensorDescription,
    ) -> None:
        super().__init__(coordinator, f"sensor_{description.key}")
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        """Return the current sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        if self.entity_description.attr_fn is None:
            return None
        return self.entity_description.attr_fn(self.coordinator.data)
