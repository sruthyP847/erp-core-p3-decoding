"""Download ERP CORE P3 BIDS subjects from OSF via the OSF API.

Pulls subject folders from "P3 Raw Data BIDS-Compatible" in the P3 component
(node etdkz) of the ERP CORE project (thsqg) into data/, checking each file's
size and MD5 against what the API reports. Files already present and intact
are skipped.

    python osf_download.py            # sub-002 to sub-010
    python osf_download.py 11 40      # sub-011 to sub-040
"""

import hashlib
import json
import ssl
import sys
import time
import urllib.request
from pathlib import Path

try:
    # python.org builds on macOS ship without CA certificates
    import certifi

    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = ssl.create_default_context()

BIDS_FOLDER = "https://api.osf.io/v2/nodes/etdkz/files/osfstorage/60077b04ba010908a78927e9/"
DATA_DIR = Path("data")


def get_json(url):
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=60, context=SSL_CONTEXT) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            print(f"  retry {attempt + 1} for {url}: {e}")
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"failed: {url}")


def listing(url):
    """All entries of an OSF folder, following pagination."""
    url += "?page%5Bsize%5D=100"
    while url:
        page = get_json(url)
        yield from page["data"]
        url = page["links"].get("next")


def walk(url, rel=Path()):
    """Yield (relative path, file entry) for every file under a folder."""
    for entry in listing(url):
        a = entry["attributes"]
        if a["kind"] == "folder":
            yield from walk(entry["relationships"]["files"]["links"]["related"]["href"], rel / a["name"])
        else:
            yield rel / a["name"], entry


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(entry, dest):
    a = entry["attributes"]
    want_md5 = a["extra"]["hashes"]["md5"]
    if dest.exists() and dest.stat().st_size == a["size"] and md5(dest) == want_md5:
        return "already present"
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(
                entry["links"]["download"], timeout=120, context=SSL_CONTEXT
            ) as r, open(tmp, "wb") as f:
                while chunk := r.read(1 << 20):
                    f.write(chunk)
            if tmp.stat().st_size == a["size"] and md5(tmp) == want_md5:
                tmp.rename(dest)
                return "downloaded"
            print(f"  checksum/size mismatch for {dest.name}, retrying")
        except Exception as e:  # noqa: BLE001
            print(f"  retry {attempt + 1} for {dest.name}: {e}")
            time.sleep(3 * (attempt + 1))
    tmp.unlink(missing_ok=True)
    return "FAILED"


def main():
    first, last = (int(a) for a in sys.argv[1:3]) if len(sys.argv) == 3 else (2, 10)
    subjects = [f"sub-{i:03d}" for i in range(first, last + 1)]

    folders = {
        e["attributes"]["name"]: e["relationships"]["files"]["links"]["related"]["href"]
        for e in listing(BIDS_FOLDER)
        if e["attributes"]["kind"] == "folder"
    }
    manifest = {}
    for sub in subjects:
        if sub not in folders:
            print(f"{sub}: NOT ON OSF")
            continue
        for rel, entry in walk(folders[sub], Path(sub)):
            status = download(entry, DATA_DIR / rel)
            a = entry["attributes"]
            manifest[str(rel)] = {"size": a["size"], "md5": a["extra"]["hashes"]["md5"], "status": status}
            print(f"{rel}  {a['size']:>10d}  {status}", flush=True)
    failed = [k for k, v in manifest.items() if v["status"] == "FAILED"]
    print(f"\n{len(manifest)} files, {len(failed)} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
