"""Reanalyze preserved v1 results without rerunning or changing them."""
import csv,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def run():
 out=[]
 for source in ('batches','stress','development'):
  rows=list(csv.DictReader((ROOT/f'results/{source}.csv').open()))
  for family in sorted({r['family'] for r in rows}):
   for N in sorted({int(r['N']) for r in rows}):
    for method in sorted({r['method'] for r in rows}):
     a=[r for r in rows if r['family']==family and int(r['N'])==N and r['method']==method]
     if not a:continue
     b=[r for r in a if r['success'] in ('True','1')]
     out.append(dict(source=source,family=family,N=N,method=method,n=len(a),success=len(b),
       success_robot_mean_s=float(np.mean([float(r['robot_time_s']) for r in b])) if b else None,
       J_mean_s=float(np.mean([float(r['penalized_time_s']) for r in a]))))
 (ROOT/'revision/legacy_summary.json').write_text(json.dumps(out,indent=2))
 with (ROOT/'revision/legacy_summary.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
if __name__=='__main__':run()
