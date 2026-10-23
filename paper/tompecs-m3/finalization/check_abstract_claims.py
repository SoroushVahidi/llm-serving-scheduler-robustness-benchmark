"""Read saved results only; independently check abstract/conclusion quantities."""
import argparse
import collections
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--report", type=Path, required=True)
args = parser.parse_args()
paper = Path(__file__).resolve().parents[1]
hashes = json.loads((paper / "evidence/input-hashes.json").read_text())

def read(name):
    raw = gzip.decompress((paper / "evidence/inputs" / (name + ".json.gz")).read_bytes())
    assert hashlib.sha256(raw).hexdigest() == hashes[name + ".json"]["sha256_uncompressed"]
    return json.loads(raw)

rows = read("c01-absolute_metrics")
assert len(rows) == 5760
assert sum(r["metrics"]["num_completed"] for r in rows) == 1152000
assert all(r["metrics"]["num_completed"] == 200 and r["metrics"]["num_unfinished"] == 0 for r in rows)
assert len({r["window"] for r in rows}) == 120
assert len({r["policy"] for r in rows}) == 4
paired = collections.defaultdict(dict)
groups = collections.defaultdict(list)
for row in rows:
    paired[row["condition_id"], row["profile"]][row["policy"]] = row
    groups[row["source"], row["profile"], row["policy"]].append(row["metrics"])
assert len(paired) == 1440
assert all(v["chunked_fcfs_c01"]["metrics"] == v["decode_first_c01"]["metrics"] for v in paired.values())
journal_hash_differences = sum(v["chunked_fcfs_c01"]["journal_sha256"] != v["decode_first_c01"]["journal_sha256"] for v in paired.values())
metrics = ["mean_latency", "token_throughput", "p95_latency", "mean_ttft", "arrival_normalized_weighted_goodput"]
means = {k: {m: math.fsum(r[m] for r in v) / len(v) for m in metrics} for k, v in groups.items()}
assert all(len(v) == 240 for v in groups.values())
with (paper / "supplement/c01-source-capacity-means.csv").open() as stream:
    for row in csv.DictReader(stream):
        key = row["source"], row["profile"], row["policy"]
        assert all(math.isclose(float(row[m]), means[key][m], rel_tol=1e-12, abs_tol=1e-12) for m in metrics)
effects = []
for source, profile in sorted({(s, k) for s, k, p in means}):
    a, b = means[source, profile, "chunked_fcfs_c01"], means[source, profile, "slo_gated_c01"]
    effects.append(dict(source=source, profile=profile,
        latency_reduction_percent=100 * (1 - b["mean_latency"] / a["mean_latency"]),
        throughput_reduction_percent=100 * (1 - b["token_throughput"] / a["token_throughput"]),
        mean_window_p95_increase_percent=100 * (b["p95_latency"] / a["p95_latency"] - 1)))
assert len(effects) == 6
assert [round(f(e["latency_reduction_percent"] for e in effects), 1) for f in [min, max]] == [11.3, 34.0]
assert [round(f(e["throughput_reduction_percent"] for e in effects), 2) for f in [min, max]] == [1.65, 4.01]
assert [round(e["mean_window_p95_increase_percent"], 2) for e in effects if e["source"] == "burstgpt"] == [3.72, 18.97]
reversals = read("c01-reversals")
by_axis = collections.defaultdict(lambda: dict(groups=0, total=0, reversals=0))
for row in reversals:
    summary = by_axis[row["axis"]]
    summary["groups"] += 1
    summary["total"] += row["total"]
    summary["reversals"] += row["reversals"]
assert len(reversals) == 26136
source_axes = [by_axis["source_mean"]]
assert source_axes and all(v["reversals"] == 0 for v in source_axes)
assert sum(v["total"] for v in source_axes) == 2376
assert by_axis["window"]["reversals"] > 0
assert by_axis["metric"]["reversals"] > 0
report = dict(status="PASS", cells=len(rows), completed_request_executions=1152000,
    matched_metric_equivalences=len(paired), differing_compressed_journal_hashes=journal_hash_differences,
    journal_caveat="Different compressed hashes alone do not identify ordering differences; terminal equality was independently checked against all raw terminal records by check_c01.py.",
    source_capacity_effects=effects, reversal_summary=dict(by_axis), experiments_executed=0)
args.report.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
