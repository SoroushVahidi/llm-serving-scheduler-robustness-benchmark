#!/usr/bin/env bash
set -euo pipefail
python -B -m pytest -q -p no:cacheprovider tests/test_anwg_metric.py tests/test_ranking_portability_analysis_stats.py tests/test_ranking_portability_analysis_ranking.py tests/test_ranking_portability_analysis_reversal.py tests/test_ranking_portability_analysis_sample_complexity.py
(cd dataset/v1.1.0 && python -B scripts/validate_release.py)
