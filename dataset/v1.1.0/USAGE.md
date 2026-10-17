# Loading and analysis

The examples below use Python datasets and pandas. Install datasets, pandas and pyarrow in a separate environment. The table configurations are declared in README.md; load the local package for a prepublication review or replace its path with the Hugging Face repository and approved immutable revision after release.

    from datasets import load_dataset
    from pathlib import Path
    import pandas as pd

    package = Path("/path/to/lssp-v1.1.0-package")
    outcomes = load_dataset(str(package), name="scheduler_outcomes", split="train")
    configurations = load_dataset(str(package), name="unique_configurations", split="train")
    assert len(outcomes) == 18720
    assert len(configurations) == 9360

    df = outcomes.to_pandas()
    assert df.cell_id.is_unique
    assert set(df.repetition.unique()) == {0, 1}
    key = ["source_family", "window_id", "load_region", "policy_id"]
    assert df.groupby(key).size().eq(2).all()
    selected = df.loc[(df.policy_id == "fifo") & (df.load_region == "KNEE")]
    by_source = selected.groupby("source_family")["arrival_normalized_weighted_goodput"].mean()
    print(by_source)

    checks = configurations.to_pandas()
    assert checks.deterministic_passes_equal.all()
    print(checks[["cell_id_rep0", "cell_id_rep1"]].head())

Treat the window as the unit for uncertainty analysis; do not use the two deterministic passes as independent samples. The example source averages are exploratory and do not reproduce manuscript confidence intervals.

Each canonical analysis has a separate loadable table view and an unchanged original JSON:

    import json
    reversals = load_dataset(str(package), name="pairwise_reversals", split="train")
    temporal = load_dataset(str(package), name="temporal_robustness", split="train")
    assert len(reversals) == 10890
    assert len(temporal) == 36
    original = json.loads((package / "scientific/analysis/pairwise_reversals.json").read_text())
    assert len(original["records"]) == 10890

All six originals can be supplied to the public manuscript table-data generator in the [GitHub repository](https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark/blob/main/paper/scripts/generate_phase12_tables_figures.py) at the pinned analysis commit. This exact invocation was tested with the staged package:

    python /path/to/llm-serving-scheduler-robustness-benchmark/paper/scripts/generate_phase12_tables_figures.py \
      --data-dir /path/to/lssp-v1.1.0-package/scientific/analysis \
      --out-dir /path/to/private-output-directory

It writes four manuscript table JSONs from the six hash-gated canonical analysis artifacts. It does not rederive the six analyses from matrix rows. The package makes the frozen inputs inspectable; direct alternative analyses of the eleven cell metrics are possible from scheduler_outcomes. Keep IEEE NaN values as undefined; pandas may display them as missing.

    import subprocess
    subprocess.run(["sha256sum", "-c", "checksums/v1.1.0.sha256"], cwd=package, check=True)
    subprocess.run(["python", "scripts/validate_release.py"], cwd=package, check=True)

Use revision="v1.1.0" only after the approved HF tag has actually been created. See [SCHEMA.md](SCHEMA.md) for field semantics and view-specific conversions.
