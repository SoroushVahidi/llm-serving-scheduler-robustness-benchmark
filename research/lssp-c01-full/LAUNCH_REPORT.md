# LSSP-C01-FULL launch observation

State: **RUNNING_HEALTHY**. Observation: 2026-10-22T15:38:48.675240+00:00. Monitoring ended after 67.7 seconds from submission; no further monitoring or automatic retries.

Draft PR: https://github.com/SoroushVahidi/llm-serving-scheduler-robustness-benchmark/pull/15, stacked on #11. Execution commit: `2d8342e699f35044044ac518c0b75a3c4a1c768c`. Launch freeze commit: `22756cee28db386205ebfe03b0cf782d6c64d2e5`. Full launch identity: `167b9074e57114203e6aaaf3ded08b7b4d8f0a72b35c69054fa995de8d4ef47a`.

Slurm job: **1440402**; one CPU, 4 GiB, zero GPUs, nine-hour maximum. Submission 2026-10-22 15:37:41 UTC; start 15:37:56 UTC. Initial scheduler snapshot coincided with startup, before Python initialized. The subsequent single application-health check observed checkpoint status `RUNNING`, 300 validated cells (48 pilot reuse, 252 new), with empty stderr and no failure record. This is startup evidence, not campaign completion.

Deployment: `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-full-20261022`

- stdout: `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-full-20261022/logs/c01-full-167b9074e5711420-1440402.out`
- stderr: `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-full-20261022/logs/c01-full-167b9074e5711420-1440402.err`
- checkpoint: `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-full-20261022/runs/c01-full-167b9074e5711420/checkpoint.json`
- new cells: `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-full-20261022/runs/c01-full-167b9074e5711420/cells/`
- reused pilot copies: `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-full-20261022/reused/`
- eventual reports: `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-full-20261022/runs/c01-full-167b9074e5711420/analysis/`
- original audit provenance: `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-full-20261022/reuse_index.json` and `provenance/pilot/`
- initial scheduler snapshot: `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-full-20261022/startup-observation.json`
- final startup health snapshot: `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-full-20261022/startup-health.json`
- pinned checks: `/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-c01-full-20261022/prelaunch.txt`, `final-tests.txt`, `launch-check.exit`

Reuse audit: 144/144 original cells replay-validated and exactly compatible; full matrix 5,760, requiring 5,616 new cells; zero invalidated. Local and pinned-Wulver tests: 55 each. Pinned full-input regeneration and all 164 launch fingerprints passed. Original engine, policies, referee, corpus, experimental parameters and historical artifacts are unchanged. STAT01 was not queried or changed.

See PROTOCOL.md for prospective analysis, README.md for the final verification procedure, and evidence/ for audit/tests/hash evidence. No full-campaign scientific conclusions or publication readiness are asserted. Next phase after completion is independent result review, manuscript revision and submission.
