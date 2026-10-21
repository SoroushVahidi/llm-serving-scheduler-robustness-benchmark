#!/usr/bin/env python3
"""Read-only independent revalidation. Print to stdout; no GPU/framework imports."""
import argparse
import json
from pathlib import Path
from robustbench.mgpu05.offline import analyze

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('execution_directory', type=Path)
    args = p.parse_args()
    try:
        result = analyze(args.execution_directory)
    except FileNotFoundError as exc:
        result = dict(acceptance='NOT_VERIFIED', error=str(exc), error_type=type(exc).__name__)
    except (ValueError, KeyError, TypeError) as exc:
        result = dict(acceptance='FAIL', error=str(exc), error_type=type(exc).__name__)
    print(json.dumps(result, indent=2, allow_nan=False))
    raise SystemExit(0 if result['acceptance']=='PASS' else 1)
