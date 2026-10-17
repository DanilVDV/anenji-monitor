# Anenji Monitor

Single-file Python 3 web monitor/control service for an Anenji solar inverter on OpenWrt with Saihang BLE BMS battery telemetry.

Current stable version in this repository: **v2.11.26**.

## Verified development hardware

This project is **running, tested and actively debugged on the following real installation**:

- **Inverter:** ANENJI **ANJ-6200-48V-48PL-WIFI**, 48 V battery system, 6.2 kW class.
- **Batteries:** ANENJI **ANJ-24V100AH** LiFePO4 battery modules.
- **Battery arrangement used by the project:** four 24 V / 100 Ah modules forming the approximately 48/52 V inverter battery bank; BMS units are monitored individually.
- **BMS telemetry:** Saihang SH-series BMS, polled over **Bluetooth Low Energy** from OpenWrt.
- **OpenWrt hardware:** **RMS7688A** development/router board used as the local controller for the inverter monitor, BLE polling and HTTP API.
- **Inverter link:** RS485 / Modbus RTU, typically `/dev/ttyS2`, 9600 baud, slave 1 on the tested installation.
- **Web/API service:** Python 3 service on OpenWrt, default HTTP port `8088`.

The companion BMS project documents the low-level BLE reader as tested on the **MT7688AN/OpenWrt** platform. Hardware revisions, UART numbering, Bluetooth adapters and inverter firmware may differ, so register mappings and device paths should be verified before enabling writes.

## What it does

- Polls the inverter over Modbus/RS485.
- Shows PV, grid, load, inverter and battery energy flow in a web UI.
- Polls Saihang BMS packs over BLE using `saihang-bms`.
- Tracks active/idle/suspect/offline battery packs.
- Estimates remaining runtime to a configured battery reserve.
- Detects battery discharge with hysteresis and on/off delays.
- Can notify the user on sustained discharge, either only when the grid is absent or on any discharge (including scheduled discharge while grid is present).
- Exposes JSON APIs such as `/api/summary`, `/api/bms` and `/api/cache`.

## Hardware / topology used during development

```text
ANJ-6200-48V-48PL-WIFI inverter
          |
          | RS485 / Modbus RTU
          v
RMS7688A + OpenWrt
   |              |
   | BLE          | HTTP / LAN / Wi-Fi
   v              v
Saihang BMS     Web UI / external clients
(ANJ-24V100AH)
```

The tested battery installation uses four Saihang-equipped 8-cell / 24 V modules. The monitor uses `ANENJI_BMS_TOPOLOGY=individual` and treats every BMS as a separate pack for health/participation analysis while inverter-side voltage/current represents the whole 48 V battery bus.

## Related projects

This repository is the central inverter monitor/API component of a small group of related projects:

### [`DanilVDV/openwrt-saihang-bms`](https://github.com/DanilVDV/openwrt-saihang-bms)

Standalone C CLI and OpenWrt package for Saihang SH-series BLE BMS. It talks directly to Linux Bluetooth MGMT/raw ATT and outputs JSON. `anenji-monitor` uses this tool through `ANENJI_BMS_CMD=saihang-bms` and polls configured BMS MAC addresses with the CLI `read` command.

**Compatibility check:** the current BMS CLI supports JSON output, the `read <MAC>` command and the global `-T/--io-timeout` option used by this monitor. The two projects are aligned for the current BMS polling path.

### [`DanilVDV/anenji-rgb-display`](https://github.com/DanilVDV/anenji-rgb-display)

External 64×32 HUB75 RGB information display built around Arduino Mega 2560 + ESP8266. It displays solar production, grid/load power, battery charge/discharge, SOC, clock and estimated autonomy.

The ESP8266 bridge polls an RMS/OpenWrt HTTP endpoint and forwards a compact UART packet to the Mega.

**Compatibility status:** the RGB-display firmware currently expects a compact `/api/rgb` endpoint. The stable `anenji-monitor` `main` file in this repository is still **v2.11.26** and exposes `/api/summary`, but not `/api/rgb`. The RGB-display repository contains later experimental server snapshots (`v2.11.27` through `v2.11.32`) that add and refine `/api/rgb`, including SOC/time/grid-present handling. Those server-side changes should be reviewed and promoted into this repository before the RGB display is considered fully synchronized with `main`.

In other words: **Saihang BMS integration matches the current monitor; RGB display integration is one server-version step ahead of this repository and still needs to be merged back here.**

## Run

```sh
python3 /root/anenji/anenji_web.py
```

Default HTTP port is `8088`.

Open:

```text
http://<openwrt-ip>:8088/
```

Summary API:

```sh
curl -s http://127.0.0.1:8088/api/summary
```

## Important OpenWrt environment settings

Example values used for this installation:

