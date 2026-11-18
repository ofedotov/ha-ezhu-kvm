"""Read/write number entities for the EZHU KVM48 Power System integration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EzhuKvmConfigEntry
from .const import ADC_CHANNEL_DESCRIPTIONS
from .coordinator import EzhuKvmDataUpdateCoordinator, EzhuKvmSnapshot
from .entity import EzhuKvmEntity


@dataclass(frozen=True, kw_only=True)
class EzhuKvmNumberDescription(NumberEntityDescription):
    """Describe an EZHU KVM48 modifiable numeric parameter."""

    value_fn: Callable[[EzhuKvmSnapshot], float]
    set_value_fn: Callable[[EzhuKvmDataUpdateCoordinator, float], Awaitable[None]]


def _build_number_descriptions() -> tuple[EzhuKvmNumberDescription, ...]:
    descriptions: list[EzhuKvmNumberDescription] = [
        # --- 1. TABParams (0x09 / 0x0A Battery & Test Configuration) ---
        EzhuKvmNumberDescription(
            key="ab_cell_count",
            name="AB Cell Count",
            icon="mdi:battery-charging-high",
            native_min_value=1,
            native_max_value=200,
            native_step=1,
            mode=NumberMode.BOX,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: float(d.ab_params.cell_count),
            set_value_fn=lambda c, v: c.async_update_ab_params(
                cell_count=int(round(v))
            ),
        ),
        EzhuKvmNumberDescription(
            key="ab_dudt",
            name="AB Temp Compensation (dU/dT)",
            icon="mdi:thermometer-lines",
            native_unit_of_measurement="mV/°C",
            native_min_value=-100,
            native_max_value=100,
            native_step=1,
            mode=NumberMode.BOX,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: float(d.ab_params.dudt),
            set_value_fn=lambda c, v: c.async_update_ab_params(dudt=int(round(v))),
        ),
        EzhuKvmNumberDescription(
            key="ab_u20c",
            name="AB Float Cell Voltage at 20°C (U20C)",
            device_class=NumberDeviceClass.VOLTAGE,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            native_min_value=1.500,
            native_max_value=3.000,
            native_step=0.001,
            mode=NumberMode.BOX,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.ab_params.u20c,
            set_value_fn=lambda c, v: c.async_update_ab_params(
                u20c_raw=int(round(v * 1000))
            ),
        ),
        EzhuKvmNumberDescription(
            key="ab_qab",
            name="AB Nominal Capacity (Qab)",
            icon="mdi:battery-high",
            native_unit_of_measurement="Ah",
            native_min_value=1,
            native_max_value=5000,
            native_step=1,
            mode=NumberMode.BOX,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: float(d.ab_params.qab),
            set_value_fn=lambda c, v: c.async_update_ab_params(qab=int(round(v))),
        ),
        EzhuKvmNumberDescription(
            key="ab_icharge",
            name="AB Charge Current Limit (Icharge)",
            device_class=NumberDeviceClass.CURRENT,
            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            native_min_value=0.1,
            native_max_value=500.0,
            native_step=0.1,
            mode=NumberMode.BOX,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.ab_params.icharge,
            set_value_fn=lambda c, v: c.async_update_ab_params(
                icharge_raw=int(round(v * 10))
            ),
        ),
        EzhuKvmNumberDescription(
            key="ab_dt_iu",
            name="AB Boost Charge Duration (dT IU)",
            icon="mdi:timer-cog-outline",
            native_unit_of_measurement=UnitOfTime.MINUTES,
            native_min_value=0,
            native_max_value=10000,
            native_step=1,
            mode=NumberMode.BOX,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: float(d.ab_params.dt_iu),
            set_value_fn=lambda c, v: c.async_update_ab_params(dt_iu=int(round(v))),
        ),
        EzhuKvmNumberDescription(
            key="ab_test_tdischarge",
            name="AB Test Max Discharge Time",
            icon="mdi:timer-outline",
            native_unit_of_measurement=UnitOfTime.MINUTES,
            native_min_value=1,
            native_max_value=10000,
            native_step=1,
            mode=NumberMode.BOX,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: float(d.ab_params.test_tdischarge),
            set_value_fn=lambda c, v: c.async_update_ab_params(
                test_tdischarge=int(round(v))
            ),
        ),
        EzhuKvmNumberDescription(
            key="ab_test_umin",
            name="AB Test End-of-Discharge Voltage (Umin)",
            device_class=NumberDeviceClass.VOLTAGE,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            native_min_value=20.00,
            native_max_value=80.00,
            native_step=0.01,
            mode=NumberMode.BOX,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.ab_params.test_umin,
            set_value_fn=lambda c, v: c.async_update_ab_params(
                test_umin_raw=int(round(v * 100))
            ),
        ),
        EzhuKvmNumberDescription(
            key="ab_test_ttesting",
            name="AB Periodic Test Interval",
            icon="mdi:calendar-refresh",
            native_unit_of_measurement="months",
            native_min_value=0,
            native_max_value=120,
            native_step=1,
            mode=NumberMode.BOX,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: float(d.ab_params.test_ttesting),
            set_value_fn=lambda c, v: c.async_update_ab_params(
                test_ttesting=int(round(v))
            ),
        ),
        EzhuKvmNumberDescription(
            key="ab_test_tarchivation",
            name="AB Test Logging Interval",
            icon="mdi:clock-fast",
            native_unit_of_measurement=UnitOfTime.MINUTES,
            native_min_value=1,
            native_max_value=1440,
            native_step=1,
            mode=NumberMode.BOX,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: float(d.ab_params.test_tarchivation),
            set_value_fn=lambda c, v: c.async_update_ab_params(
                test_tarchivation=int(round(v))
            ),
        ),
        # --- 2. TCtrlParams (0x0B / 0x0C Thresholds & Manual Voltage) ---
        EzhuKvmNumberDescription(
            key="ctrl_umanual",
            name="Ctrl Umanual (Manual Output Voltage Setpoint)",
            device_class=NumberDeviceClass.VOLTAGE,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            native_min_value=30.00,
            native_max_value=70.00,
            native_step=0.01,
            mode=NumberMode.BOX,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.ctrl_params.umanual,
            set_value_fn=lambda c, v: c.async_update_ctrl_params(
                umanual_raw=int(round(v * 100))
            ),
        ),
        EzhuKvmNumberDescription(
            key="ctrl_umax",
            name="Ctrl Umax (Overvoltage Alarm Threshold)",
            device_class=NumberDeviceClass.VOLTAGE,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            native_min_value=30.00,
            native_max_value=80.00,
            native_step=0.01,
            mode=NumberMode.BOX,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.ctrl_params.umax,
            set_value_fn=lambda c, v: c.async_update_ctrl_params(
                umax_raw=int(round(v * 100))
            ),
        ),
        EzhuKvmNumberDescription(
            key="ctrl_umax_hyst",
            name="Ctrl Umax Hysteresis",
            device_class=NumberDeviceClass.VOLTAGE,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            native_min_value=-20.00,
            native_max_value=20.00,
            native_step=0.01,
            mode=NumberMode.BOX,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.ctrl_params.umax_hyst,
            set_value_fn=lambda c, v: c.async_update_ctrl_params(
                umax_hyst_raw=int(round(v * 100))
            ),
        ),
        EzhuKvmNumberDescription(
            key="ctrl_umin",
            name="Ctrl Umin (Undervoltage Alarm Threshold)",
            device_class=NumberDeviceClass.VOLTAGE,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            native_min_value=20.00,
            native_max_value=70.00,
            native_step=0.01,
            mode=NumberMode.BOX,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.ctrl_params.umin,
            set_value_fn=lambda c, v: c.async_update_ctrl_params(
                umin_raw=int(round(v * 100))
            ),
        ),
        EzhuKvmNumberDescription(
            key="ctrl_umin_hyst",
            name="Ctrl Umin Hysteresis",
            device_class=NumberDeviceClass.VOLTAGE,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            native_min_value=-20.00,
            native_max_value=20.00,
            native_step=0.01,
            mode=NumberMode.BOX,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.ctrl_params.umin_hyst,
            set_value_fn=lambda c, v: c.async_update_ctrl_params(
                umin_hyst_raw=int(round(v * 100))
            ),
        ),
        EzhuKvmNumberDescription(
            key="ctrl_tdiscon_ab",
            name="Ctrl TdisconAB (Battery Overtemp Cutoff)",
            device_class=NumberDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            native_min_value=0.00,
            native_max_value=120.00,
            native_step=0.1,
            mode=NumberMode.BOX,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.ctrl_params.tdiscon_ab,
            set_value_fn=lambda c, v: c.async_update_ctrl_params(
                tdiscon_ab_raw=int(round(v * 100))
            ),
        ),
        EzhuKvmNumberDescription(
            key="ctrl_tdiscon_ab_hyst",
            name="Ctrl TdisconAB Hysteresis",
            device_class=NumberDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            native_min_value=-30.00,
            native_max_value=30.00,
            native_step=0.1,
            mode=NumberMode.BOX,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.ctrl_params.tdiscon_ab_hyst,
            set_value_fn=lambda c, v: c.async_update_ctrl_params(
                tdiscon_ab_hyst_raw=int(round(v * 100))
            ),
        ),
        EzhuKvmNumberDescription(
            key="ctrl_tmax_ab",
            name="Ctrl TmaxAB (Battery Overtemp Alarm Threshold)",
            device_class=NumberDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            native_min_value=0.00,
            native_max_value=120.00,
            native_step=0.1,
            mode=NumberMode.BOX,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.ctrl_params.tmax_ab,
            set_value_fn=lambda c, v: c.async_update_ctrl_params(
                tmax_ab_raw=int(round(v * 100))
            ),
        ),
        EzhuKvmNumberDescription(
            key="ctrl_tmax_ab_hyst",
            name="Ctrl TmaxAB Hysteresis",
            device_class=NumberDeviceClass.TEMPERATURE,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            native_min_value=-30.00,
            native_max_value=30.00,
            native_step=0.1,
            mode=NumberMode.BOX,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.ctrl_params.tmax_ab_hyst,
            set_value_fn=lambda c, v: c.async_update_ctrl_params(
                tmax_ab_hyst_raw=int(round(v * 100))
            ),
        ),
        EzhuKvmNumberDescription(
            key="ctrl_udiscon_npl",
            name="Ctrl UdisconNPL (Non-Priority Load LVD Cutoff)",
            device_class=NumberDeviceClass.VOLTAGE,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            native_min_value=20.00,
            native_max_value=70.00,
            native_step=0.01,
            mode=NumberMode.BOX,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.ctrl_params.udiscon_npl,
            set_value_fn=lambda c, v: c.async_update_ctrl_params(
                udiscon_npl_raw=int(round(v * 100))
            ),
        ),
        EzhuKvmNumberDescription(
            key="ctrl_udiscon_npl_hyst",
            name="Ctrl UdisconNPL Hysteresis",
            device_class=NumberDeviceClass.VOLTAGE,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            native_min_value=-20.00,
            native_max_value=20.00,
            native_step=0.01,
            mode=NumberMode.BOX,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.ctrl_params.udiscon_npl_hyst,
            set_value_fn=lambda c, v: c.async_update_ctrl_params(
                udiscon_npl_hyst_raw=int(round(v * 100))
            ),
        ),
        EzhuKvmNumberDescription(
            key="ctrl_udiscon_ab",
            name="Ctrl UdisconAB (Battery Deep-Discharge LVD Cutoff)",
            device_class=NumberDeviceClass.VOLTAGE,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            native_min_value=20.00,
            native_max_value=70.00,
            native_step=0.01,
            mode=NumberMode.BOX,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.ctrl_params.udiscon_ab,
            set_value_fn=lambda c, v: c.async_update_ctrl_params(
                udiscon_ab_raw=int(round(v * 100))
            ),
        ),
        EzhuKvmNumberDescription(
            key="ctrl_udiscon_ab_hyst",
            name="Ctrl UdisconAB Hysteresis",
            device_class=NumberDeviceClass.VOLTAGE,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            native_min_value=-20.00,
            native_max_value=20.00,
            native_step=0.01,
            mode=NumberMode.BOX,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: d.ctrl_params.udiscon_ab_hyst,
            set_value_fn=lambda c, v: c.async_update_ctrl_params(
                udiscon_ab_hyst_raw=int(round(v * 100))
            ),
        ),
        # --- 3. TSysParams (0x0F / 0x10 System Parameters) ---
        EzhuKvmNumberDescription(
            key="sys_period_archive",
            name="System Telemetry Archive Period",
            icon="mdi:database-clock-outline",
            native_unit_of_measurement=UnitOfTime.MINUTES,
            native_min_value=1,
            native_max_value=10080,
            native_step=1,
            mode=NumberMode.BOX,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: float(d.sys_params.period_archive),
            set_value_fn=lambda c, v: c.async_update_sys_params(
                period_archive=int(round(v))
            ),
        ),
        EzhuKvmNumberDescription(
            key="sys_active_interface",
            name="System Active Interface",
            icon="mdi:serial-port",
            native_min_value=0,
            native_max_value=255,
            native_step=1,
            mode=NumberMode.BOX,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: float(d.sys_params.active_interface),
            set_value_fn=lambda c, v: c.async_update_sys_params(
                active_interface=int(round(v))
            ),
        ),
        # --- 4. TEthParams & TSNMPParams Numeric Fields (0x11..0x14) ---
        EzhuKvmNumberDescription(
            key="eth_media_type",
            name="Ethernet Media Type",
            icon="mdi:ethernet",
            native_min_value=0,
            native_max_value=255,
            native_step=1,
            mode=NumberMode.BOX,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: float(d.eth_params.media_type),
            set_value_fn=lambda c, v: c.async_update_eth_params(
                media_type=int(round(v))
            ),
        ),
        EzhuKvmNumberDescription(
            key="snmp_trap_event_mask",
            name="SNMP Trap Event Mask",
            icon="mdi:bell-cog-outline",
            native_min_value=0,
            native_max_value=65535,
            native_step=1,
            mode=NumberMode.BOX,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda d: float(d.snmp_params.trap_event_mask),
            set_value_fn=lambda c, v: c.async_update_snmp_params(
                trap_event_mask=int(round(v))
            ),
        ),
    ]

    # --- 5. TADCParams Offset & Gain for Channels 0..7 (0x07 / 0x08) ---
    for ch_idx, (ch_key, ch_label, _unit) in ADC_CHANNEL_DESCRIPTIONS.items():
        descriptions.append(
            EzhuKvmNumberDescription(
                key=f"adc_ch{ch_idx}_{ch_key}_offset",
                name=f"ADC Ch{ch_idx} ({ch_label}) Offset",
                icon="mdi:tune-vertical",
                native_min_value=-10000.0,
                native_max_value=10000.0,
                native_step=0.01,
                mode=NumberMode.BOX,
                entity_category=EntityCategory.CONFIG,
                value_fn=lambda d, ch=ch_idx: d.adc_params[ch].offset,
                set_value_fn=lambda c, v, ch=ch_idx: c.async_update_adc_params(
                    ch, offset_raw=int(round(v * 100))
                ),
            )
        )
        descriptions.append(
            EzhuKvmNumberDescription(
                key=f"adc_ch{ch_idx}_{ch_key}_gain",
                name=f"ADC Ch{ch_idx} ({ch_label}) Gain",
                icon="mdi:tune-vertical",
                native_min_value=-100.0,
                native_max_value=100.0,
                native_step=0.0001,
                mode=NumberMode.BOX,
                entity_category=EntityCategory.CONFIG,
                value_fn=lambda d, ch=ch_idx: d.adc_params[ch].gain,
                set_value_fn=lambda c, v, ch=ch_idx: c.async_update_adc_params(
                    ch, gain_raw=int(round(v * 10000))
                ),
            )
        )

    return tuple(descriptions)


NUMBER_DESCRIPTIONS = _build_number_descriptions()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EzhuKvmConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EZHU KVM48 modifiable number entities."""
    coordinator = entry.runtime_data
    async_add_entities(
        EzhuKvmNumber(coordinator, desc) for desc in NUMBER_DESCRIPTIONS
    )


class EzhuKvmNumber(EzhuKvmEntity, NumberEntity):
    """Representation of an EZHU KVM48 read/write numeric parameter."""

    entity_description: EzhuKvmNumberDescription

    def __init__(
        self,
        coordinator: EzhuKvmDataUpdateCoordinator,
        description: EzhuKvmNumberDescription,
    ) -> None:
        super().__init__(coordinator, f"number_{description.key}")
        self.entity_description = description

    @property
    def native_value(self) -> float:
        """Return the current parameter value."""
        return self.entity_description.value_fn(self.coordinator.data)

    async def async_set_native_value(self, value: float) -> None:
        """Write the updated parameter value to the controller."""
        await self.entity_description.set_value_fn(self.coordinator, value)
