# RANKING_PORTABILITY_CALIBRATION_CHARACTERISTICS.md

Descriptive calibration provenance for the Phase-11 FIFO-only run. This document is not a scheduler-ranking result section.

## Region pressure summary

| Region | Load factor | min | max | avg | Interpretation |
|---|---:|---:|---:|---:|---|
| LOW | 0.5 | 0.0 | 0.0 | 0.0 | no SLO violation |
| PRE_KNEE | 0.8 | 0.0 | 0.0 | 0.0 | no SLO violation |
| KNEE | 1.0 | 0.0 | 0.01 | 0.002625 | transitional region |
| POST_KNEE | 1.1 | 0.0 | 0.075 | 0.0132916667 | moderate pressure |
| OVERLOAD | 1.2 | 0.0 | 0.23 | 0.0332083333 | elevated pressure |
| HIGH_PRESSURE | 1.5 | 0.005 | 0.845 | 0.148375 | pressure-dominant region |

## Calibration facts to preserve

- FIFO-only run over the frozen 120-window manifest.
- 720 total calibration cells; 720 valid.
- 0 failed / 0 missing / 0 duplicate.
- `PHASE11_CALIBRATION_VALID = YES`
- `CALIBRATION_DETERMINISTIC = YES`

## Important descriptive provenance

The following counts are preserved as descriptive calibration provenance only, not comparative scheduler results:

- Azure zero-completion region records = 107
- Bailian/Qwen zero-completion records = 101
- BurstGPT zero-completion region records = 93
- Total = 301

Do not reinterpret these counts as a comparative scheduler ranking or performance claim.
