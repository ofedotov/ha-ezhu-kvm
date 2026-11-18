"""Constants for the EZHU KVM48 Power System (ЕЖУ И 14000 Б 48-160-хД / КВМ48-20) integration."""

from __future__ import annotations

DOMAIN = "ezhu_kvm"

DEFAULT_NAME = "EZHU KVM48-20"
DEFAULT_HOST = ""
DEFAULT_PORT = 1001
DEFAULT_PASSWORD = "555555"
DEFAULT_FACTORY_PASSWORD = "434410"
DEFAULT_SCAN_INTERVAL = 10
DEFAULT_CONFIG_REFRESH_CYCLES = 6

CONF_FACTORY_PASSWORD = "factory_password"
CONF_INTERFACE = "interface"

# WAKE Protocol Framing Constants
WAKE_FEND = 0xC0
WAKE_FESC = 0xDB
WAKE_TFEND = 0xDC
WAKE_TFESC = 0xDD
WAKE_CRC_INIT = 0xDE
WAKE_CRC_POLY = 0x18

# WAKE Command IDs (from KVMCtrlMon.exe RTTI / disassembly)
CMD_NOP = 0x00
CMD_ERR = 0x01
CMD_ECHO = 0x02
CMD_INFO = 0x03
KVM_CMD_GET_INFO_EX = 0x04
KVM_CMD_GET_STATE = 0x05
KVM_CMD_SET_DATETIME = 0x06
KVM_CMD_GET_ADC_PARAMS = 0x07
KVM_CMD_SET_ADC_PARAMS = 0x08
KVM_CMD_GET_AB_PARAMS = 0x09
KVM_CMD_SET_AB_PARAMS = 0x0A
KVM_CMD_GET_CTRL_PARAMS = 0x0B
KVM_CMD_SET_CTRL_PARAMS = 0x0C
KVM_CMD_GET_RELAY_PARAMS = 0x0D
KVM_CMD_SET_RELAY_PARAMS = 0x0E
KVM_CMD_GET_SYS_PARAMS = 0x0F
KVM_CMD_SET_SYS_PARAMS = 0x10
KVM_CMD_GET_ETH_PARAMS = 0x11
KVM_CMD_SET_ETH_PARAMS = 0x12
KVM_CMD_GET_SNMP_PARAMS = 0x13
KVM_CMD_SET_SNMP_PARAMS = 0x14
KVM_CMD_GET_LOG_RECORD = 0x15
KVM_CMD_CLEAR_LOG = 0x16
KVM_CMD_GET_TEST_AB_RECORD = 0x17
KVM_CMD_CLEAR_TEST_AB_RECORD = 0x18
KVM_CMD_SET_TEST_STATE = 0x19
KVM_CMD_SET_FACTORY_DEFAULTS = 0x1A
KVM_CMD_RESET_DEVICE = 0x1B
KVM_CMD_SEND_SNMP_TRAP = 0x1D
KVM_CMD_SET_SYS_LOCATION = 0x1E
KVM_CMD_SET_SYS_INFO = 0x1F

# WAKE Status / Error Codes
STATUS_OK = 0x00
STATUS_ERR_NO = 0x00
STATUS_ERR_TX = 0x01
STATUS_ERR_BUFSIZE = 0x02
STATUS_ERR_PARAM = 0x03
STATUS_ERR_CRC = 0x04
STATUS_ERR_FLASH = 0x05
STATUS_ERR_BUSY = 0x06
STATUS_ERR_TIMEOUT = 0x07
STATUS_ERR_ACCESS_DENIED = 0x08

STATUS_NAMES: dict[int, str] = {
    0x00: "OK",
    0x01: "ERR_TX",
    0x02: "ERR_BUFSIZE",
    0x03: "ERR_PARAM",
    0x04: "ERR_CRC",
    0x05: "ERR_FLASH",
    0x06: "ERR_BUSY",
    0x07: "ERR_TIMEOUT",
    0x08: "ACCESS_DENIED",
}

# WorkMode (read-only live status in GetState)
WORK_MODES: dict[int, str] = {
    0: "Idle (0)",
    1: "Auto U",
    2: "Auto IU",
    3: "Manual U",
    4: "Manual IU",
    5: "Testing AB",
}

# Battery Charge Regime (read/write in TABParams.regime)
REGIME_OPTIONS: dict[int, str] = {
    1: "Auto U",
    2: "Auto IU",
    3: "Manual U",
    4: "Manual IU",
}
REGIME_NAME_TO_ID: dict[str, int] = {v: k for k, v in REGIME_OPTIONS.items()}

# ADC Channel Metadata (Indices 0..7)
ADC_CHANNEL_DESCRIPTIONS: dict[int, tuple[str, str, str]] = {
    0: ("i_ab1", "I ab1 (Battery 1 Current)", "A"),
    1: ("i_ab2", "I ab2 (Battery 2 Current)", "A"),
    2: ("i3_unused", "I3 (Channel 2 Current)", "A"),
    3: ("i_load", "I load (Load Current)", "A"),
    4: ("u_ph1", "U ph1 (Phase A Voltage)", "V"),
    5: ("u_ph2", "U ph2 (Phase B Voltage)", "V"),
    6: ("u_load", "U load (DC Bus/Load Voltage)", "V"),
    7: ("u_ph3", "U ph3 (Phase C Voltage)", "V"),
}

# 10 Alarm Channels (A1..A10)
ALARM_DEFINITIONS: list[tuple[int, str, str]] = [
    (0, "a1_ac_input", "A1 AC Input (Мережа ~380В)"),
    (1, "a2_rectifiers", "A2 Rectifiers (Випрямлячі)"),
    (2, "a3_overload", "A3 Overload (Перевантаження)"),
    (3, "a4_ab_circuit", "A4 AB Circuit (Коло АБ)"),
    (4, "a5_open_door", "A5 Open Door (Двері відчинено)"),
    (5, "a6_load_state", "A6 Load State (Стан навантаження)"),
    (6, "a7_overvoltage", "A7 Overvoltage (U > Umax)"),
    (7, "a8_undervoltage", "A8 Undervoltage (U < Umin)"),
    (8, "a9_ab_overtemp", "A9 AB Overtemperature (T АБ > Tmax)"),
    (9, "a10_fire", "A10 Fire (Пожежа)"),
]

# 4 Relay/Sound Output Groups in TRelayConfiguration (4 x 10 bytes)
RELAY_OUTPUT_GROUPS: list[tuple[int, str, str]] = [
    (0, "relay1", "Relay 1"),
    (1, "relay2", "Relay 2"),
    (2, "relay3", "Relay 3"),
    (3, "sound", "Sound Alarm"),
]
