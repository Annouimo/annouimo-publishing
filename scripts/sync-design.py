"""Fetch the design commit locked by this repository before building."""
import io
import json
from pathlib import Path
import re
import shutil
import tarfile
import tempfile
import urllib.request

root = Path(__file__).resolve().parents[1]
commit = (root / "design.lock").read_text().strip()
if not re.fullmatch(r"[0-9a-f]{40}", commit):
    raise SystemExit("design.lock must contain a full commit SHA")
target = root / ".shared-design"
if (target / ".revision").exists() and (target / ".revision").read_text() == commit:
    raise SystemExit(0)
url = f"https://codeload.github.com/Annouimo/annouimo-home/tar.gz/{commit}"
with urllib.request.urlopen(url, timeout=45) as response:
    archive = response.read()
with tempfile.TemporaryDirectory(dir=root) as directory:
    stage = Path(directory) / "design"
    stage.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
        for member in bundle.getmembers():
            parts = Path(member.name).parts
            if len(parts) < 3 or parts[1] != "design" or not member.isfile():
                continue
            relative = Path(*parts[2:])
            if relative.is_absolute() or ".." in relative.parts:
                raise SystemExit("Invalid design archive path")
            destination = stage / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(bundle.extractfile(member).read())
    for name in ["tokens.css", "navigation.css", "sites.json"]:
        if not (stage / name).is_file():
            raise SystemExit(f"Missing shared file: {name}")
    json.loads((stage / "sites.json").read_text())
    (stage / ".revision").write_text(commit)
    if target.exists():
        shutil.rmtree(target)
    stage.rename(target)
