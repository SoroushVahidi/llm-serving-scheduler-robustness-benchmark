"""Shared infrastructure for real-LLM API calibration harnesses (Phase 4+).

Provider-specific scripts under scripts/run_*_api_calibration.py build on
calibration_common so that every provider produces the same output schema
(requests.jsonl, summary.json/md, aggregate_by_*.csv, manifest.json,
run_config.json, reproducibility.md).
"""
