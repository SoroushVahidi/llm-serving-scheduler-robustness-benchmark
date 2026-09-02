# Phase-11 prelaunch freeze template

This template documents the required inputs that must be hashed before any real Phase-11 calibration execution.

Do not fill outcome-dependent values in this task. This document is a freeze checklist, not an execution log.

## Required frozen inputs

- integration branch SHA: <fill before execution>
- 120-window freeze hash: <fill before execution>
- calibration implementation hash: <fill before execution>
- candidate-factor grid: <fill before execution>
- target region definitions: <fill before execution>
- FIFO policy definition: <fill before execution>
- simulator/config hash: <fill before execution>
- validator hash: <fill before execution>

## Required schema-level invariants

- exactly six regions: `LOW`, `PRE_KNEE`, `KNEE`, `POST_KNEE`, `OVERLOAD`, `HIGH_PRESSURE`
- identical rule for all sources/windows
- no comparative scheduler outcome data in the calibration output schema
- no scheduler policy other than the frozen FIFO reference may be inspected during calibration

## Execution gate

Execution is allowed only when all fields above are set and all hashes match the frozen identity of the current branch and manifest.
