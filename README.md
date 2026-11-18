# <img src="icon.png" width="48" align="absmiddle" alt="INTEGRAL"> EZHU KVM48 Power System (`ezhu_kvm`) — Home Assistant Custom Integration

Complete Home Assistant integration for the **ЕЖУ И 14000 Б 48-160-хД** DC power supply system with the **КВМ48-20** controller (`INTEGRAL`, firmware `VPMA.758725.037`), communicating directly over **TCP Port 1001** using the binary **WAKE protocol**.

Exposes **100% of device parameters**:
- Every **read-only** measurement, status, bitmask, and alarm is exposed as a `sensor` or `binary_sensor` entity (62 read-only entities).
- Every **read/write** configuration parameter is exposed as a modifiable `number`, `select`, `switch`, or `text` entity (122 read/write entities).
- Every **remote command / action** is exposed as a `button` entity (9 action buttons).

---

## Exposed Entities Summary (193 Entities Total)

| Platform | Count | Access | Parameters Covered |
| --- | ---: | --- | --- |
| `sensor` | **25** | **Read-Only** | `U load`, `I ab1`, `I ab2`, `I ab Total`, `I load`, `P load`, `I3`, `U ph1`, `U ph2`, `U ph3`, `T ab`, `T cu`, `Work Mode`, `Ucontrol`, `Faults Bitmask`, `Relay State Bitmask`, `Access Level`, `Controller Clock (RTC)`, `Next Scheduled Battery Test`, `T ab / T cu CRC Errors`, `Firmware Version`, `Bootloader Version`, `Telemetry Log Head Index`, `Battery Test Log Count` |
| `binary_sensor` | **37** | **Read-Only** | All 10 Alarms (`A1 AC Input` .. `A10 Fire`), `Battery Discharge Test Active`, `T ab / T cu Sensor Present`, 8 `Relay Output Bits 0..7`, 16 `Fault Flag Bits 0..15` |
| `number` | **43** | **Read/Write** | 10 `TABParams` (`CellCount`, `dUdT`, `U20C`, `Qab`, `Icharge`, `dT_IU`, `test_Tdischarge`, `test_Umin`, `test_Ttesting`, `test_Tarchivation`), 13 `TCtrlParams` (`Umanual`, `Umax`/`Hyst`, `Umin`/`Hyst`, `TdisconAB`/`Hyst`, `TmaxAB`/`Hyst`, `UdisconNPL`/`Hyst`, `UdisconAB`/`Hyst`), `TSysParams` (`Period_Archive`, `Active_Interface`), `TEthParams.MediaType`, `TSNMPParams.TrapEventMask`, 16 `TADCParams` (`Offset` & `Gain` for `Ch 0..7`) |
| `select` | **1** | **Read/Write** | `TABParams.regime` (`Auto U`, `Auto IU`, `Manual U`, `Manual IU`) |
| `switch` | **51** | **Read/Write** | `Battery Discharge Test` (`0x19`), `System Audible Alarm (Voice)` (`0x10`), `Ethernet DHCP Enabled` (`0x12`), 8 `ADC Ch 0..7 Enabled` (`0x08`), 40 `TRelayConfiguration` alarm routing matrix switches (`Relay 1..3` & `Sound` × `Alarms A1..A10`, `0x0E`) |
| `text` | **27** | **Read/Write** | `SysLocation` (`0x1E`), `Hardware ID`, `Device Name`, `Serial Number`, `Customer` (`0x1F`), `System User Password (6-digit PIN)` (`0x10`), `Ethernet HostName / MAC / IP / Gateway / NetMask / DNS1 / DNS2` (`0x12`), `SNMP Community Name` & `Trap Servers 1..5` (`0x14`), 8 `ADC Ch 0..7 Labels` (`0x08`) |
| `button` | **9** | **Write Action** | `Refresh All Parameters`, `Sync Controller Clock (0x06)`, `Start Battery Discharge Test (0x19)`, `Stop Battery Discharge Test (0x19)`, `Clear Telemetry Archive Log (0x16)`, `Clear Battery Test Log (0x18)`, `Send Test SNMP Trap (0x1D)`, `Reboot Controller (0x1B)`, `Restore Factory Defaults (0x1A)` |

---

## Installation & Automatic Discovery

1. Copy `custom_components/ezhu_kvm` into your Home Assistant `config/custom_components/ezhu_kvm` directory (or install via HACS as a custom repository).
2. Restart Home Assistant.
3. **Automatic DHCP / ARP Discovery**:
   - Home Assistant automatically detects any КВМ48-20 controller on the LAN (via the factory Atmel SAM7X MAC prefix `1E:30:6C:*` or hostname `kvm*`) and verifies it over TCP port `1001` (`0x04 GetInfoEx`).
   - Discovered controllers appear automatically under **Settings → Devices & Services → Discovered** with a one-click **Configure** button.
4. **Manual Setup / Active LAN Scan**:
   - Or go to **Settings → Devices & Services → Add Integration → EZHU KVM48 Power System**:
   - **Host / IP Address**: Leave empty to automatically scan the local network for TCP port `1001` controllers, or enter your controller's IPv4 address (e.g., `192.168.0.50`)
   - **TCP Port**: `1001`
   - **Admin Password**: `555555`
   - **Factory Password**: `434410`
   - **Polling Interval**: `10` seconds
