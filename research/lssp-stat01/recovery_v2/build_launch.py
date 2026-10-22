"""Freeze a distinct recovery identity after tests; never submits a job."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(output, root):
    here = Path(__file__).resolve().parent
    original = json.loads((here.parent/'launch.json').read_text())
    audit = json.loads((here/'evidence/pr13-audit-summary.json').read_text())
    if audit['status'] != 'COMPLETED_SUCCESS' or audit['checked_studies'] != 112275 or audit['failed_batches']:
        raise ValueError('audit gate')
    if (here/'evidence/tests-pinned.exit').read_text().strip() != '0':
        raise ValueError('pinned test gate')
    # Every frozen original source must still agree with its execution manifest.
    for name, expected in original['files'].items():
        if sha(here.parent/name) != expected:
            raise ValueError('original source changed: '+name)
    names = ['rv2_methods.py','rv2_reference.py','rv2_summary.py','rv2_run.py',
             'test_recovery.py','AMENDMENT.md','recovery.sbatch','build_launch.py','submit_once.py']
    spec = dict(schema='STAT01-recovery-v2',
        code_commit=subprocess.check_output(['git','rev-parse','HEAD'], cwd=here, text=True).strip(),
        original_root='/project/ikoutis/sv96/github/llm-serving-scheduler-lssp-stat01-454168a00524',
        original_launch=original, original_identity=audit['identity'], recovery_root=root,
        files={name:sha(here/name) for name in names},
        source_index_sha256=sha(here/'evidence/source-batches.json'),
        source_audit_sha256=sha(here/'evidence/pr13-audit-summary.json'),
        audited_evidence_log_sha256=audit['batch_evidence_sha256'],
        methods=original['methods']+['legacy_source_screened_BH']+['exact_'+n for n in original['methods']],
        original_method_count=8, postdiagnosis_method_count=9,
        registration='NINE_POST_DIAGNOSIS_ADDITIONS_ORIGINAL_EIGHT_PRESERVED',
        original_mc_delta='.05/(18*8*16*5)', expanded_mc_delta='.05/(18*17*16*5)',
        stopping='UNCHANGED_ORIGINAL_EIGHT_ONLY',
        reuse=dict(raw_studies=112275, original_records=112275, invalidated_raw_studies=0,
                   original_screened_records_not_legacy_equivalent=31, missing_studies=21725),
        resources=dict(cpus=4, memory='8G', gpus=0, walltime='09:00:00', schedule_hours=8.75),
        validation=dict(local_log_sha256=sha(here/'evidence/tests-local-final.txt'),
                        pinned_log_sha256=sha(here/'evidence/tests-pinned.txt')))
    with output.open('x') as stream:
        json.dump(spec,stream,indent=2,sort_keys=True,allow_nan=False)
        stream.write('\n')
    identity = hashlib.sha256(json.dumps(spec,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    print('stat01-recovery-v2-'+identity[:16])


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--recovery-root',required=True)
    args=parser.parse_args()
    main(args.output,args.recovery_root)
