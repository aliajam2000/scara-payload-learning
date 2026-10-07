"""Check delivered file hashes using only Python's standard library.

Run before changing files: python verify_release.py
Extra local outputs are ignored. Missing/modified release files are reported.
"""
import hashlib
from pathlib import Path

root=Path(__file__).resolve().parent
bad=[];count=0
for line in (root/'MANIFEST_SHA256.txt').read_text().splitlines():
    expected,name=line.split('  ',1);p=root/name;count+=1
    if not p.is_file():bad.append(f'MISSING: {name}')
    elif hashlib.sha256(p.read_bytes()).hexdigest()!=expected:bad.append(f'CHANGED: {name}')
if bad:
    print('\n'.join(bad));raise SystemExit(1)
print(f'PASS: {count} release files match the SHA-256 manifest.')
