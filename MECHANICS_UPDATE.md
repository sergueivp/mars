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

## Overweight + Transport Layer
- MU budget is spacecraft cargo capacity proxy.
- Overweight handling:
  - `MU_total / MU_budget <= 1.00`: normal
  - `1.00 < ratio <= 1.15`: accepted with transport risk
  - `ratio > 1.15`: invalid submission (`Overweight exceeds 15% limit`)
- Transport Feasibility (`TF`) in `[0..100]`:
  - Overweight penalty: `TF_penalty = 4 * overweight_pct`
  - Status bands:
    - `TF >= 70`: OK
    - `40 <= TF < 70`: AT RISK
    - `TF < 40`: FAILED
- `AT RISK` applies deterministic startup penalties:
  - reduced reserve benefit for `item_19` and `item_20` (50%)
  - ES start stress equivalent to PS_0=92

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

## Deterministic Fixture Checks
- Added built-in deterministic fixtures via `runDeterministicFixtures()`.
- Run automatically when URL contains `?sim-fixtures=1`.
- Includes checks for:
  - no primary power fail day 10
  - surface no-effective-shielding fail day 27
  - printer deficit no-completion path
  - adequate printer completion path
  - overweight acceptance in +15% band
  - invalid submission above +15%
  - TF status mapping for `< 40`.
