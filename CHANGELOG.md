# Changelog

## v2.11.26
- Added `ANENJI_ATTENTION_REQUIRE_GRID_ABSENT` to independently control whether user attention requires grid absence.
- `0` permits alerts for any sustained battery discharge, including scheduled discharge with grid present.
- Added `attention_require_grid_absent` and `attention_grid_ok` to `/api/summary`.

## v2.11.25
- Added `ANENJI_DISCHARGE_REQUIRE_GRID_ABSENT`; default is `0`.

## v2.11.24
- Added shared configurable discharge detector with on/off thresholds and delays.

## v2.11.23
- Fixed grid/load horizontal flow rendering and battery charge/discharge arrow direction.