```sh
ANENJI_PORT=/dev/ttyS2
ANENJI_BAUD=9600
ANENJI_SLAVE=1
ANENJI_HTTP_PORT=8088
ANENJI_POLL_SEC=5

ANENJI_BMS_ENABLE=1
ANENJI_BMS_CMD=saihang-bms
ANENJI_BMS_TOPOLOGY=individual
ANENJI_BMS_EXPECTED_PACKS=4
ANENJI_BMS_PARALLEL=2
ANENJI_BMS_RETRY_FAILED=1
ANENJI_BMS_AUTO_ON_DISCHARGE=1
ANENJI_BMS_DISCHARGE_POLL_SEC=60
ANENJI_BMS_POST_RECOVERY_POLLS=3
ANENJI_BMS_POST_RECOVERY_POLL_SEC=20

ANENJI_BATTERY_RESERVE_SOC=15
ANENJI_ETA_AVG_SEC=600
ANENJI_BMS_ACTIVE_CURRENT_A=1.0
ANENJI_BMS_INACTIVE_CYCLES=3

ANENJI_DISCHARGE_POWER_ON_W=150
ANENJI_DISCHARGE_POWER_OFF_W=50
ANENJI_DISCHARGE_ON_DELAY_SEC=10
ANENJI_DISCHARGE_OFF_DELAY_SEC=20
ANENJI_DISCHARGE_REQUIRE_GRID_ABSENT=0

ANENJI_ATTENTION_ENABLE=1
ANENJI_ATTENTION_ON_DELAY_SEC=120
ANENJI_ATTENTION_OFF_DELAY_SEC=60
ANENJI_ATTENTION_BATTERY_POWER_W=150
ANENJI_ATTENTION_REQUIRE_GRID_ABSENT=1

ANENJI_GRID_PRESENT_V=180
```

Do **not** commit private BLE MAC addresses, passwords, tokens or other installation-specific secrets to a public repository. Keep those in `/etc/init.d/anenji`, an ignored local environment file, or another private configuration source.

## Discharge detection

The discharge detector is independent of the attention/notification policy.

```sh
ANENJI_DISCHARGE_REQUIRE_GRID_ABSENT=0
```

means that a real battery discharge can be detected even while grid voltage is present.

The detector uses hysteresis and delays:

```sh
ANENJI_DISCHARGE_POWER_ON_W=150
ANENJI_DISCHARGE_POWER_OFF_W=50
ANENJI_DISCHARGE_ON_DELAY_SEC=10
ANENJI_DISCHARGE_OFF_DELAY_SEC=20
```

## User attention policy

v2.11.26 added:

```sh
ANENJI_ATTENTION_REQUIRE_GRID_ABSENT=1
```

- `1` — alert only when sustained battery discharge occurs while the grid is absent.
- `0` — alert on sustained battery discharge even when grid is present, including planned/scheduled inverter discharge.

This setting is independent of `ANENJI_DISCHARGE_REQUIRE_GRID_ABSENT`.

## Runtime / ETA calculation

The remaining time estimate combines BMS energy information with inverter battery power.

BMS data provides the remaining/design energy and pack participation. Only packs classified as `active` contribute to the active energy pool. A configured reserve SOC is subtracted from available energy.

The discharge/charge rate comes from inverter-side battery voltage/current and is smoothed over the ETA window, by default:

```sh
ANENJI_ETA_AVG_SEC=600
```

Conceptually:

```text
ETA to reserve ≈ active usable energy to reserve / averaged battery discharge power
```

Useful `/api/summary` fields include:

```text
state
pv_w
load_w
grid_w
grid_voltage_v
grid_present
battery_voltage_v
battery_current_a
battery_power_w
battery_avg_power_w
discharge_detected
discharge_power_w
active_remaining_wh
active_usable_to_reserve_wh
eta_to_reserve_sec
reserve_soc_pct
bms_active
bms_online
bms_total
active_packs
suspect_packs
offline_packs
battery_problem
battery_problem_level
attention_condition
attention_required
attention_pending
attention_require_grid_absent
```

## External display / dashboard

For a generic external dashboard connected to the current stable `main`, use:

```sh
curl -s http://127.0.0.1:8088/api/summary
```

A display can refresh this endpoint every few seconds and render only the fields it needs.

The dedicated `anenji-rgb-display` project currently targets `/api/rgb`; see the compatibility note in **Related projects** above.

## BMS behavior

The service supports automatic BMS refresh during battery discharge and additional post-recovery refreshes. It also tracks participation so an inactive battery pack does not incorrectly inflate the ETA calculation.

Typical settings:

```sh
ANENJI_BMS_AUTO_ON_DISCHARGE=1
ANENJI_BMS_DISCHARGE_POLL_SEC=60
ANENJI_BMS_POST_RECOVERY_POLLS=3
ANENJI_BMS_POST_RECOVERY_POLL_SEC=20
```

## Version notes

### v2.11.26

- Added `ANENJI_ATTENTION_REQUIRE_GRID_ABSENT`.
- Attention can now be configured independently from discharge detection.
- With `ANENJI_ATTENTION_REQUIRE_GRID_ABSENT=0`, planned battery discharge with grid present can still trigger user attention after the configured delay.
- `/api/summary` exposes `attention_require_grid_absent` and `attention_grid_ok`.

### v2.11.25

- Added `ANENJI_DISCHARGE_REQUIRE_GRID_ABSENT`.
- Default `0` allows discharge detection while grid voltage is present.

### v2.11.24

- Added shared configurable discharge detector with power hysteresis and on/off delays.

### v2.11.23

- Fixed horizontal grid/load flow connector layout.
- Battery arrow direction follows battery current sign: negative = discharge toward inverter; positive = charging toward battery.

## Repository layout

```text
anenji_web.py                 Current stable application
archive/                      Versioned snapshots
README.md                     Project notes and installation/behavior description
CHANGELOG.md                  Version history
.gitignore                    Local/runtime files not committed
```
