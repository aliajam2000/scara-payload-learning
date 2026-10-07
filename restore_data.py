"""Restore the losslessly compressed publication data (Python standard library)."""
from pathlib import Path
import gzip
import hashlib

ROOT = Path(__file__).resolve().parent
EXPECTED_SHA256 = "db73661a9112ddf401b2f407b1cefe9827766f06612877bba98e38c0406ebf06"

def restore():
    target = ROOT / "revision/items.csv"
    if target.exists():
        return  # Preserve locally regenerated experimental data.
    archive = ROOT / "revision/items.csv.gz"
    if not archive.exists():
        raise FileNotFoundError(archive)
    data = gzip.decompress(archive.read_bytes())
    if hashlib.sha256(data).hexdigest() != EXPECTED_SHA256:
        raise ValueError("Compressed per-item data failed SHA-256 verification")
    temporary = target.with_suffix(".csv.tmp")
    temporary.write_bytes(data)
    temporary.replace(target)
    print("Restored revision/items.csv; SHA-256 verified.")

if __name__ == "__main__":
    restore()
