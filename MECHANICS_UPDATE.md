# Mechanics Update

## Construction Window (Sol 0-60)
- `item_04` (Excavator) draws 5 kW only at checkpoints `0, 30, 60`.
- `item_07` (Printer) draws 4 kW only at checkpoints `0, 30, 60`.
- After Sol 60, both stop drawing power.

## Printer Completion Rules
- Printer shielding can complete at Sol 30 if deficit at Sol 30 is `<= 1.0 kW`.
- If not completed at Sol 30, second chance at Sol 60 with same deficit condition.
- Shielding effects apply only after completion checkpoint.

## Excavator Readiness Rules
- Excavator readiness is checked at Sol 60.
- Ready if deficit at Sol 60 is `<= 2.0 kW`.
- If not ready, excavator post-build subsurface/berm benefits do not activate.

## Surface Radiation Emergency Logic
- Habitation strategy controls exposure (no automatic subsurface benefit from owning enabler items).
- If strategy is `Surface` and printer is not completed by Sol 60, hard failure is forced at Sol 27:
  - `Surface radiation overload (no effective shielding)`

## No Primary Power Rule
- If neither `item_01` nor `item_02` is selected:
  - Hard failure at Sol 10
  - Reason: `No primary power source (cannot run life support)`

## Transport Tolerance Adjustment – Integer Safe 20% Soft Band
- MU budget is spacecraft cargo capacity proxy.
- Compute soft tolerance limit with integer-safe rounding:
  - `soft_limit = ceil(1.20 * MU_budget)`
- Transport result:
  - if `MU_total <= MU_budget`: `OK`
  - if `MU_budget < MU_total <= soft_limit`: `AT_RISK`
  - if `MU_total > soft_limit`: `FAILED` at Sol 0
- Overweight is never an invalid submission by itself.
- Invalid submission remains only for:
  - not exactly 4 items
  - habitation gating fail
  - hard dependency fail
- `AT_RISK` still applies deterministic startup penalties:
  - reduced reserve benefit for `item_19` and `item_20` (50%)
  - ES start stress equivalent to PS_0=92

## Habitation Strategy Effects
- Habitation changes only three mechanical domains:
  - radiation exposure
  - thermal load added to power draw
  - base mechanical wear

### Radiation multipliers
- Surface: `1.00`
- Partial subsurface: `0.65`
- Fully subsurface: `0.35`

Radiation multiplier is driven by selected habitation strategy only.
Owning enabler items does not automatically grant subsurface radiation protection.

### Thermal load
- Base thermal load:
  - Surface: `2.0 kW`
  - Partial: `1.0 kW`
  - Full: `0.5 kW`
- Thermal Regulation (`item_11`) reduction:
  - Surface: `-1.0 kW`
  - Partial: `-0.6 kW`
  - Full: `-0.3 kW`
- Thermal load is clamped to a minimum of `0.2 kW`.

This thermal load is added to checkpoint draw at every checkpoint.

### Habitation wear (ER)
- Added deterministic wear per 30-sol block:
  - Surface: `+2`
  - Partial: `+1`
  - Full: `+0`

This stacks with existing wear from dust, seals, and power stress.

### Surface emergency rule
- If strategy is Surface and printer shielding is not completed by Sol 60:
  - hard failure at Sol 27
  - reason: `Surface radiation overload (no effective shielding)`

Owning excavator/rover does not bypass this when Surface is selected.

### Playback and feedback visibility
- Mission playback now shows at each checkpoint:
  - habitat status line with icon
  - radiation risk as LOW / MEDIUM / HIGH
- Sol 0 event added:
  - `Habitation plan selected: Surface / Partial / Full.`
- Feedback summary includes a one-line habitation consequence statement.

## Oxygen/Water Duration Feedback
- Oxygen:
  - with `item_09`: `continuous`
  - without `item_09`: estimated `until Sol 45` and hard-fail path
- Water:
  - with `item_08`: `continuous`
  - without `item_08` but with `item_19`: finite estimate
    - `Surface`: until Sol 105
    - `Partial/Fully subsurface`: until Sol 120
  - without both `item_08` and `item_19`: `until Sol 90` hard-fail path
- Late mission oxygen warning added when `item_09` is used without `item_15`.

## Student-Facing Output Additions
- Transport check: `OK / AT RISK / FAILED`
- Power summary at Sol 180:
  - produced, needed, margin
- Estimated oxygen duration
- Estimated water duration
- Two weakest areas (plain language)
- Two diagnostics (plain language, no item IDs)

## Fail-Day and Power Consistency Patch
- Non-transport failures are no longer allowed at Sol 0.
  - Transport failure can still fail at Sol 0.
  - Other failure checks are floored to Sol 30+ unless explicitly defined (for example Surface radiation emergency at Sol 27).
- Reliability hard-failure now uses internal ER timeline (`0..100`) instead of BC `0..5` scoring.
  - BC display remains in `0..5`, derived from ER at Sol 0 (`ER/20`).
- Power draw now includes always-on base load:
  - `core_load = 4.0 kW`
  - plus habitation thermal load
  - plus active item draws at each checkpoint.
- Power summary (Sol 180) and playback values now use the same source:
  - `powerTimeline[{sol, genKW, drawKW, netKW, deficit}]`
- Critical-event header is now mapped by failure category:
  - Transport / Energy Stability / Radiation / Water-Oxygen / Repairs & Breakdown Risk.

## Deterministic Fixture Checks
- Added built-in deterministic fixtures via `runDeterministicFixtures()`.
- Run automatically when URL contains `?sim-fixtures=1`.
- Includes checks for:
  - no primary power fail day 10
  - surface no-effective-shielding fail day 27
  - printer deficit no-completion path
  - adequate printer completion path
  - budget 12: totals 12/14/15/16 map to OK/AT_RISK/AT_RISK/FAILED
  - budget 10: totals 11/12/13 map to AT_RISK/AT_RISK/FAILED
  - overweight failure returns NON-VIABLE at Sol 0 (not INVALID).
