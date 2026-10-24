"""Engineering-only throughput check. Never print calibration outcomes."""
import json,time
from experiment import study
from reference import validate_record
from design import SCENARIOS
for sid in (7,11,17):
    started=time.monotonic()
    y,mask,record=study(sid,42,engineering=True)
    validate_record(SCENARIOS[sid],y,mask,record,sid,42)
    print(json.dumps(dict(evidence_class='ENGINEERING_ONLY_NAMESPACE_0',scenario=SCENARIOS[sid]['name'],seconds=time.monotonic()-started,bootstrap_draws=2000,raw_shape=list(y.shape))),flush=True)
