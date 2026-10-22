"""One-time construction notes: applies M2 edits to the copied M1 prose.
Not a regeneration command: final TeX is authoritative, inspect Git diff.
"""
from pathlib import Path
B=Path('paper/tompecs-m2/revised'); sec=B/'sections'
p=B/'main.tex';s=p.read_text().replace('36 satisfy the saved practical-margin and interval criteria for','36 satisfy the saved practical-margin and nominal interval criteria for').replace('with explicit tie and\nmissing-observation qualifications.','while a post-hoc comparison finds overlap of maximizing policy sets in\n57.8\\% of conditions. Independent numerical reproduction confirms the saved\nintervals, but their coverage and the historical FDR claim are not established.').replace('the M1 claim audit','the M1 and M2 claim audits').replace('this M1 revision','these M1/M2 revisions');p.write_text(s)
p=sec/'introduction.tex';s=p.read_text().replace('original six research questions are retained in','four retrospective manuscript questions and their mapping to all six\noriginal protocol questions appear in');s=s.replace('confidence-interval reversal criteria','nominal interval reversal criteria');s=s.replace('Uncertainty is instead assessed across workload windows, subject','Historical resampling variation is instead assessed across workload windows, subject');s=s.replace('The primary ANWG ranking correlations',r'''\subsection{Why comparative validity is the evaluation target}
A performance evaluator often has two decisions to make: which
implementation to compare, and which evidence would justify carrying its
ordering into a new setting. The second decision can fail even when the
first experiment is reproducible. An average over a trace can hide a
policy pair whose ordering changes elsewhere. Conversely, a small rank
change can be irrelevant if both implementations attain almost identical
utility. We therefore separate agreement of the full panel, individual
pair reversals, and changes in the set of preferred policies. These are
complementary questions with different denominators.

This distinction matters for modeling as well as for deployment. A
simulator can be repeatable while representing service demands or resource
constraints differently for different policies. Its ranking is then a
property of the complete policy--model combination. Reporting only a
leaderboard would encourage readers to attribute all differences to the
scheduling discipline. Reporting the model boundary, absolute outcome
levels and comparison support makes that attribution testable. This paper
uses the historical corpus to expose where the evidence ends rather than
treating a policy's implementation name as validation.

The unit of observation is equally consequential. Thousands of execution
records need not provide thousands of independent observations: policies
reuse the same windows, regions are transformations of those windows, and
the second deterministic pass supplies no sampling variation. Similarly,
more metric pairs do not create new workload coverage. A portable
comparison needs a clear account of what was resampled and what remained
fixed. This motivates preserving the full comparison grid, including
stable, tied and undefined cases, rather than reporting only reversals.

\subsection{Contribution and evidential scope}
The primary ANWG ranking correlations''')
s=s.replace('Agreement\nand disagreement are both findings; neither is assumed in advance.',r'''A retrospective audit additionally distinguishes deterministic choice
from the existence of a common maximizing policy, and saved interval
support from calibrated inference. Agreement and disagreement are both
findings; neither is assumed in advance.

The resulting contribution has three parts: a fixed evidence organization
that separates ranking agreement from practical pairwise change; a fully
identified simulator case study spanning source, operating region and
objective; and an independently reproducible audit showing how ties,
missingness and inferential assumptions alter the meaning of the saved
summaries. The audit is post hoc. It strengthens traceability, not the
prospective status of the experiment. No new scheduler, rank statistic,
coverage theorem or learned transfer predictor is proposed.''');p.write_text(s)
p=sec/'related_work.tex';s=p.read_text()+r'''
\subsection{What is added beyond standard ranking statistics}
Workload resampling has a direct performance-evaluation precedent.
Zakay and Feitelson's conference study decomposes traces into user
subtraces and recombines them while preserving activity cycles
\citep{zakay2013resampling}. The shared concern is that the structure of
the workload affects the reliability of a scheduler comparison. LSSP
resamples already selected request windows instead; it does not implement
user-level trace reconstruction or establish that its windows are
independent. The distinction prevents borrowing a validity argument from
a resampling design with different observational units.

Dem\v{s}ar's comparison framework uses ranks across multiple datasets to
compare algorithms, including Friedman omnibus tests and subsequent
comparisons \citep{demsar2006comparisons}. LSSP applies standard rank tools
to fixed policy implementations, but asks an additional descriptive
question: whether their order is preserved when the condition or metric
changes. A pooled difference between policies is not itself evidence of
such a change. A method can outperform another in every source and still
produce a strong omnibus statistic. The source-pair reversal table is
therefore a distinct object, not an automatic interpretation of Friedman
significance.

The methodological addition is the explicit linkage between comparison
objects: each ranking carries its implementation panel, observed-window
support, utility definition, practical threshold and tie rule. The
post-hoc audit shows that these choices have measurable consequences in
one corpus. For example, agreement of deterministic top choices and
intersection of maximizing sets yield different answers without any change
to the outcomes. This is evidence for reporting both objects when ties
are common; it is not a claim that a new estimator has been invented.

The study also separates three validation tasks that can otherwise be
conflated: reproducing an analysis from frozen numbers, assessing its
sampling assumptions, and checking whether the simulator represents the
intended serving mechanisms. Exact numerical reproduction addresses only
the first. The inferential audit addresses limits of the second; the
legacy native-runner audit exposes unresolved parts of the third. This
separation is the paper's relevance to modeling and performance evaluation,
but it also limits the strength of its systems conclusions. A benchmark
with correctly implemented standard statistics still needs a defensible
comparison model and sufficiently representative inputs.
''';p.write_text(s)
p=sec/'model.tex';s=p.read_text().replace('it has adequate implementation fidelity and passes its own unit\ntests','it was judged to have adequate implementation fidelity and passed its own unit\ntests').replace("two policies' outcomes on the same window and\nregion differ only because of the policy's own scheduling decisions, not\nbecause of independent sampling noise.","two policies' outcomes share the same input window without independent\nsimulation noise. Differences also include policy-dependent service modes,\nresource enforcement and information access; they cannot be attributed to\nscheduling order alone.");p.write_text(s)
p=sec/'portability.tex';s=p.read_text().replace('practically and statistically supported reversals','practical reversals passing the saved nominal interval rule').replace('95\\% CI $[0.90, 1.00]$','nominal 95\\% resampling interval $[0.90, 1.00]$').replace('Intervals are the preserved 95\\% window-bootstrap intervals;\nM1 independently reproduced the point estimates but did not rerun intervals.','Intervals are preserved nominal 95\\% window-resampling intervals;\nM2 independently reproduced all 18, without establishing coverage.').replace('Saved 95\\% interval','Saved nominal interval').replace('The canonical results reveal high rank stability across time:','The temporal evidence is mostly stable, with a LOW exception:').replace('a leave-one-region-out comparison','a region-subset comparison').replace('exhibit an identical quantitative pattern','provide additional summaries').replace('tests region dependence\nexplicitly','describes region dependence').replace('the headline cross-source portability conclusion is not sensitive\nto the choice of four-region versus six-region calibration grid','this particular descriptive mean changes little under that region subset');p.write_text(s)
p=sec/'robustness.tex';s=p.read_text().replace('seven preregistered robustness families','seven non-SLO robustness items in the historical implementation account').replace('This analysis directly answers RQ5','This analysis partially addresses original RQ5 and answers the finite-reference\npart of Q4').replace('does the resampled subset identify the single\nbest-performing PRIMARY-panel policy correctly','does the resampled subset reproduce the deterministic\nPRIMARY-panel top choice').replace('identifying the single best policy requires far less\nevidence','recovering that top choice requires fewer sampled windows').replace('this check was never part\nof the preregistered protocol','the concrete extension was specified after primary results, although\nbroad SLO sensitivity was already anticipated in the historical plan').replace('statistically indistinguishable from zero','unsupported by the extension\'s saved interval rule').replace('so\nhas nothing for a sensitivity check to stress-test','so\nthe selected-reversal persistence design omits it; this does not establish\nSLO insensitivity at LOW');p.write_text(s)
p=sec/'limitations.tex';s=p.read_text().replace('Window bootstrap intervals characterize variation within the\nsampled trace corpus under a window-exchangeability assumption.','Window bootstrap intervals summarize resampling variation within the\nsampled trace corpus. Their nominal coverage requires assumptions not\nestablished here.').replace('The raw-CI\nreversal taxonomy and the additional within-family BH-FDR flag answer\ndifferent questions; neither is a family-wise error guarantee. No global\nmultiplicity claim across all analyses is made.','The raw-interval\nreversal taxonomy and within-family BH flags are historical procedural\nlabels. Neither a calibrated significance level nor even within-family\nFDR control has been established. Increasing bootstrap draws cannot\nrepair dependence, screening or a mismatch of estimands.').replace('M1 independently reconciles execution counts, numerical pairs, primary\nKendall point estimates, stored reversal classifications and cross-metric\npoint estimates. It does not regenerate every bootstrap interval, establish\nfresh hardware reproducibility, or retroactively validate source licensing\nand public release accessibility.','M1 reconciled counts and point estimates; M2 independently reproduces all\n198 source-ranking tau intervals, 72 primary reversal intervals, 6,890\ncross-metric difference intervals, six cross-metric rank intervals and\n66 Friedman statistics. This does not establish interval coverage, fresh\nhardware reproducibility, source licensing or public release accessibility.');p.write_text(s)
