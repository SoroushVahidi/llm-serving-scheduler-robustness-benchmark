# Reproduce this read-only investigation

Run from `/home/soroush/repos/llm-serving-scheduler-lssp-m3-urgency-mechanism`.
The first structural record was committed before the experiment decision.
No new scientific campaign was executed, and no simulator source was edited.

```bash
python paper/tompecs-m3/urgency-analysis/audit_urgency.py /home/soroush/artifacts/lssp-m3-rc1-20261022/clean-extraction /home/soroush/artifacts/lssp-m3-budget-sensitivity-20261022 --output paper/tompecs-m3/urgency-analysis
python paper/tompecs-m3/urgency-analysis/check_certificate.py /home/soroush/artifacts/lssp-m3-rc1-20261022/clean-extraction /home/soroush/artifacts/lssp-m3-budget-sensitivity-20261022
python paper/tompecs-m3/urgency-analysis/check_policy_boundary.py /home/soroush/artifacts/lssp-m3-rc1-20261022/clean-extraction
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider /home/soroush/artifacts/lssp-m3-rc1-20261022/clean-extraction/evidence/c01/research/lssp-c01/test_contract.py
python paper/tompecs-m3/budget-sensitivity/verify_study.py /home/soroush/artifacts/lssp-m3-budget-sensitivity-20261022 /home/soroush/artifacts/lssp-m3-rc1-20261022/clean-extraction
python paper/tompecs-m3/editorial-revision/reduced_comparisons.py
python paper/tompecs-m3/editorial-revision/check_abstract_claims.py --report paper/tompecs-m3/urgency-analysis/abstract-check.json
python paper/tompecs-m3/editorial-revision/verify_preservation.py
bash paper/tompecs-m3/scripts/build.sh manuscript
bash paper/tompecs-m3/scripts/build.sh acmsmall
python paper/tompecs-m3/scripts/validate.py --artifact-root /home/soroush/artifacts/lssp-m3-rc1-20261022/clean-extraction
```

The audit was also regenerated to `/home/soroush/artifacts/lssp-m3-urgency-clean-audit`;
all three outputs were byte-compared. Original validation/preservation files
were restored from the exact baseline after their fresh reports were copied
into `urgency-analysis/`. The prior budget-study checker regenerates its
report byte-identically. Input/journal directories remain read-only.

Logs under `/home/soroush/artifacts/`:

* `lssp-m3-urgency-audit.log`
* `lssp-m3-urgency-independent.log`
* `lssp-m3-urgency-clean-audit.log`
* `lssp-m3-urgency-regression.log`
* `lssp-m3-urgency-c01-tests.log`
* `lssp-m3-urgency-pr24-check.log`
* `lssp-m3-urgency-reduced.log`
* `lssp-m3-urgency-abstract.log`
* `lssp-m3-urgency-scientific.log`
* `lssp-m3-urgency-build-manuscript.log`
* `lssp-m3-urgency-build-acmsmall.log`

Visual inspection renders: `/home/soroush/artifacts/lssp-m3-urgency-visual/`.
All commands completed; no persistent job/session remains. The pinned code
and prior raw inputs/journals are in the pre-existing local candidate and
budget-study artifact. This change adds only manuscript/supporting analysis,
not a dataset release or new raw experimental output.
