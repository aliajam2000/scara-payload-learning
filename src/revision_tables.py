"""Data-backed LaTeX tables used directly by the revised manuscript."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'revision'
def number(x):return '--' if x is None else f'{x:.3f}'
def interval(a):return '--' if a[0] is None else f'{a[0]:.3f} [{a[1]:.3f}, {a[2]:.3f}]'
def make(s):
 rows=[r for r in s['decomposition'] if r['group']=='extended']
 lines=[r'\begin{tabular}{rcc}\toprule',r'$N$ & Exciting & Low yaw\\\midrule']
 for N in (1,5,20,40,60,100):
  parts=[interval(next(r for r in rows if r['N']==N and r['family']==f)['net_extra_mean_ci95_s']) for f in ('excited','low_yaw')]
  lines.append(str(N)+' & '+' & '.join(parts)+r'\\')
 lines.append(r'\bottomrule\end{tabular}')
 (OUT/'table_effects.tex').write_text('\n'.join(lines))
 methods=[('passive','Passive'),('always_probe','Always probe'),('batch_aware','Batch aware'),('ignore_passive','Ignore passive'),('uncertainty_trigger','Uncertainty trigger'),('oracle','Known payload')]
 lines=[r'\begin{tabular}{lrrc}\toprule',r'Method & Exciting & Low yaw & Completed\\\midrule']
 for m,label in methods:
  a=[next(r for r in s['summaries'] if r['group']=='extended' and r['N']==20 and r['family']==f and r['method']==m) for f in ('excited','low_yaw')]
  lines.append(label+' & '+' & '.join(number(r['success_robot_mean_s']) for r in a)+f" & {a[0]['success']}/{a[0]['n']}"+r'\\')
 lines.append(r'\bottomrule\end{tabular}');(OUT/'table_times.tex').write_text('\n'.join(lines))
 lines=[r'\begin{tabular}{llrrrr}\toprule',r'Setting & Method & Correct & Beneficial & Selected & Regret (s)\\\midrule']
 for setting,N in [('base',100),('noise10',20),('noise10',60),('margin2',60),('margin4',60)]:
  for m,label in methods[:3]:
   r=next(r for r in s['decisions'] if r['setting']==setting and r['N']==N and r['family']=='low_yaw' and r['method']==m)
   summary=next(x for x in s['summaries'] if x['setting']==setting and x['N']==N and x['family']=='low_yaw' and x['method']==m)
   name=f'{setting}, {N}'.replace('_',r'\_')
   lines.append(f"{name} & {label} & {r['correct_n']}/{r['decision_n']} & {r['beneficial_probe_n']} & {summary['probes']} & {number(r['mean_regret_ci95_s'][0])}"+r'\\')
 lines.append(r'\bottomrule\end{tabular}');(OUT/'table_decisions.tex').write_text('\n'.join(lines))
if __name__=='__main__':make(json.loads((OUT/'analysis.json').read_text()))
