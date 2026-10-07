"""Revision entry point. Analysis reuses included data; rerun preserves it."""
import argparse,json,shutil,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('command',choices=['analyze','rerun','verify','progress'])
a=p.parse_args()
from restore_data import restore
restore()
if a.command=='analyze':
 from src.revision_analysis import analyze
 analyze()
elif a.command=='verify':
 from src.revision_release import verify
 verify()
elif a.command=='progress':
 import csv
 protocol=json.loads((ROOT/'revision/post_review_protocol.json').read_text())
 total=sum(len(j['seeds'])*len(j['methods']) for j in protocol['jobs'])
 runs=ROOT/'revision/runs.csv'
 n=sum(1 for _ in csv.DictReader(runs.open())) if runs.exists() else 0
 total+=250
 extra=ROOT/'revision/break_even_runs.csv'
 if extra.exists():n+=sum(1 for _ in csv.DictReader(extra.open()))
 print(f'Recorded post-review batches: {n}/{total} ({100*n/total:.1f}%)')
else:
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
 backup=ROOT/'rerun_backups'/stamp
 backup.mkdir(parents=True)
 for name in ('runs.csv','items.csv','probe_forecasts.csv','execution.log','default_equivalence.json','break_even_runs.csv','break_even_items.csv'):
  path=ROOT/'revision'/name
  if path.exists():shutil.copy2(path,backup/name)
 print(f'Preserved existing raw results at {backup}',flush=True)
 subprocess.run([sys.executable,'-m','src.revision_experiment','run'],cwd=ROOT,check=True)
 subprocess.run([sys.executable,'-m','src.revision_break_even'],cwd=ROOT,check=True)
 subprocess.run([sys.executable,'-m','src.revision_analysis'],cwd=ROOT,check=True)
