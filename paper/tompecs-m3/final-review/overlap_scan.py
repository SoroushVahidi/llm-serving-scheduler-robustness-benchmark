#!/usr/bin/env python3
"""Read pinned manuscript sources only; exact prose-overlap diagnostic, not experiments.

Requires the three local repositories. Does not infer plagiarism or submission status.
Reports unique 12-word shingles, retaining per-file boundaries. TeX normalization is
deliberately conservative; bibliography/template/generated tables are excluded.
"""
import collections, hashlib, itertools, json, pathlib, re, subprocess

OUT = pathlib.Path(__file__).resolve().parent
REPO = OUT.parents[2]
HOME = pathlib.Path('/home/soroush')
versions = {
    'M3_reviewed': (REPO, 'ed24b2e8224ea88aa289b60dea6142beeea5330d', ['paper/tompecs-m3/main.tex', 'paper/tompecs-m3/sections/']),
    'JSC': (REPO, 'b1f9a12021c25dff8ad7cc06ff9654b6a047c132', ['paper/jsc_submission_package/']),
    'PEVA': (REPO, '097547206b6e99286553f43190bfa14c5b542b35', ['paper/peva_submission_package/']),
    'SMPT': (REPO, 'cc25fcd14f6fe28ab30d9e46635a72c0d6285d00', ['paper/smpt_submission_package/']),
    'SMPT_blind': (REPO, 'cc25fcd14f6fe28ab30d9e46635a72c0d6285d00', ['paper/smpt_blind_submission_package/']),
    'legacy_main': (REPO, 'e73a3b711b65f9c181ff9a2674007efca22f1b65', ['paper/main.tex', 'paper/sections/']),
    'M1_baseline': (REPO, '366752a76f86dec30190f3e7767124f684378de4', ['paper/tompecs-m1/baseline/main.tex', 'paper/tompecs-m1/baseline/sections/']),
    'M1_revised': (REPO, '366752a76f86dec30190f3e7767124f684378de4', ['paper/tompecs-m1/revised/main.tex', 'paper/tompecs-m1/revised/sections/']),
    'M2': (REPO, '880a37e8e7c19d089be124291e288269966a9147', ['paper/tompecs-m2/revised/main.tex', 'paper/tompecs-m2/revised/sections/']),
    'headroom_PEVA': (HOME/'llm-serving-heuristic-evolution', '327736bc07c79e9ac6a1f233473f5a289ca4438a', ['paper/performance_evaluation/main.tex']),
    'headroom_PEVA_package': (HOME/'llm-serving-heuristic-evolution', '327736bc07c79e9ac6a1f233473f5a289ca4438a', ['paper/performance_evaluation/submission/main.tex']),
    'heuristic_LLM2026_history': (HOME/'llm-serving-heuristic-evolution', '327736bc07c79e9ac6a1f233473f5a289ca4438a', ['paper/history/llm2026/submission_package/source/main.tex']),
    'module_intervention': (HOME/'repos/llm-serving-module-intervention-benchmark', 'ffae40a1d470624b3dc1da7c48673b12c6556152', ['paper/main.tex', 'paper/sections/']),
}

def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args])

def words(text):
    text = re.sub(r'(?m)(?<!\\)%.*$', '', text)
    text = re.sub(r'\\(?:cite\w*|label|ref|eqref|input|includegraphics|bibliography|bibliographystyle)(?:\[[^]]*\])?\{[^}]*\}', ' ', text)
    if '\\begin{document}' in text:
        text = text.split('\\begin{document}', 1)[1]
    text = re.sub(r'\\[A-Za-z@]+\*?', ' ', text)
    return re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text.lower())

snapshots, sets = {}, {}
for name, (repo, rev, prefixes) in versions.items():
    files = git(repo, 'ls-tree', '-r', '--name-only', rev, '--', *prefixes).decode().splitlines()
    files = [f for f in files if f.endswith('.tex')]
    assert files, name
    inventory, index = [], {}
    for f in files:
        raw = git(repo, 'show', f'{rev}:{f}')
        w = words(raw.decode())
        inventory.append(dict(path=f, sha256=hashlib.sha256(raw).hexdigest(), normalized_words=len(w)))
        for i in range(len(w)-11):
            index.setdefault(' '.join(w[i:i+12]), []).append(f)
    snapshots[name] = dict(commit=rev, repository=str(repo), files=inventory, unique_12grams=len(index))
    sets[name] = index
comparisons = []
for a, b in itertools.combinations(versions, 2):
    common = set(sets[a]) & set(sets[b])
    if a != 'M3_reviewed' and {a,b} not in [{'PEVA','SMPT'}, {'JSC','PEVA'}, {'SMPT','SMPT_blind'}, {'headroom_PEVA','headroom_PEVA_package'}]:
        continue
    comparisons.append(dict(a=a,b=b,shared_unique_12grams=len(common),
        fraction_a=len(common)/len(sets[a]),fraction_b=len(common)/len(sets[b]),
        file_pair_counts=[dict(a_file=fa,b_file=fb,shared_12grams=n) for (fa,fb),n in sorted(collections.Counter((fa,fb) for s in common for fa in set(sets[a][s]) for fb in set(sets[b][s])).items())],
        sample_matches=[dict(words=s,a_files=sets[a][s],b_files=sets[b][s]) for s in sorted(common)[:12]]))
result=dict(method='Exact unique 12-word shingles after conservative TeX normalization; within-file only; not semantic similarity or a plagiarism score.', snapshots=snapshots, comparisons=comparisons)
(OUT/'overlap-evidence.json').write_text(json.dumps(result,indent=2)+'\n')
for x in comparisons:
    print(x['a'], x['b'], x['shared_unique_12grams'], f"{100*x['fraction_a']:.2f}%", f"{100*x['fraction_b']:.2f}%")
