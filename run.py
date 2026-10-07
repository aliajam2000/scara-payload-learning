"""Portable command-line entry point; Python 3.12 recommended."""
import argparse
import json
from pathlib import Path
from src.experiment import METHODS, run_grid

ROOT=Path(__file__).resolve().parent

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('command',choices=['demo','development','benchmark','stress','analyze','verify','all'])
    ap.add_argument('--out',default=str(ROOT/'results'),help='Output directory; absolute or relative to current directory')
    args=ap.parse_args(); out=Path(args.out); c=json.loads((ROOT/'protocol.json').read_text())
    if args.command=='demo':
        rows=run_grid(out,[11],[5],['excited'],METHODS,name='demo')
        for r in rows: print(f"{r['method']:16s} success={r['success']} time={r['robot_time_s']:.3f}s probes={r['probes']}")
    if args.command=='development': run_grid(out,list(range(11,16)),[1,5],c['path_families'],METHODS,name='development')
    if args.command in ('benchmark','all'):
        run_grid(out,list(range(1001,1031)),c['batch_sizes'],c['path_families'],METHODS)
    if args.command in ('stress','all'):
        run_grid(out,list(range(2001,2011)),[5],c['path_families'],METHODS,fs=1.25,name='stress')
    if args.command in ('verify','all'):
        from src.validation import validate
        validate(out)
    if args.command in ('analyze','all'):
        from src.analysis import analyze
        analyze(out)

if __name__=='__main__': main()
