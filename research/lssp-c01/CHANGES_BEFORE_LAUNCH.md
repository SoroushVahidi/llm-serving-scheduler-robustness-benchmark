# Pre-launch implementation notes

Protocol commit: `8dd2c37`. No scientific outcomes inspected during these changes.

* First synthetic fixture run:32 passed/1 failed. The KV-release test incorrectly expected FCFS admission for the shortest-prompt adaptation. Corrected the expected first request according to the frozen policy definition; no algorithm changed. Original log/exit/PID retained under `evidence/local-validation-attempt1.*`.
* Input preparation independently checked raw/scaled arrival geometry, exact prompt/output lengths, IDs, window hashes, seed/factor agreement with saved historical cells, no dropped records and common-context coverage. First canonical window in each source remains selected; no substitution.
* Clarification: `token_throughput` counts output tokens of completed requests to match the historical numerator. `emitted_token_throughput` separately includes tokens from unfinished requests. The observed-time denominator is explicitly recorded; the new event-driven clock is not claimed bit-identical to historical tick rounding. No historical value is replaced.
* TTFT and TPOT summaries use completed-request support; incomplete requests' first-output times remain in raw terminal records. Every conditional count is reported. Partial output is not a completed request.
* Independent referee validates input/event/terminal consistency and common execution constraints. It does not certify the historical/native fidelity of the new policy algorithms. Literal scheduling fixtures separately check each adaptation's ordering, chunking and critical-decode rule. Policy-agnostic service is tested by injecting identical plans under every policy ID.

* Corrected the initial protocol's mistaken description of the historical margin denominator before any scientific run: historical ANWG uses the losing value, strict >10%, zero loser unestimable. The initially written max-value denominator remains only an explicitly new sensitivity. Both implementations receive boundary/zero tests. This is a protocol correction, not a historical estimate change.
* Wulver default Python is3.9.25, below the code's3.10 requirement. Batch launch now requires explicit `C01_PYTHON`, pinned to the existing historical `.venv312/bin/python` (3.12.13), and its environment is recorded. No dependency installation or login-node scientific simulation is performed.
