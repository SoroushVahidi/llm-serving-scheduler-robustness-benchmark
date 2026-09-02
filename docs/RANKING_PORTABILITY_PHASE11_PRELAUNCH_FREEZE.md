# Phase-11 prelaunch freeze

This freeze is recorded before real calibration execution begins.

## Contract summary

- `lambda_ref`: the FIFO inter-arrival compression factor at which `fifo.slo_violation_rate` first crosses the frozen 0.5% threshold (`0.005`).
- FIFO pressure statistic used: `slo_violation_rate` from the simulator's `RunMetrics`, computed with the single reference policy `fifo` and the frozen simulator config.
- six regions: `LOW` = 0.5×, `PRE_KNEE` = 0.8×, `KNEE` = 1.0×, `POST_KNEE` = 1.1×, `OVERLOAD` = 1.2×, `HIGH_PRESSURE` = 1.5×.
- factor-selection rule: the six multipliers map directly to the six regions; they are not searched after seeing results. The calibration target is a fixed region grid.
- deterministic tie rule: if a value lands exactly on a tie, prefer the earlier factor in canonical region order (`LOW`, `PRE_KNEE`, `KNEE`, `POST_KNEE`, `OVERLOAD`, `HIGH_PRESSURE`).
- two regions may not select the same factor: each region is assigned its own fixed multiplier from the frozen grid, and there is no optimizer that reassigns two regions to the same candidate.
- unreachable-target behavior: nearest valid boundary candidate is used with explicit interpolation/edge status, without changing the predeclared grid.
- zero-completion behavior: zero completion is recorded as a valid zero-completion assignment and is never silently reinterpreted.
- simulator-failure behavior: a simulator failure emits a schema-valid failure status and prevents the record from being claimed as valid calibration output.

## Frozen identity

- branch SHA: `f67c65f2f0b6cef661701e75c14f0a7e6868da4d`
- Phase-10 window hash: `0d1aa06ccbee352207327ea369ae75f12e91c0cda006c813a41b381effd29eef`
- compact index hash: `d78ec1087fedae02174ca093a9860c70468be336ccb1d7e6de756c81ba331e53`
- aggregate prelaunch-freeze SHA-256: `e2564ea9484190832de50f63173c4b73ae054d6ae7008bb4ff6648c8dc917f7b`
- calibration implementation hash: `030ea1760ecc4797ab7a1bab48f8a7af3f59ddba54905d571ece6ef5cb1c8804`
- build script hash: `45e4d7c2d7228ac5f7f421a99f711735f8de0affd3fb97c97da0138a9b19a39c`
- calibration plan hash: `01e403daed3ad0fc2ea92bfd042457198d47740c7ea6bc51edc953268bfd1593`
- candidate factor grid hash: `217e99b5b7ab3e25ca2d89eb29adc997c15a7d5684f05bb339ce301255ae2cd0`
- six-region definition hash: `139be6d2ad6db9bbea8a642ec420ff29228f74b5ab2105fdd520acbbae73f533`
- FIFO policy implementation hash: `431171492d5174caa1358cf2adf76bf699ffb76f252a602ee9ec5ce69ef61381`
- simulator implementation/config hash: `a4fa693aa24c76e87bf0fc023ec88086f727dd926d89b586648c75c182ed1b5e`
- validator/schema hash: `dfb4b7815047852c5bf8d626daed1073380a844158ca54c76d030e47ae28e2b3`

`PHASE11_PRELAUNCH_CONTRACT = SATISFIED`
