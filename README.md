# Anenji Monitor

Single-file Python 3 web monitor/control service for an Anenji solar inverter on OpenWrt with four Saihang BLE BMS battery packs.

Current version: **v2.11.26**.

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

- Anenji inverter connected through RS485/Modbus.
- Four Saihang 8-cell / 24 V battery modules arranged for an approximately 52 V inverter battery system.
- BMS topology: `individual`.
- Expected BMS pack count: 4.

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

For an external display, use one request and avoid duplicating battery logic in the display client:

```sh
curl -s http://127.0.0.1:8088/api/summary
```

A display can refresh this endpoint every few seconds and render only the fields it needs.

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
.gitignore                    Local/runtime files not committed
```
