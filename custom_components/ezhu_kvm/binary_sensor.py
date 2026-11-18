"""Read-only binary sensor entities for the EZHU KVM48 Power System integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EzhuKvmConfigEntry
from .const import ALARM_DEFINITIONS
from .coordinator import EzhuKvmDataUpdateCoordinator, EzhuKvmSnapshot
from .entity import EzhuKvmEntity


@dataclass(frozen=True, kw_only=True)
class EzhuKvmBinarySensorDescription(BinarySensorEntityDescription):
    """Describe an EZHU KVM48 read-only binary sensor entity."""

    is_on_fn: Callable[[EzhuKvmSnapshot], bool]


def _build_binary_sensor_descriptions() -> tuple[EzhuKvmBinarySensorDescription, ...]:
    descriptions: list[EzhuKvmBinarySensorDescription] = []

    # 1. 10 Alarms A1..A10 (0x05 GetState.Alarms[0..9])
    for alarm_idx, alarm_key, alarm_label in ALARM_DEFINITIONS:
        descriptions.append(
            EzhuKvmBinarySensorDescription(
                key=f"alarm_{alarm_key}",
                name=f"Alarm {alarm_label}",
                device_class=BinarySensorDeviceClass.PROBLEM,
                is_on_fn=lambda d, idx=alarm_idx: bool(d.state.alarms[idx]),
            )
        )

    # 2. Live Testing State & Temperature Sensor Presence (0x05 GetState)
    descriptions.extend(
        [
            EzhuKvmBinarySensorDescription(
                key="testing_active",
                name="Battery Discharge Test Active",
                device_class=BinarySensorDeviceClass.RUNNING,
                icon="mdi:battery-heart-variant",
                is_on_fn=lambda d: bool(d.state.testing),
            ),
            EzhuKvmBinarySensorDescription(
                key="temp_ab_present",
                name="T ab Temperature Sensor Present",
                device_class=BinarySensorDeviceClass.CONNECTIVITY,
                entity_category=EntityCategory.DIAGNOSTIC,
                is_on_fn=lambda d: bool(d.state.temp_sens_presence),
            ),
            EzhuKvmBinarySensorDescription(
                key="temp_cu_present",
                name="T cu Temperature Sensor Present",
                device_class=BinarySensorDeviceClass.CONNECTIVITY,
                entity_category=EntityCategory.DIAGNOSTIC,
                is_on_fn=lambda d: bool(d.state.temp_sens_proc_presence),
            ),
        ]
    )

    # 3. 8 Relay / Contactor Output Bits (GetState.Rele bits 0..7)
    for bit in range(8):
        descriptions.append(
            EzhuKvmBinarySensorDescription(
                key=f"rele_bit_{bit}",
                name=f"Relay Output Bit {bit}",
                icon="mdi:electric-switch",
                entity_category=EntityCategory.DIAGNOSTIC,
                is_on_fn=lambda d, b=bit: bool(d.state.rele & (1 << b)),
            )
        )

    # 4. 16 Fault Bitmask Bits (GetState.Faults bits 0..15)
    for bit in range(16):
        descriptions.append(
            EzhuKvmBinarySensorDescription(
                key=f"fault_bit_{bit}",
                name=f"Fault Flag Bit {bit}",
                device_class=BinarySensorDeviceClass.PROBLEM,
                entity_category=EntityCategory.DIAGNOSTIC,
                is_on_fn=lambda d, b=bit: bool(d.state.faults & (1 << b)),
            )
        )

    return tuple(descriptions)


BINARY_SENSOR_DESCRIPTIONS = _build_binary_sensor_descriptions()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EzhuKvmConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EZHU KVM48 read-only binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        EzhuKvmBinarySensor(coordinator, desc) for desc in BINARY_SENSOR_DESCRIPTIONS
    )


class EzhuKvmBinarySensor(EzhuKvmEntity, BinarySensorEntity):
    """Representation of an EZHU KVM48 read-only binary sensor."""

    entity_description: EzhuKvmBinarySensorDescription

    def __init__(
        self,
        coordinator: EzhuKvmDataUpdateCoordinator,
        description: EzhuKvmBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, f"binary_sensor_{description.key}")
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self.entity_description.is_on_fn(self.coordinator.data)
