"""Publication-quality proposed exhibits, outside manuscript and release candidate."""
import csv,pathlib,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=pathlib.Path(__file__).parent;O=R/'review';E=R/'proposed-exhibits';E.mkdir(exist_ok=True)
def rows(p):
 with p.open() as f:return list(csv.DictReader(f))
labels={'azure_llm_2024':'Azure','bailian_qwen':'Bailian','burstgpt':'BurstGPT'}
data=rows(O/'table-time01.csv')
headers=['Source','Slots','Timing: mean latency','Timing: token rate','SLO: mean latency','SLO: window p95','SLO: token rate']
cols=['chunked_timing_mean_latency_pct','chunked_timing_token_throughput_pct','slo_vs_chunked_variable_mean_latency_pct','slo_vs_chunked_variable_mean_window_p95_pct','slo_vs_chunked_variable_token_throughput_pct']
body=[]
for r in data:body.append([labels[r['source']],r['slots']]+[f"{float(r[c]):+.2f}" for c in cols])
caption=("Timing effects are percentage changes of chunked-FCFS source means from fixed to composition-dependent timing; "
"SLO columns compare SLO-gated with chunked-FCFS under composition-dependent timing. Each source contributes eight windows, "
"equally weighted across LOW and HIGH_PRESSURE at each capacity. The p95 column is a mean of window p95s. "
"Negative latency changes are favorable; positive throughput changes are favorable. These are descriptive ratios of means.")
tex=r"""\begin{table}[t]
\centering\small
\setlength{\tabcolsep}{3pt}
\caption{"""+caption+r"""}
\label{tab:proposed-time-sensitivity}
\begin{tabular}{llrrrrr}
\toprule
 & & \multicolumn{2}{c}{Timing change (\%)} & \multicolumn{3}{c}{SLO vs.\ chunked, variable (\%)}\\
Source & Slots & Mean latency & Token rate & Mean latency & Window p95 & Token rate\\
\midrule
"""
tex+='\n'.join(' & '.join(x)+r'\\' for x in body)
tex+=r"""
\bottomrule
\end{tabular}
\end{table}
"""
(E/'table-time01.tex').write_text(tex)
(E/'table-time01.txt').write_text(caption+'\n\n'+'\t'.join(headers)+'\n'+'\n'.join('\t'.join(x) for x in body)+'\n')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'pdf.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(1,2,figsize=(7.6,3.4),sharey=True,layout='constrained')
ys=list(range(6))
for ax,metric,title in zip(axes,['mean_latency','token_throughput'],['Mean latency','Token throughput']):
 fixed=[float(x['slo_vs_chunked_fixed_'+metric+'_pct']) for x in data];var=[float(x['slo_vs_chunked_variable_'+metric+'_pct']) for x in data]
 for y,a,b in zip(ys,fixed,var):ax.plot([a,b],[y,y],color='#777777',lw=1)
 ax.scatter(fixed,ys,marker='o',facecolors='white',edgecolors='#0072B2',s=38,label='Fixed duration',zorder=3)
 ax.scatter(var,ys,marker='s',color='#D55E00',s=27,label='Composition dependent',zorder=4)
 ax.axvline(0,color='#444444',lw=.8,ls='--');ax.grid(axis='x',alpha=.18);ax.set_title(title);ax.set_xlabel('SLO-gated relative to chunked-FCFS (%)')
axes[0].set_yticks(ys,[labels[x['source']]+' · '+x['slots']+' slots' for x in data]);axes[0].invert_yaxis();fig.legend(*axes[1].get_legend_handles_labels(),loc='outside upper center',ncol=2,frameon=False,fontsize=8)
fig.savefig(E/'time01-relative-policy-effects.pdf',metadata={'Title':'Relative scheduling effects under two timing models','Author':'Soroush Vahidi','Subject':'Proposed descriptive exhibit; eight selected windows per source; no inferential error bars'})
fig.savefig(E/'time01-relative-policy-effects.svg')
fig.savefig(E/'time01-relative-policy-effects.png',dpi=180)
plt.close(fig)
(E/'FIGURE_CAPTION.txt').write_text("Relative SLO-gated performance on the same selected windows under fixed and composition-dependent timing. Each point is a percentage contrast between equally weighted source means, averaging LOW and HIGH_PRESSURE within eight windows per source. Lower latency and higher throughput are preferable. The selected BurstGPT subset has worse SLO-gated mean latency under both models; it does not reproduce the full-corpus average benefit. Connected points are matched model contrasts, not confidence intervals. No hardware prediction is implied.\n")
# ABL table presents intervention direction explicitly and omits redundant endpoints only from this compact display.
a=rows(O/'table-abl01-all-endpoints.csv')
keep={'mean_latency':'Mean latency (s)','p95_latency':'Mean window p95 (s)','token_throughput':'Token throughput (tokens/s)','arrival_normalized_weighted_goodput':'Deadline attainment'}
display=[x for x in a if x['metric'] in keep]
text='FCFS waiting control minus original prompt-ordered SLO; 1,440 matched setting cells, not independent replicates.\n\n'
text+='Endpoint\tOriginal mean\tControl mean\tMean paired difference\tControl better/worse/tied\n'
for x in display:text+='\t'.join([keep[x['metric']],f"{float(x['mean_original']):.6f}",f"{float(x['mean_control']):.6f}",f"{float(x['mean_paired_difference']):+.6f}",'/'.join(x[k] for k in ['favorable','adverse','ties'])])+'\n'
(E/'table-abl01.txt').write_text(text)
tex=r"""\begin{table}[t]
\centering\small
\caption{Controlled prompt-ordering intervention over all 1,440 matched C01 conditions. Positive differences mean FCFS-waiting control minus original prompt-ordered SLO. Counts favor the control according to each endpoint direction; they are dependent descriptive counts. Tail latency is a mean of window p95s, not a pooled p95.}
\label{tab:proposed-prompt-ablation}
\begin{tabular}{lrrrr}
\toprule
Endpoint & Original & Control & Difference & Better/worse/tied\\
\midrule
"""
for x in display:tex+=' & '.join([keep[x['metric']],f"{float(x['mean_original']):.5f}",f"{float(x['mean_control']):.5f}",f"{float(x['mean_paired_difference']):+.5f}",'/'.join(x[k] for k in ['favorable','adverse','ties'])])+r'\\'+'\n'
tex+=r'\bottomrule'+'\n'+r'\end{tabular}'+'\n'+r'\end{table}'+'\n'
(E/'table-abl01.tex').write_text(tex)
print('Created two standalone table proposals and vector PDF/SVG timing figure.')

