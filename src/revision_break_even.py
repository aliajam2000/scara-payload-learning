"""Sequential exploratory refinement, declared after inspecting noise10 N=20/60."""
import csv,json,hashlib
from pathlib import Path
from .revision_experiment import batch,METHODS,ROOT

def run():
 spec=json.loads((ROOT/'revision/break_even_protocol.json').read_text())
 for p,h in spec['hashes'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
 out=ROOT/'revision'
 with (out/'break_even_runs.csv').open('w',newline='') as f,(out/'break_even_items.csv').open('w',newline='') as fi:
  w=wi=None
  for N in spec['N']:
   for seed in spec['seeds']:
    for method in spec['methods']:
     r,h,_=batch(seed,N,spec['family'],method,spec['settings'])
     r={'group':'break_even','setting':'noise10',**r}
     if w is None:w=csv.DictWriter(f,fieldnames=list(r));w.writeheader()
     w.writerow(r)
     for it in h:
      it={k:r[k] for k in ('group','setting','seed','N','family','method')}|it
      if wi is None:wi=csv.DictWriter(fi,fieldnames=list(it));wi.writeheader()
      wi.writerow(it)
   f.flush();fi.flush();print(f'Break-even refinement N={N} complete',flush=True)
if __name__=='__main__':run()
