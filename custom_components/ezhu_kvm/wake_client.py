"""TCP WAKE protocol client for EZHU KVM48 Power System (ЕЖУ И 14000 Б 48-160-хД / КВМ48-20)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
import ipaddress
import logging
import socket
import struct
import sys
import time
from typing import Any

from .const import (
    DEFAULT_FACTORY_PASSWORD,
    DEFAULT_HOST,
    DEFAULT_PASSWORD,
    DEFAULT_PORT,
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
    STATUS_NAMES,
    STATUS_OK,
    WAKE_CRC_INIT,
    WAKE_CRC_POLY,
    WAKE_FEND,
    WAKE_FESC,
    WAKE_TFEND,
    WAKE_TFESC,
    WORK_MODES,
)

_LOGGER = logging.getLogger(__name__)

MACOS_IP_BOUND_IF = 25


class EzhuKvmError(Exception):
    """Base exception for EZHU KVM errors."""


class EzhuKvmCommandError(EzhuKvmError):
    """Exception raised when device returns a non-zero status code."""

    def __init__(self, cmd: int, status_code: int) -> None:
        self.cmd = cmd
        self.status_code = status_code
        status_name = STATUS_NAMES.get(status_code, f"0x{status_code:02X}")
        super().__init__(
            f"WAKE command 0x{cmd:02X} failed with status {status_name} (0x{status_code:02X})"
        )


def calc_wake_crc(data: bytes) -> int:
    """Calculate WAKE reflected CRC-8 (init=0xDE, poly=0x18)."""
    crc = WAKE_CRC_INIT
    for b in data:
        for _ in range(8):
            if (b ^ crc) & 1:
                crc = ((crc ^ WAKE_CRC_POLY) >> 1) | 0x80
            else:
                crc = (crc >> 1) & 0x7F
            b >>= 1
    return crc


def stuff_wake_bytes(raw: bytes) -> bytes:
    """Apply WAKE SLIP-like byte stuffing (0xC0 -> 0xDB 0xDC, 0xDB -> 0xDB 0xDD)."""
    out = bytearray()
    for b in raw:
        if b == WAKE_FEND:
            out.extend((WAKE_FESC, WAKE_TFEND))
        elif b == WAKE_FESC:
            out.extend((WAKE_FESC, WAKE_TFESC))
        else:
            out.append(b)
    return bytes(out)


def build_wake_frame(cmd: int, payload: bytes = b"", addr: int = 0) -> bytes:
    """Build a byte-stuffed WAKE request frame."""
    if len(payload) > 255:
        raise ValueError(f"WAKE payload too long: {len(payload)} > 255")
    cmd_byte = cmd & 0x7F
    nbt = len(payload)
    header = bytearray([WAKE_FEND])
    body = bytearray()
    if addr & 0x7F:
        addr_byte = (addr & 0x7F) | 0x80
        header.append(addr_byte)
        body.append(addr_byte)
    header.extend((cmd_byte, nbt))
    body.extend((cmd_byte, nbt))
    crc = calc_wake_crc(bytes(header) + payload)
    body.extend(payload)
    body.append(crc)
    return bytes([WAKE_FEND]) + stuff_wake_bytes(bytes(body))


def decode_cstr(raw: bytes, encoding: str = "cp1251") -> str:
    """Decode a null-terminated C string from a fixed-size byte buffer."""
    return raw.split(b"\x00", 1)[0].decode(encoding, errors="replace").strip()


def encode_cstr(value: str, size: int, encoding: str = "cp1251") -> bytes:
    """Encode a string into a fixed-size null-padded byte buffer."""
    raw = value.encode(encoding, errors="replace")[:size]
    return raw.ljust(size, b"\x00")


def bcd_to_int(b: int) -> int:
    """Convert a single BCD byte to integer (matches 0x5570de in KVMCtrlMon.exe)."""
    hi = (b >> 4) & 0x0F
    lo = b & 0x0F
    if hi > 9 or lo > 9:
        return 0
    return hi * 10 + lo


def int_to_bcd(val: int) -> int:
    """Convert an integer 0..99 to BCD byte (matches 0x5570a4 in KVMCtrlMon.exe)."""
    if val < 0 or val >= 100:
        return 0
    return ((val // 10) << 4) | (val % 10)


def format_bcd_datetime(raw6: bytes) -> str:
    """Format 6 BCD bytes [Y-2000, M, D, h, m, s] as ISO-like string."""
    if len(raw6) < 6:
        return "2000-00-00 00:00:00"
    y, m, d, hh, mm, ss = (bcd_to_int(x) for x in raw6[:6])
    return f"20{y:02d}-{m:02d}-{d:02d} {hh:02d}:{mm:02d}:{ss:02d}"


def encode_bcd_datetime(dt: datetime) -> bytes:
    """Encode a Python datetime into 6 BCD bytes [Y-2000, M, D, h, m, s]."""
    y = max(0, min(99, dt.year - 2000))
    return bytes(
        [
            int_to_bcd(y),
            int_to_bcd(dt.month),
            int_to_bcd(dt.day),
            int_to_bcd(dt.hour),
            int_to_bcd(dt.minute),
            int_to_bcd(dt.second),
        ]
    )


def format_ipv4(raw4: bytes) -> str:
    """Format 4 bytes as dotted-quad IPv4 string."""
    return ".".join(str(b) for b in raw4[:4])


def parse_ipv4(ip_str: str) -> bytes:
    """Parse dotted-quad IPv4 string into 4 bytes."""
    addr = ipaddress.IPv4Address(ip_str.strip())
    return addr.packed


def format_mac(raw6: bytes) -> str:
    """Format 6 bytes as colon-separated lowercase MAC address."""
    return ":".join(f"{b:02x}" for b in raw6[:6])


def parse_mac(mac_str: str) -> bytes:
    """Parse a colon- or hyphen-separated MAC address into 6 bytes."""
    cleaned = mac_str.strip().replace("-", ":").replace(".", ":")
    parts = cleaned.split(":")
    if len(parts) != 6:
        raise ValueError(f"Invalid MAC address format: {mac_str}")
    return bytes(int(p, 16) for p in parts)


def decode_user_password(raw6: bytes) -> str:
    """Decode TSysParams.Password_User[6] (stored as 6 digit bytes 0..9 or ASCII)."""
    chars: list[str] = []
    for b in raw6[:6]:
        if 0 <= b <= 9:
            chars.append(str(b))
        elif 0x30 <= b <= 0x39:
            chars.append(chr(b))
        elif b == 0:
            chars.append("0")
        else:
            chars.append(str(b % 10))
    return "".join(chars)


def encode_user_password(pin: str) -> bytes:
    """Encode a 6-digit user PIN into TSysParams.Password_User[6] (bytes 0..9)."""
    cleaned = "".join(ch for ch in pin.strip() if ch.isdigit())
    if len(cleaned) != 6:
        raise ValueError("User password (PIN) must be exactly 6 digits (0..9)")
    return bytes(int(ch) for ch in cleaned)


@dataclass(slots=True)
class KvmInfoEx:
    """Parsed 0x04 GetInfoEx response (TKVMGetInfoExAns, 172 bytes)."""

    bl_version: tuple[int, int, int, int]
    bl_version_str: str
    bl_build_datetime: str
    fw_version: tuple[int, int, int, int]
    fw_version_str: str
    fw_build_datetime: str
    hardware_id: str
    dev_name: str
    serial_number: str
    customer: str
    sys_location: str
    hostname: str


@dataclass(slots=True)
class KvmAdcChannelState:
    """Single ADC channel measurement from 0x05 GetState (12 bytes: <8sf)."""

    index: int
    name: str
    value: float


@dataclass(slots=True)
class KvmState:
    """Parsed 0x05 GetState response (160 bytes)."""

    status: int
    header_reserved: int
    temp_sens_value: float
    temp_sens_presence: int
    temp_sens_crc_errors: int
    temp_sens_proc_value: float
    temp_sens_proc_presence: int
    temp_sens_proc_crc_errors: int
    channels: list[KvmAdcChannelState]
    datetime_bcd: bytes
    datetime_str: str
    next_test_ab_bcd: bytes
    next_test_ab_str: str
    testing: int
    work_mode: int
    work_mode_str: str
    faults: int
    alarms: list[int]
    ucontrol_raw: int
    ucontrol_v: float
    rele: int
    access_level: int

    @property
    def u_load(self) -> float:
        """DC load/bus voltage (Ch 6)."""
        return round(self.channels[6].value, 2) if len(self.channels) > 6 else 0.0

    @property
    def i_ab1(self) -> float:
        """Battery group 1 current (Ch 0)."""
        return round(self.channels[0].value, 3) if len(self.channels) > 0 else 0.0

    @property
    def i_ab2(self) -> float:
        """Battery group 2 current (Ch 1)."""
        return round(self.channels[1].value, 3) if len(self.channels) > 1 else 0.0

    @property
    def i_ab_total(self) -> float:
        """Total battery current (I ab1 + I ab2)."""
        return round(self.i_ab1 + self.i_ab2, 3)

    @property
    def i3_unused(self) -> float:
        """Channel 2 current (Ch 2)."""
        return round(self.channels[2].value, 3) if len(self.channels) > 2 else 0.0

    @property
    def i_load(self) -> float:
        """Load current (Ch 3)."""
        return round(self.channels[3].value, 3) if len(self.channels) > 3 else 0.0

    @property
    def p_load(self) -> float:
        """Calculated DC load power (U load * I load) in Watts."""
        return round(self.u_load * self.i_load, 2)

    @property
    def u_ph1(self) -> float:
        """AC Phase A voltage (Ch 4)."""
        return round(self.channels[4].value, 1) if len(self.channels) > 4 else 0.0

    @property
    def u_ph2(self) -> float:
        """AC Phase B voltage (Ch 5)."""
        return round(self.channels[5].value, 1) if len(self.channels) > 5 else 0.0

    @property
    def u_ph3(self) -> float:
        """AC Phase C voltage (Ch 7)."""
        return round(self.channels[7].value, 1) if len(self.channels) > 7 else 0.0


@dataclass(slots=True)
class KvmAdcParams:
    """Parsed 0x07/0x08 TADCParams (20 bytes: <8siii)."""

    channel: int
    channel_name: str
    channel_enabled: bool
    offset_raw: int
    gain_raw: int

    @property
    def offset(self) -> float:
        """Offset scaled by 1/100."""
        return round(self.offset_raw / 100.0, 2)

    @property
    def gain(self) -> float:
        """Gain scaled by 1/10000."""
        return round(self.gain_raw / 10000.0, 4)

    def to_bytes(self) -> bytes:
        """Pack into 20-byte TADCParams struct."""
        return struct.pack(
            "<8siii",
            encode_cstr(self.channel_name, 8),
            1 if self.channel_enabled else 0,
            int(self.offset_raw),
            int(self.gain_raw),
        )


@dataclass(slots=True)
class KvmAbParams:
    """Parsed 0x09/0x0A TABParams (44 bytes: <11i)."""

    cell_count: int
    dudt: int
    u20c_raw: int
    qab: int
    regime: int
    icharge_raw: int
    dt_iu: int
    test_tdischarge: int
    test_umin_raw: int
    test_ttesting: int
    test_tarchivation: int

    @property
    def u20c(self) -> float:
        """Float cell voltage at 20°C (V/cell, raw / 1000)."""
        return round(self.u20c_raw / 1000.0, 3)

    @property
    def icharge(self) -> float:
        """Battery charge current limit (A, raw / 10)."""
        return round(self.icharge_raw / 10.0, 1)

    @property
    def test_umin(self) -> float:
        """Battery test minimum end-of-discharge voltage (V, raw / 100)."""
        return round(self.test_umin_raw / 100.0, 2)

    def to_bytes(self) -> bytes:
        """Pack into 44-byte TABParams struct."""
        return struct.pack(
            "<11i",
            int(self.cell_count),
            int(self.dudt),
            int(self.u20c_raw),
            int(self.qab),
            int(self.regime),
            int(self.icharge_raw),
            int(self.dt_iu),
            int(self.test_tdischarge),
            int(self.test_umin_raw),
            int(self.test_ttesting),
            int(self.test_tarchivation),
        )


@dataclass(slots=True)
class KvmCtrlParams:
    """Parsed 0x0B/0x0C TCtrlParams (52 bytes: <13i, all scaled x100)."""

    umax_raw: int
    umax_hyst_raw: int
    umin_raw: int
    umin_hyst_raw: int
    tdiscon_ab_raw: int
    tdiscon_ab_hyst_raw: int
    tmax_ab_raw: int
    tmax_ab_hyst_raw: int
    udiscon_npl_raw: int
    udiscon_npl_hyst_raw: int
    udiscon_ab_raw: int
    udiscon_ab_hyst_raw: int
    umanual_raw: int

    @property
    def umax(self) -> float:
        return round(self.umax_raw / 100.0, 2)

    @property
    def umax_hyst(self) -> float:
        return round(self.umax_hyst_raw / 100.0, 2)

    @property
    def umin(self) -> float:
        return round(self.umin_raw / 100.0, 2)

    @property
    def umin_hyst(self) -> float:
        return round(self.umin_hyst_raw / 100.0, 2)

    @property
    def tdiscon_ab(self) -> float:
        return round(self.tdiscon_ab_raw / 100.0, 2)

    @property
    def tdiscon_ab_hyst(self) -> float:
        return round(self.tdiscon_ab_hyst_raw / 100.0, 2)

    @property
    def tmax_ab(self) -> float:
        return round(self.tmax_ab_raw / 100.0, 2)

    @property
    def tmax_ab_hyst(self) -> float:
        return round(self.tmax_ab_hyst_raw / 100.0, 2)

    @property
    def udiscon_npl(self) -> float:
        return round(self.udiscon_npl_raw / 100.0, 2)

    @property
    def udiscon_npl_hyst(self) -> float:
        return round(self.udiscon_npl_hyst_raw / 100.0, 2)

    @property
    def udiscon_ab(self) -> float:
        return round(self.udiscon_ab_raw / 100.0, 2)

    @property
    def udiscon_ab_hyst(self) -> float:
        return round(self.udiscon_ab_hyst_raw / 100.0, 2)

    @property
    def umanual(self) -> float:
        return round(self.umanual_raw / 100.0, 2)

    def to_bytes(self) -> bytes:
        """Pack into 52-byte TCtrlParams struct."""
        return struct.pack(
            "<13i",
            int(self.umax_raw),
            int(self.umax_hyst_raw),
            int(self.umin_raw),
            int(self.umin_hyst_raw),
            int(self.tdiscon_ab_raw),
            int(self.tdiscon_ab_hyst_raw),
            int(self.tmax_ab_raw),
            int(self.tmax_ab_hyst_raw),
            int(self.udiscon_npl_raw),
            int(self.udiscon_npl_hyst_raw),
            int(self.udiscon_ab_raw),
            int(self.udiscon_ab_hyst_raw),
            int(self.umanual_raw),
        )


@dataclass(slots=True)
class KvmRelayParams:
    """Parsed 0x0D/0x0E TRelayConfiguration (40 bytes: 4 groups x 10 alarms)."""

    matrix: list[list[bool]]

    def get_flag(self, group_idx: int, alarm_idx: int) -> bool:
        """Return whether alarm_idx (0..9) triggers group_idx (0=Relay1..3=Sound)."""
        return bool(self.matrix[group_idx][alarm_idx])

    def with_flag(self, group_idx: int, alarm_idx: int, enabled: bool) -> KvmRelayParams:
        """Return a copy with (group_idx, alarm_idx) updated."""
        new_matrix = [list(row) for row in self.matrix]
        new_matrix[group_idx][alarm_idx] = bool(enabled)
        return KvmRelayParams(matrix=new_matrix)

    def to_bytes(self) -> bytes:
        """Pack into 40-byte TRelayConfiguration struct."""
        out = bytearray()
        for group_idx in range(4):
            for alarm_idx in range(10):
                out.append(1 if self.matrix[group_idx][alarm_idx] else 0)
        return bytes(out)


@dataclass(slots=True)
class KvmSysParams:
    """Parsed 0x0F/0x10 TSysParams (12 bytes: <B6siB)."""

    voice: bool
    password_user: str
    period_archive: int
    active_interface: int

    def to_bytes(self) -> bytes:
        """Pack into 12-byte TSysParams struct."""
        return struct.pack(
            "<B6siB",
            1 if self.voice else 0,
            encode_user_password(self.password_user),
            int(self.period_archive),
            int(self.active_interface) & 0xFF,
        )


@dataclass(slots=True)
class KvmEthParams:
    """Parsed 0x11/0x12 TEthParams (44 bytes)."""

    hostname: str
    mac_addr: str
    dhcp_enabled: bool
    ip_addr: str
    def_gw: str
    net_mask: str
    pri_dns: str
    sec_dns: str
    media_type: int

    def to_bytes(self) -> bytes:
        """Pack into 44-byte TEthParams struct."""
        out = bytearray()
        out.extend(encode_cstr(self.hostname, 16))
        out.extend(parse_mac(self.mac_addr))
        out.append(1 if self.dhcp_enabled else 0)
        out.extend(parse_ipv4(self.ip_addr))
        out.extend(parse_ipv4(self.def_gw))
        out.extend(parse_ipv4(self.net_mask))
        out.extend(parse_ipv4(self.pri_dns))
        out.extend(parse_ipv4(self.sec_dns))
        out.append(int(self.media_type) & 0xFF)
        return bytes(out)


@dataclass(slots=True)
class KvmSnmpParams:
    """Parsed 0x13/0x14 TSNMPParams (40 bytes)."""

    community_name: str
    trap_servers: list[str]
    trap_event_mask: int

    def to_bytes(self) -> bytes:
        """Pack into 40-byte TSNMPParams struct."""
        out = bytearray()
        out.extend(encode_cstr(self.community_name, 16))
        for i in range(5):
            ip_str = self.trap_servers[i] if i < len(self.trap_servers) else "0.0.0.0"
            out.extend(parse_ipv4(ip_str))
        out.extend(struct.pack("<I", int(self.trap_event_mask) & 0xFFFFFFFF))
        return bytes(out)


@dataclass(slots=True)
class KvmLogRecord:
    """Parsed 0x15 GetLogRecord response (63 bytes)."""

    record_id: int
    head_id: int
    datetime_str: str
    alarms: list[int]
    values: list[float]


@dataclass(slots=True)
class KvmTestAbRecord:
    """Parsed 0x17 GetTestABRecord response (61 bytes)."""

    record_id: int
    last_id: int
    start_datetime_str: str
    end_datetime_str: str
    state_code: int
    floats: list[float]
    int1: int
    int2: int


class EzhuKvmClient:
    """Synchronous TCP WAKE client for EZHU KVM48-20 controller (run via executor in HA)."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        password: str = DEFAULT_PASSWORD,
        factory_password: str = DEFAULT_FACTORY_PASSWORD,
        timeout: float = 4.0,
        interface: str | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.password = password
        self.factory_password = factory_password
        self.timeout = timeout
        self.interface = interface
        self._auto_bound_if: str | None = None

    def _encode_password(self, pwd: str | None = None) -> bytes:
        """Encode 8-byte null-padded ASCII password."""
        actual = self.password if pwd is None else pwd
        return encode_cstr(actual, 8, encoding="ascii")

    def _encode_factory_password(self, pwd: str | None = None) -> bytes:
        """Encode 8-byte null-padded factory password."""
        actual = self.factory_password if pwd is None else pwd
        return encode_cstr(actual, 8, encoding="ascii")

    def _create_socket(self, bound_if: str | None = None) -> socket.socket:
        """Create and connect TCP socket, with optional interface binding."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        if bound_if:
            try:
                if sys.platform == "darwin":
                    if_idx = socket.if_nametoindex(bound_if)
                    sock.setsockopt(socket.IPPROTO_IP, MACOS_IP_BOUND_IF, if_idx)
                elif hasattr(socket, "SO_BINDTODEVICE"):
                    sock.setsockopt(
                        socket.SOL_SOCKET,
                        socket.SO_BINDTODEVICE,
                        bound_if.encode("ascii") + b"\x00",
                    )
            except OSError as err:
                _LOGGER.debug("Could not bind socket to interface %s: %s", bound_if, err)
        sock.connect((self.host, self.port))
        return sock

    def _connect(self) -> socket.socket:
        """Connect to device, falling back to en0 on macOS if direct route is shadowed."""
        chosen_if = self.interface or self._auto_bound_if
        try:
            return self._create_socket(chosen_if)
        except (TimeoutError, OSError) as first_err:
            if sys.platform == "darwin" and not chosen_if:
                try:
                    sock = self._create_socket("en0")
                    self._auto_bound_if = "en0"
                    return sock
                except OSError:
                    pass
            raise EzhuKvmError(
                f"Cannot connect to {self.host}:{self.port}: {first_err}"
            ) from first_err

    def _recv_frame(self, sock: socket.socket) -> tuple[int, bytes]:
        """Receive and decode a single WAKE frame from the socket."""
        in_frame = False
        esc = False
        addr_raw: int | None = None
        cmd: int | None = None
        nbt: int | None = None
        data = bytearray()

        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            chunk = sock.recv(1)
            if not chunk:
                raise EzhuKvmError("Connection closed by device while waiting for WAKE frame")
            b = chunk[0]
            if b == WAKE_FEND:
                in_frame = True
                esc = False
                addr_raw = None
                cmd = None
                nbt = None
                data.clear()
                continue
            if not in_frame:
                continue

            if esc:
                if b == WAKE_TFEND:
                    b = WAKE_FEND
                elif b == WAKE_TFESC:
                    b = WAKE_FESC
                else:
                    raise EzhuKvmError(f"Invalid WAKE byte-stuffing sequence: 0xDB 0x{b:02X}")
                esc = False
            elif b == WAKE_FESC:
                esc = True
                continue

            if cmd is None:
                if (b & 0x80) and addr_raw is None:
                    addr_raw = b
                    continue
                cmd = b
                continue

            if nbt is None:
                nbt = b
                continue

            if len(data) < nbt:
                data.append(b)
                continue

            rx_crc = b
            crc_buf = bytearray([WAKE_FEND])
            if addr_raw is not None:
                crc_buf.append(addr_raw)
            crc_buf.append(cmd)
            crc_buf.append(nbt)
            crc_buf.extend(data)
            expected_crc = calc_wake_crc(bytes(crc_buf))
            if rx_crc != expected_crc:
                _LOGGER.warning(
                    "WAKE RX CRC mismatch for cmd 0x%02X: rx=0x%02X expected=0x%02X",
                    cmd,
                    rx_crc,
                    expected_crc,
                )
            return cmd, bytes(data)

        raise EzhuKvmError(f"Timed out waiting for WAKE frame from {self.host}:{self.port}")

    def query(
        self,
        cmd: int,
        payload: bytes = b"",
        *,
        check_status: bool = True,
        sock: socket.socket | None = None,
    ) -> bytes:
        """Send a WAKE command and return the response data payload."""
        own_socket = sock is None
        active_sock = self._connect() if own_socket else sock
        assert active_sock is not None
        try:
            tx_frame = build_wake_frame(cmd, payload)
            active_sock.sendall(tx_frame)
            rx_cmd, rx_data = self._recv_frame(active_sock)
            if (rx_cmd & 0x7F) != (cmd & 0x7F):
                raise EzhuKvmError(
                    f"Unexpected WAKE command response: sent 0x{cmd:02X}, got 0x{rx_cmd:02X}"
                )
            if check_status and rx_data:
                status_code = rx_data[0]
                if status_code != STATUS_OK:
                    raise EzhuKvmCommandError(cmd, status_code)
            return rx_data
        finally:
            if own_socket:
                try:
                    active_sock.close()
                except OSError:
                    pass

    # -------------------------------------------------------------------------
    # Read Commands
    # -------------------------------------------------------------------------

    def get_info_ex(self, sock: socket.socket | None = None) -> KvmInfoEx:
        """0x04 GetInfoEx: Read static device info (172 bytes, no status byte)."""
        data = self.query(KVM_CMD_GET_INFO_EX, b"", check_status=False, sock=sock)
        if len(data) < 172:
            raise EzhuKvmError(f"GetInfoEx response too short: {len(data)} < 172")
        # Handle both 172-byte direct payload and 173-byte status-prefixed payload
        d = data[1:173] if len(data) >= 173 and data[0] == 0 and data[29] == 1 else data[:172]
        bl_maj, bl_min, bl_build, bl_svn = struct.unpack("<BBHI", d[0:8])
        bl_dt = decode_cstr(d[8:28])
        fw_maj, fw_min, fw_build, fw_svn = struct.unpack("<BBHI", d[28:36])
        fw_dt = decode_cstr(d[36:56])
        hw_id = decode_cstr(d[56:72])
        dev_name = decode_cstr(d[72:88])
        serial_num = decode_cstr(d[88:104])
        customer = decode_cstr(d[104:124])
        sys_loc = decode_cstr(d[124:156])
        hostname = decode_cstr(d[156:172])
        return KvmInfoEx(
            bl_version=(bl_maj, bl_min, bl_build, bl_svn),
            bl_version_str=f"{bl_maj}.{bl_min}.{bl_build} (SVN {bl_svn})",
            bl_build_datetime=bl_dt,
            fw_version=(fw_maj, fw_min, fw_build, fw_svn),
            fw_version_str=f"{fw_maj}.{fw_min}.{fw_build} (SVN {fw_svn})",
            fw_build_datetime=fw_dt,
            hardware_id=hw_id,
            dev_name=dev_name,
            serial_number=serial_num,
            customer=customer,
            sys_location=sys_loc,
            hostname=hostname,
        )

    def get_state(self, sock: socket.socket | None = None) -> KvmState:
        """0x05 GetState: Read live telemetry, temperatures, ADC channels, alarms, relays."""
        data = self.query(KVM_CMD_GET_STATE, struct.pack("<I", 0), sock=sock)
        if len(data) < 160:
            raise EzhuKvmError(f"GetState response too short: {len(data)} < 160")
        status = data[0]
        header_res = struct.unpack("<I", data[1:5])[0]
        st = data[5:160]
        ts_val, ts_pres, ts_crc = struct.unpack("<fII", st[0:12])
        tsp_val, tsp_pres, tsp_crc = struct.unpack("<fII", st[12:24])
        channels: list[KvmAdcChannelState] = []
        for idx in range(8):
            off = 24 + idx * 12
            raw_name, val = struct.unpack("<8sf", st[off : off + 12])
            channels.append(
                KvmAdcChannelState(
                    index=idx,
                    name=decode_cstr(raw_name),
                    value=float(val),
                )
            )
        dt_bcd = bytes(st[120:126])
        next_test_bcd = bytes(st[126:132])
        testing, work_mode, faults = struct.unpack("<IBH", st[132:139])
        alarms = list(st[139:149])
        ucontrol_raw, rele, access_level = struct.unpack("<IBB", st[149:155])
        return KvmState(
            status=status,
            header_reserved=header_res,
            temp_sens_value=round(float(ts_val), 2),
            temp_sens_presence=int(ts_pres),
            temp_sens_crc_errors=int(ts_crc),
            temp_sens_proc_value=round(float(tsp_val), 2),
            temp_sens_proc_presence=int(tsp_pres),
            temp_sens_proc_crc_errors=int(tsp_crc),
            channels=channels,
            datetime_bcd=dt_bcd,
            datetime_str=format_bcd_datetime(dt_bcd),
            next_test_ab_bcd=next_test_bcd,
            next_test_ab_str=format_bcd_datetime(next_test_bcd),
            testing=int(testing),
            work_mode=int(work_mode),
            work_mode_str=WORK_MODES.get(int(work_mode), f"Unknown ({work_mode})"),
            faults=int(faults),
            alarms=alarms,
            ucontrol_raw=int(ucontrol_raw),
            ucontrol_v=round(int(ucontrol_raw) / 100.0, 2),
            rele=int(rele),
            access_level=int(access_level),
        )

    def get_adc_params(self, channel: int, sock: socket.socket | None = None) -> KvmAdcParams:
        """0x07 GetADCParams: Read ADC calibration parameters for channel 0..7."""
        if not 0 <= channel <= 7:
            raise ValueError(f"ADC channel must be 0..7, got {channel}")
        data = self.query(KVM_CMD_GET_ADC_PARAMS, bytes([channel]), sock=sock)
        if len(data) < 22:
            raise EzhuKvmError(f"GetADCParams response too short: {len(data)} < 22")
        rx_ch = data[1]
        raw_name, enabled, offset_raw, gain_raw = struct.unpack("<8siii", data[2:22])
        return KvmAdcParams(
            channel=rx_ch,
            channel_name=decode_cstr(raw_name),
            channel_enabled=bool(enabled),
            offset_raw=int(offset_raw),
            gain_raw=int(gain_raw),
        )

    def get_all_adc_params(self, sock: socket.socket | None = None) -> dict[int, KvmAdcParams]:
        """Read all 8 ADC channel calibration parameters (0..7)."""
        own_socket = sock is None
        active_sock = self._connect() if own_socket else sock
        assert active_sock is not None
        try:
            return {ch: self.get_adc_params(ch, sock=active_sock) for ch in range(8)}
        finally:
            if own_socket:
                try:
                    active_sock.close()
                except OSError:
                    pass

    def get_ab_params(self, sock: socket.socket | None = None) -> KvmAbParams:
        """0x09 GetABParams: Read battery & charge/test parameters (45 bytes)."""
        data = self.query(KVM_CMD_GET_AB_PARAMS, b"", sock=sock)
        if len(data) < 45:
            raise EzhuKvmError(f"GetABParams response too short: {len(data)} < 45")
        vals = struct.unpack("<11i", data[1:45])
        return KvmAbParams(
            cell_count=vals[0],
            dudt=vals[1],
            u20c_raw=vals[2],
            qab=vals[3],
            regime=vals[4],
            icharge_raw=vals[5],
            dt_iu=vals[6],
            test_tdischarge=vals[7],
            test_umin_raw=vals[8],
            test_ttesting=vals[9],
            test_tarchivation=vals[10],
        )

    def get_ctrl_params(self, sock: socket.socket | None = None) -> KvmCtrlParams:
        """0x0B GetCtrlParams: Read voltage/temperature threshold & contactor parameters (53 bytes)."""
        data = self.query(KVM_CMD_GET_CTRL_PARAMS, b"", sock=sock)
        if len(data) < 53:
            raise EzhuKvmError(f"GetCtrlParams response too short: {len(data)} < 53")
        vals = struct.unpack("<13i", data[1:53])
        return KvmCtrlParams(*vals)

    def get_relay_params(self, sock: socket.socket | None = None) -> KvmRelayParams:
        """0x0D GetRelayParams: Read 4x10 alarm routing matrix for Relay 1..3 and Sound (41 bytes)."""
        data = self.query(KVM_CMD_GET_RELAY_PARAMS, b"", sock=sock)
        if len(data) < 41:
            raise EzhuKvmError(f"GetRelayParams response too short: {len(data)} < 41")
        raw = data[1:41]
        matrix: list[list[bool]] = []
        for g in range(4):
            row = [bool(raw[g * 10 + a]) for a in range(10)]
            matrix.append(row)
        return KvmRelayParams(matrix=matrix)

    def get_sys_params(self, sock: socket.socket | None = None) -> KvmSysParams:
        """0x0F GetSysParams: Read system parameters (Voice, User PIN, Archive Period, Interface)."""
        data = self.query(KVM_CMD_GET_SYS_PARAMS, b"", sock=sock)
        if len(data) < 13:
            raise EzhuKvmError(f"GetSysParams response too short: {len(data)} < 13")
        voice, raw_pin, period_arch, active_if = struct.unpack("<B6siB", data[1:13])
        return KvmSysParams(
            voice=bool(voice),
            password_user=decode_user_password(raw_pin),
            period_archive=int(period_arch),
            active_interface=int(active_if),
        )

    def get_eth_params(self, sock: socket.socket | None = None) -> KvmEthParams:
        """0x11 GetEthParams: Read Ethernet parameters (45 bytes)."""
        data = self.query(KVM_CMD_GET_ETH_PARAMS, b"", sock=sock)
        if len(data) < 45:
            raise EzhuKvmError(f"GetEthParams response too short: {len(data)} < 45")
        p = data[1:45]
        return KvmEthParams(
            hostname=decode_cstr(p[0:16]),
            mac_addr=format_mac(p[16:22]),
            dhcp_enabled=bool(p[22]),
            ip_addr=format_ipv4(p[23:27]),
            def_gw=format_ipv4(p[27:31]),
            net_mask=format_ipv4(p[31:35]),
            pri_dns=format_ipv4(p[35:39]),
            sec_dns=format_ipv4(p[39:43]),
            media_type=int(p[43]),
        )

    def get_snmp_params(self, sock: socket.socket | None = None) -> KvmSnmpParams:
        """0x13 GetSNMPParams: Read SNMP community, 5 trap servers, trap event mask (41 bytes)."""
        data = self.query(KVM_CMD_GET_SNMP_PARAMS, b"", sock=sock)
        if len(data) < 41:
            raise EzhuKvmError(f"GetSNMPParams response too short: {len(data)} < 41")
        p = data[1:41]
        community = decode_cstr(p[0:16])
        servers = [format_ipv4(p[16 + i * 4 : 20 + i * 4]) for i in range(5)]
        mask = struct.unpack("<I", p[36:40])[0]
        return KvmSnmpParams(
            community_name=community,
            trap_servers=servers,
            trap_event_mask=int(mask),
        )

    def get_log_record(self, record_id: int = 1, sock: socket.socket | None = None) -> KvmLogRecord:
        """0x15 GetLogRecord: Read telemetry archive record (63 bytes)."""
        data = self.query(KVM_CMD_GET_LOG_RECORD, struct.pack("<H", record_id & 0xFFFF), sock=sock)
        if len(data) < 63:
            raise EzhuKvmError(f"GetLogRecord response too short: {len(data)} < 63")
        rec_id, head_id = struct.unpack("<HH", data[1:5])
        dt_str = format_bcd_datetime(data[5:11])
        alarms = list(data[11:21])
        floats = [round(float(x), 3) for x in struct.unpack("<10f", data[23:63])]
        return KvmLogRecord(
            record_id=int(rec_id),
            head_id=int(head_id),
            datetime_str=dt_str,
            alarms=alarms,
            values=floats,
        )

    def get_test_ab_record(
        self, record_id: int = 0, sock: socket.socket | None = None
    ) -> KvmTestAbRecord:
        """0x17 GetTestABRecord: Read battery test archive record (61 bytes)."""
        data = self.query(
            KVM_CMD_GET_TEST_AB_RECORD, struct.pack("<H", record_id & 0xFFFF), sock=sock
        )
        if len(data) < 55:
            raise EzhuKvmError(f"GetTestABRecord response too short: {len(data)} < 55")
        rec_id = struct.unpack("<H", data[1:3])[0]
        start_dt = format_bcd_datetime(data[3:9])
        end_dt = format_bcd_datetime(data[9:15])
        state_code, f1, f2, f3, f4, f5, f6, i1, i2, last_id = struct.unpack(
            "<iffffffiii", data[15:55]
        )
        return KvmTestAbRecord(
            record_id=int(rec_id),
            last_id=int(last_id),
            start_datetime_str=start_dt,
            end_datetime_str=end_dt,
            state_code=int(state_code),
            floats=[round(float(x), 3) for x in (f1, f2, f3, f4, f5, f6)],
            int1=int(i1),
            int2=int(i2),
        )

    # -------------------------------------------------------------------------
    # Write & Action Commands
    # -------------------------------------------------------------------------

    def set_datetime(
        self,
        dt: datetime | None = None,
        *,
        save_to_flash: bool = True,
        sock: socket.socket | None = None,
    ) -> None:
        """0x06 SetDateTime: Set controller RTC date/time (16-byte request payload)."""
        target_dt = dt or datetime.now()
        payload = (
            b"\x00"
            + self._encode_password()
            + encode_bcd_datetime(target_dt)
            + bytes([1 if save_to_flash else 0])
        )
        self.query(KVM_CMD_SET_DATETIME, payload, sock=sock)

    def set_adc_params(
        self,
        params: KvmAdcParams,
        *,
        save_to_flash: bool = True,
        sock: socket.socket | None = None,
    ) -> None:
        """0x08 SetADCParams: Write ADC channel calibration parameters (30-byte request payload)."""
        if not 0 <= params.channel <= 7:
            raise ValueError(f"ADC channel must be 0..7, got {params.channel}")
        payload = (
            bytes([params.channel])
            + self._encode_password()
            + params.to_bytes()
            + bytes([1 if save_to_flash else 0])
        )
        self.query(KVM_CMD_SET_ADC_PARAMS, payload, sock=sock)

    def set_ab_params(
        self,
        params: KvmAbParams,
        *,
        save_to_flash: bool = True,
        sock: socket.socket | None = None,
    ) -> None:
        """0x0A SetABParams: Write battery & charge/test parameters (53-byte request payload)."""
        payload = (
            self._encode_password()
            + params.to_bytes()
            + bytes([1 if save_to_flash else 0])
        )
        self.query(KVM_CMD_SET_AB_PARAMS, payload, sock=sock)

    def set_ctrl_params(
        self,
        params: KvmCtrlParams,
        *,
        save_to_flash: bool = True,
        sock: socket.socket | None = None,
    ) -> None:
        """0x0C SetCtrlParams: Write voltage/temperature control thresholds (61-byte request payload)."""
        payload = (
            self._encode_password()
            + params.to_bytes()
            + bytes([1 if save_to_flash else 0])
        )
        self.query(KVM_CMD_SET_CTRL_PARAMS, payload, sock=sock)

    def set_relay_params(
        self,
        params: KvmRelayParams,
        *,
        save_to_flash: bool = True,
        sock: socket.socket | None = None,
    ) -> None:
        """0x0E SetRelayParams: Write 4x10 alarm routing matrix (49-byte request payload)."""
        payload = (
            self._encode_password()
            + params.to_bytes()
            + bytes([1 if save_to_flash else 0])
        )
        self.query(KVM_CMD_SET_RELAY_PARAMS, payload, sock=sock)

    def set_sys_params(
        self,
        params: KvmSysParams,
        *,
        save_to_flash: bool = True,
        sock: socket.socket | None = None,
    ) -> None:
        """0x10 SetSysParams: Write system parameters (21-byte request payload)."""
        payload = (
            self._encode_password()
            + params.to_bytes()
            + bytes([1 if save_to_flash else 0])
        )
        self.query(KVM_CMD_SET_SYS_PARAMS, payload, sock=sock)

    def set_eth_params(
        self,
        params: KvmEthParams,
        *,
        save_to_flash: bool = True,
        sock: socket.socket | None = None,
    ) -> None:
        """0x12 SetEthParams: Write Ethernet parameters (53-byte request payload)."""
        payload = (
            self._encode_password()
            + params.to_bytes()
            + bytes([1 if save_to_flash else 0])
        )
        self.query(KVM_CMD_SET_ETH_PARAMS, payload, sock=sock)

    def set_snmp_params(
        self,
        params: KvmSnmpParams,
        *,
        save_to_flash: bool = True,
        sock: socket.socket | None = None,
    ) -> None:
        """0x14 SetSNMPParams: Write SNMP configuration (49-byte request payload)."""
        payload = (
            self._encode_password()
            + params.to_bytes()
            + bytes([1 if save_to_flash else 0])
        )
        self.query(KVM_CMD_SET_SNMP_PARAMS, payload, sock=sock)

    def clear_log(self, sock: socket.socket | None = None) -> None:
        """0x16 ClearLog: Clear telemetry archive log (10-byte request payload)."""
        payload = self._encode_password() + struct.pack("<H", 0xFFFF)
        self.query(KVM_CMD_CLEAR_LOG, payload, sock=sock)

    def clear_test_ab_record(self, sock: socket.socket | None = None) -> None:
        """0x18 ClearTestABRecord: Clear battery test log (10-byte request payload)."""
        payload = self._encode_password() + struct.pack("<H", 0xFFFF)
        self.query(KVM_CMD_CLEAR_TEST_AB_RECORD, payload, sock=sock)

    def set_test_state(self, active: bool, sock: socket.socket | None = None) -> None:
        """0x19 SetTestState: Start (1) or stop (0) battery discharge test (9-byte request payload)."""
        payload = self._encode_password() + bytes([1 if active else 0])
        self.query(KVM_CMD_SET_TEST_STATE, payload, sock=sock)

    def set_factory_defaults(self, sock: socket.socket | None = None) -> None:
        """0x1A SetFactoryDefaults: Reset configuration to factory defaults (8-byte request payload)."""
        payload = self._encode_password()
        self.query(KVM_CMD_SET_FACTORY_DEFAULTS, payload, sock=sock)

    def reset_device(self, sock: socket.socket | None = None) -> None:
        """0x1B ResetDevice: Reboot the controller (8-byte request payload)."""
        payload = self._encode_password()
        self.query(KVM_CMD_RESET_DEVICE, payload, sock=sock)

    def send_snmp_trap(
        self, trap_code: int = 0, param: int = 0, sock: socket.socket | None = None
    ) -> None:
        """0x1D SendSNMPTrap: Trigger a test SNMP trap (8-byte TSNMPTrap request payload)."""
        payload = struct.pack("<II", trap_code & 0xFFFFFFFF, param & 0xFFFFFFFF)
        self.query(KVM_CMD_SEND_SNMP_TRAP, payload, sock=sock)

    def set_sys_location(self, location: str, sock: socket.socket | None = None) -> None:
        """0x1E SetSysLocation: Write 32-byte system location string (40-byte request payload)."""
        payload = self._encode_password() + encode_cstr(location, 32)
        self.query(KVM_CMD_SET_SYS_LOCATION, payload, sock=sock)

    def set_sys_info(
        self,
        *,
        hardware_id: str,
        dev_name: str,
        serial_number: str,
        customer: str,
        sock: socket.socket | None = None,
    ) -> None:
        """0x1F SetSysInfo: Write factory device identification strings (76-byte request payload)."""
        payload = (
            self._encode_factory_password()
            + encode_cstr(hardware_id, 16)
            + encode_cstr(dev_name, 16)
            + encode_cstr(serial_number, 16)
            + encode_cstr(customer, 20)
        )
        self.query(KVM_CMD_SET_SYS_INFO, payload, sock=sock)

    def fetch_snapshot(self, include_config: bool = True) -> dict[str, Any]:
        """Fetch live state and optionally all configuration blocks over a single TCP connection."""
        sock = self._connect()
        try:
            result: dict[str, Any] = {
                "state": self.get_state(sock=sock),
            }
            if include_config:
                result["info_ex"] = self.get_info_ex(sock=sock)
                result["ab_params"] = self.get_ab_params(sock=sock)
                result["ctrl_params"] = self.get_ctrl_params(sock=sock)
                result["relay_params"] = self.get_relay_params(sock=sock)
                result["sys_params"] = self.get_sys_params(sock=sock)
                result["eth_params"] = self.get_eth_params(sock=sock)
                result["snmp_params"] = self.get_snmp_params(sock=sock)
                result["adc_params"] = self.get_all_adc_params(sock=sock)
                try:
                    result["log_record"] = self.get_log_record(1, sock=sock)
                except EzhuKvmError:
                    result["log_record"] = None
                try:
                    result["test_ab_record"] = self.get_test_ab_record(0, sock=sock)
                except EzhuKvmError:
                    result["test_ab_record"] = None
            return result
        finally:
            try:
                sock.close()
            except OSError:
                pass


def _collect_lan_candidate_ips() -> list[str]:
    """Collect candidate IPv4 addresses from the OS ARP cache and active local /24 subnet."""
    from pathlib import Path
    import re
    import subprocess

    priority_ips: list[str] = []
    arp_ips: list[str] = []
    seen: set[str] = set()

    def _add(ip_str: str, is_priority: bool = False) -> None:
        try:
            addr = ipaddress.IPv4Address(ip_str)
        except ValueError:
            return
        if addr.is_loopback or addr.is_multicast or addr.is_unspecified:
            return
        s = str(addr)
        if s in seen:
            return
        seen.add(s)
        if is_priority:
            priority_ips.append(s)
        else:
            arp_ips.append(s)

    # 1. Linux / Home Assistant OS /proc/net/arp
    proc_arp = Path("/proc/net/arp")
    if proc_arp.is_file():
        try:
            for line in proc_arp.read_text(encoding="utf-8", errors="ignore").splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 4:
                    ip_str, mac_str = parts[0], parts[3].lower()
                    _add(ip_str, is_priority=mac_str.startswith("1e:30:6c"))
        except OSError:
            pass

    # 2. Fallback to `arp -an` (macOS / Linux)
    try:
        proc = subprocess.run(
            ["arp", "-an"],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
        for line in proc.stdout.splitlines():
            ip_match = re.search(r"\((\d+\.\d+\.\d+\.\d+)\)", line)
            if not ip_match:
                continue
            ip_str = ip_match.group(1)
            lower_line = line.lower()
            is_kvm_mac = "1e:30:6c" in lower_line or "1e:30:6c" in lower_line.replace(
                ":0", ":"
            )
            _add(ip_str, is_priority=is_kvm_mac)
    except (OSError, subprocess.SubprocessError):
        pass

    # 3. Active local /24 subnet sweep
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_sock:
            udp_sock.connect(("192.0.2.1", 80))
            local_ip = udp_sock.getsockname()[0]
        net = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
        for host in net.hosts():
            host_str = str(host)
            if host_str != local_ip:
                _add(host_str, is_priority=False)
    except OSError:
        pass

    return priority_ips + arp_ips


def discover_kvm_devices(
    port: int = DEFAULT_PORT,
    timeout: float = 0.5,
    candidate_ips: list[str] | None = None,
) -> list[tuple[str, KvmInfoEx]]:
    """Scan LAN candidates for open TCP port 1001 and verify via WAKE 0x04 GetInfoEx."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    targets = (
        list(candidate_ips)
        if candidate_ips is not None
        else _collect_lan_candidate_ips()
    )
    if not targets:
        return []

    def _probe(ip_str: str) -> tuple[str, KvmInfoEx] | None:
        client = EzhuKvmClient(host=ip_str, port=port, timeout=max(0.5, timeout))
        try:
            info = client.get_info_ex()
            return (ip_str, info)
        except Exception:
            return None

    found: list[tuple[str, KvmInfoEx]] = []
    max_workers = min(48, max(1, len(targets)))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_probe, ip): ip for ip in targets}
        for fut in as_completed(futures):
            res = fut.result()
            if res is not None:
                found.append(res)

    found.sort(key=lambda item: item[0])
    return found


__all__ = [
    "EzhuKvmClient",
    "EzhuKvmCommandError",
    "EzhuKvmError",
    "KvmAbParams",
    "KvmAdcChannelState",
    "KvmAdcParams",
    "KvmCtrlParams",
    "KvmEthParams",
    "KvmInfoEx",
    "KvmLogRecord",
    "KvmRelayParams",
    "KvmSnmpParams",
    "KvmState",
    "KvmSysParams",
    "KvmTestAbRecord",
    "bcd_to_int",
    "build_wake_frame",
    "calc_wake_crc",
    "decode_cstr",
    "decode_user_password",
    "discover_kvm_devices",
    "encode_bcd_datetime",
    "encode_cstr",
    "encode_user_password",
    "format_bcd_datetime",
    "format_ipv4",
    "format_mac",
    "int_to_bcd",
    "parse_ipv4",
    "parse_mac",
    "replace",
    "stuff_wake_bytes",
]
