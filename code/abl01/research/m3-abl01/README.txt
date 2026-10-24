M3-ABL01 — controlled SLO waiting-order intervention
Read PROTOCOL.txt, PROOF.txt and DEDUPLICATION.txt before interpreting artifacts.

The new control is implemented as exactly one expression change in a copy of
original policies.py. Engine/referee originals are byte-preserved. Because all
candidate work fits under exact C01-FULL settings,1440 existing chunked-FCFS
trajectories are proven-equivalent. This is saved-evidence reconstruction and
analysis, NOT a new1440-cell simulation. Every derived journal preserves actual
control span order and passes original independent referee/terminal checks.

Tests:
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=research/m3-abl01 python -m pytest -q -p no:cacheprovider research/m3-abl01/test_ablation.py research/m3-abl01/frozen_c01/test_contract.py

Preparation only after frozen Git commit:
python research/m3-abl01/prepare.py LOCAL_C01 NEW_PAYLOAD --remote-base REMOTE_C01 --remote-root NEW_ROOT
python research/m3-abl01/campaign.py NEW_PAYLOAD --base LOCAL_C01 --pilot NEW_PILOT_JSON

On Wulver, exact code archive and payload are staged into a NEW project root.
Verify code/files/manifest, original C01 origin hashes, tests/pilot report and
quota. Freeze execution.json with statusPASS, source/manifest/code/validation
hashes. Inspect current jobs and acquire durable submission lock. Only then:
sbatch --export=ALL,ABL01_ROOT=NEW_ROOT --output=NEW_ROOT/logs/slurm-%j.out --error=NEW_ROOT/logs/slurm-%j.err NEW_ROOT/code/research/m3-abl01/experiment.sbatch
Never run this command twice; no automatic resume/requeue/overwrite is supported.
Monitor only approximately120s after submission, then stop and hand off.

Completion checks: sacct exit0 plus root/slurm.exit=0, complete.json,
reuse-complete.json, analysis/verification.json PASS; exact1440 unique derived
controls and no partial directories; all result/journal/analysis hashes match.
Look for failures/censoring, not just successful SLURM acceptance. Inspect stdout
PAIR_VALIDATED1..1440 plus COMPLETE and stderr. Missing/rejected cells require
investigation rather than automatic resubmission. Original evidence is read-only.

Required later independent analysis review:
paired-differences.csv: control minus originalSLO, primary11+additional2 metrics.
source-condition-means.csv:40windows per source/region/capacity; preserve all
sources and six regions, tails, throughput and null/adverse effects.
rankings.csv/policy-comparisons.csv/reversal-counts.csv: distinguish original-vs-
ablated panels from cross-source and cross-condition portability; exact strict
10% loser-relative margin BOTH endpoints. Report numerator/eligible/total/missing.
All40 windows required for source means; mean-window p95 is not pooled p95.
telemetry.csv: urgency/admission and same-state differential; zero activation
cannot be inferred just from performance. Deadline counts/denominators are raw
completed/all-arrival quantities, distinct from weighted ANWG. Independently
reconcile endpoint tables with saved records and exact margin arithmetic.
No statistical-replicate or physical-GPU interpretation; no manuscript revision
without separate authorization. Production never imports/calls engine.simulate.
