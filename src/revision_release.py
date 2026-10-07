"""Integrity gates for the frozen post-review experiment and accounting."""
import csv,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def verify():
 protocol=json.loads((ROOT/'revision/post_review_protocol.json').read_text())
 original=json.loads((ROOT/'results/frozen_protocol.json').read_text())
 refinement=json.loads((ROOT/'revision/break_even_protocol.json').read_text())
 hashes={**original['sha256'],**protocol['hashes'],**refinement['hashes']}
 checks={'frozen_code_and_protocol_hashes':all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in hashes.items())}
 rows=list(csv.DictReader((ROOT/'revision/runs.csv').open()))
 rows+=list(csv.DictReader((ROOT/'revision/break_even_runs.csv').open()))
 key=lambda r:(r['group'],r['setting'],r['family'],int(r['N']),int(r['seed']),r['method'])
 expected={(j['group'],j['setting'],j['family'],j['N'],seed,m) for j in protocol['jobs'] for seed in j['seeds'] for m in j['methods']}
 expected|={('break_even','noise10',refinement['family'],N,seed,m) for N in refinement['N'] for seed in refinement['seeds'] for m in refinement['methods']}
 keys=[key(r) for r in rows];checks['complete_unique_design']=len(keys)==len(set(keys)) and set(keys)==expected
 checks['expected_6050_batches']=len(rows)==6050
 checks['finite_scoring']=all(all(math.isfinite(float(r[k])) for k in ('robot_time_s','planning_s','J','max_acceleration_ratio','max_velocity_ratio')) for r in rows)
 checks['time_decomposition']=all(abs(float(r['robot_time_s'])-sum(float(r[k+'_s']) for k in ('grasp','probe','loaded','release','returning')))<1e-9 for r in rows)
 checks['cost_accounting']=all(abs(float(r['J'])-float(r['robot_time_s'])-float(r['planning_s'])-10*(int(r['N'])-int(r['completed'])))<1e-9 for r in rows)
 checks['completion_flags']=all(int(r['success'])==int(int(r['completed'])==int(r['N'])) for r in rows)
 maps={key(r):r for r in rows};max_time=0.;same=True
 for r in rows:
  if r['method']=='oracle':continue
  chosen='always_probe' if int(r['probes']) else 'passive'
  q=maps[(*key(r)[:-1],chosen)]
  max_time=max(max_time,abs(float(r['robot_time_s'])-float(q['robot_time_s'])))
  same=same and r['completed']==q['completed'] and r['success']==q['success']
 checks['chosen_action_matches_paired_execution']=same and max_time<1e-9
 v=json.loads((ROOT/'revision/numerics/validation.json').read_text());checks['numerical_model_checks']=v['status']=='PASS'
 e=json.loads((ROOT/'revision/default_equivalence.json').read_text());checks['default_equivalence']=all(all(x['checks'].values()) for x in e)
 report=dict(status='PASS' if all(checks.values()) else 'FAIL',checks=checks,rows=len(rows),max_chosen_action_time_discrepancy_s=max_time,
             scope='Synthetic data integrity and numerical consistency; not physical validation or conference acceptance.')
 (ROOT/'revision/release_checks.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
 if report['status']!='PASS':raise RuntimeError('Revision integrity verification failed')
if __name__=='__main__':verify()
