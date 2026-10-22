#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mode=${1:?manuscript or acmsmall}
[[ $mode == manuscript || $mode == acmsmall ]]
mkdir -p "build/$mode" pdf
export TEXINPUTS="$PWD/../tompecs-m2/template:${TEXINPUTS:-}"
export BSTINPUTS="$PWD/../tompecs-m2/template:${BSTINPUTS:-}"
export SOURCE_DATE_EPOCH=1792627200 FORCE_SOURCE_DATE=1 TZ=UTC
job="m3-$mode"
input='\input{main.tex}'
if [[ $mode == acmsmall ]]; then input="\\def\\MThreeSmall{1}$input"; fi
pdflatex -interaction=nonstopmode -halt-on-error -file-line-error -recorder -output-directory="build/$mode" -jobname="$job" "$input"
(cd "build/$mode"; BIBINPUTS="$PWD/../..:" bibtex "$job")
for pass in 2 3; do
 pdflatex -interaction=nonstopmode -halt-on-error -file-line-error -recorder -output-directory="build/$mode" -jobname="$job" "$input"
done
cp "build/$mode/$job.pdf" "pdf/$job.pdf"
pdfinfo "pdf/$job.pdf"
