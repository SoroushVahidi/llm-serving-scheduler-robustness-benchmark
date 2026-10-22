#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
variant=${1:?baseline or revised}
mode=${2:?manuscript or acmsmall}
[[ $variant == baseline || $variant == revised ]]
[[ $mode == manuscript || $mode == acmsmall ]]
mkdir -p "build/$variant-$mode" evidence
export TEXINPUTS="$PWD/template:${TEXINPUTS:-}"
export BSTINPUTS="$PWD/template:${BSTINPUTS:-}"
export SOURCE_DATE_EPOCH=1792627200 FORCE_SOURCE_DATE=1 TZ=UTC
job="$variant-$mode"
input="\\input{$variant/main.tex}"
if [[ $mode == acmsmall ]]; then input="\\def\\MOneSmall{1}$input"; fi
printf 'cwd=%s\npid=%s\nvariant=%s\nmode=%s\nstart=%s\n' "$PWD" "$$" "$variant" "$mode" "$(date -u --iso-8601=seconds)"
pdflatex -interaction=nonstopmode -halt-on-error -file-line-error -recorder -output-directory="build/$job" -jobname="$job" "$input"
(cd "build/$job"; BIBINPUTS="$PWD/../..:" bibtex "$job")
for pass in 2 3; do pdflatex -interaction=nonstopmode -halt-on-error -file-line-error -recorder -output-directory="build/$job" -jobname="$job" "$input"; done
pdfinfo "build/$job/$job.pdf"
printf 'finish=%s\n' "$(date -u --iso-8601=seconds)"
