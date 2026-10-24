#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mode=${1:?manuscript or acmsmall}
[[ $mode == manuscript || $mode == acmsmall ]]
mkdir -p "build/$mode"
export TEXINPUTS="$PWD/template:${TEXINPUTS:-}"
export BSTINPUTS="$PWD/template:${BSTINPUTS:-}"
export SOURCE_DATE_EPOCH=1792627200 FORCE_SOURCE_DATE=1 TZ=UTC
input='\input{main.tex}'
if [[ $mode == acmsmall ]]; then input='\def\MThreeSmall{1}\input{main.tex}'; fi
pdflatex -interaction=nonstopmode -halt-on-error -file-line-error -recorder -output-directory="build/$mode" -jobname="m3-$mode" "$input"
(cd "build/$mode"; BIBINPUTS="$PWD/../..:" bibtex "m3-$mode")
for pass in 2 3 4 5; do
 pdflatex -interaction=nonstopmode -halt-on-error -file-line-error -recorder -output-directory="build/$mode" -jobname="m3-$mode" "$input"
 if ! grep -Eq 'Rerun to get|undefined references|undefined citations|Citation .* undefined' "build/$mode/m3-$mode.log"; then
  break
 fi
done
if grep -Eq 'Rerun to get|undefined references|undefined citations|Citation .* undefined' "build/$mode/m3-$mode.log"; then
 echo "References did not converge after five LaTeX passes" >&2
 exit 1
fi
pdfinfo "build/$mode/m3-$mode.pdf"
