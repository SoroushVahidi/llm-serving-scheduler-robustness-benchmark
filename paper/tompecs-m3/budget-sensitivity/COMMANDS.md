# Commands and locations

Run from the dedicated checkout:
`/home/soroush/repos/llm-serving-scheduler-lssp-m3-budget-sensitivity`.
The exact baseline is PR23 head `4c08660eeb528a5a459800bbc79771f4b8e4dbfc`.

```bash
python paper/tompecs-m3/budget-sensitivity/run_study.py /home/soroush/artifacts/lssp-m3-rc1-20261022/clean-extraction /home/soroush/artifacts/lssp-m3-budget-sensitivity-20261022 --phase pilot
python paper/tompecs-m3/budget-sensitivity/run_study.py /home/soroush/artifacts/lssp-m3-rc1-20261022/clean-extraction /home/soroush/artifacts/lssp-m3-budget-sensitivity-20261022 --phase study
python paper/tompecs-m3/budget-sensitivity/analyze_study.py /home/soroush/artifacts/lssp-m3-rc1-20261022/clean-extraction /home/soroush/artifacts/lssp-m3-budget-sensitivity-20261022 --output paper/tompecs-m3/budget-sensitivity
python paper/tompecs-m3/budget-sensitivity/verify_study.py /home/soroush/artifacts/lssp-m3-budget-sensitivity-20261022 /home/soroush/artifacts/lssp-m3-rc1-20261022/clean-extraction
python -m pytest -q
python -m pytest -q /home/soroush/artifacts/lssp-m3-rc1-20261022/clean-extraction/evidence/c01/research/lssp-c01/test_contract.py
python paper/tompecs-m3/editorial-revision/verify_preservation.py
python paper/tompecs-m3/editorial-revision/reduced_comparisons.py
python paper/tompecs-m3/editorial-revision/check_abstract_claims.py --report paper/tompecs-m3/budget-sensitivity/abstract-check.json
bash paper/tompecs-m3/scripts/build.sh manuscript
bash paper/tompecs-m3/scripts/build.sh acmsmall
python paper/tompecs-m3/scripts/validate.py --artifact-root /home/soroush/artifacts/lssp-m3-rc1-20261022/clean-extraction
```

The original pilot used the preregistered runner at 5630bfd; continuation
used the metadata correction at d6407cd. The saved manifest preserves the
original identity and subsequent results record actual execution code hashes.
A new reproduction should use a new output directory: its corrected-runner
identity will differ from the original pilot identity without changing
scientific inputs or execution semantics. No hidden random draws occur.

`analyze_study.py` was also run with output directory
`/home/soroush/artifacts/lssp-m3-budget-clean-analysis`; all seven outputs
were byte-compared with the checked-in versions. Original preservation and
scientific validation reports were restored byte-for-byte after copying
fresh reports into this directory, retaining prior evidence as history.

Logs are under `/home/soroush/artifacts/`:

* `lssp-m3-budget-pilot-20261022.log`
* `lssp-m3-budget-study-20261022.log` (metadata-only stopped attempt)
* `lssp-m3-budget-study-corrected-20261022.log`
* `lssp-m3-budget-analysis-20261022.log`
* `lssp-m3-budget-clean-analysis.log`
* `lssp-m3-budget-independent-check.log`
* `lssp-m3-budget-regression.log`
* `lssp-m3-budget-reduced-check.log`
* `lssp-m3-budget-abstract.log`
* `lssp-m3-budget-scientific-validation.log`
* `lssp-m3-budget-build-manuscript.log`
* `lssp-m3-budget-build-acmsmall.log`

Visual renders are in `/home/soroush/artifacts/lssp-m3-budget-visual/`.
The manuscript's existing build scripts use SOURCE_DATE_EPOCH=1792627200.
Raw sensitivity records occupy about 6.4 MiB; no remote compute/storage
was needed. All commands completed; no persistent job/session remains.
