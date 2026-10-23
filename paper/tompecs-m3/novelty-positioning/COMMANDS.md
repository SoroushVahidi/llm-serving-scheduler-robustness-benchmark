# Revision validation commands

Run from the dedicated worktree rooted at
`/home/soroush/repos/llm-serving-scheduler-lssp-m3-novelty-positioning`.
No command below launches a scientific campaign. Tests exercise existing fixtures; all analysis checks read saved evidence.

```bash
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider /home/soroush/artifacts/lssp-m3-rc1-20261022/clean-extraction/evidence/c01/research/lssp-c01/test_contract.py
python paper/tompecs-m3/urgency-analysis/check_certificate.py /home/soroush/artifacts/lssp-m3-rc1-20261022/clean-extraction /home/soroush/artifacts/lssp-m3-budget-sensitivity-20261022
python paper/tompecs-m3/budget-sensitivity/verify_study.py /home/soroush/artifacts/lssp-m3-budget-sensitivity-20261022 /home/soroush/artifacts/lssp-m3-rc1-20261022/clean-extraction
python paper/tompecs-m3/editorial-revision/reduced_comparisons.py
python paper/tompecs-m3/editorial-revision/check_abstract_claims.py --report paper/tompecs-m3/novelty-positioning/abstract-check.json
python paper/tompecs-m3/editorial-revision/verify_preservation.py
bash paper/tompecs-m3/scripts/build.sh manuscript
bash paper/tompecs-m3/scripts/build.sh acmsmall
python paper/tompecs-m3/scripts/validate.py --artifact-root /home/soroush/artifacts/lssp-m3-rc1-20261022/clean-extraction
```

After verification, copy fresh validation and preservation reports into this directory and restore their historical tracked destinations from the parent commit. The budget, certificate, and reduced-comparison checkers regenerate their historical reports byte-identically. Copy the two final build PDFs to `paper/tompecs-m3/m3-{manuscript,acmsmall}.pdf` after visual inspection.

Logs are in `/home/soroush/artifacts/lssp-m3-novelty-positioning-20261023/`:
`regression.log`, `c01-tests.log`, `certificate.log`, `budget-verification.log`,
`reduced.log`, `abstract.log`, `preservation.log`, `scientific.log`,
`build-manuscript.log`, `build-acmsmall.log`.
Final visual-review renders are in its `visual-final/` subdirectory.
All commands completed; no background scientific job remains.
