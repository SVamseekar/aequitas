"""Produce comparison evidence. Never automatically marks a screen verified.

Run via uv run --no-sync python frontend/scripts/design-compare.py --screen D01-01
Requires Pillow. Crop coordinates refer to the unchanged multi-view original.
"""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

parser = argparse.ArgumentParser()
parser.add_argument("--screen", required=True)
parser.add_argument("--phase", default="current")
args = parser.parse_args()
repo = Path(__file__).resolve().parents[2]
manifest = json.loads((repo / "design/screen-status.json").read_text())
screen = next(s for s in manifest["screens"] + manifest["supplemental"] if s["id"] == args.screen)
folder = repo / "implementation/evidence" / args.phase / args.screen
source = repo / screen["reference"]
reference = Image.open(source).convert("RGB")
if screen.get("referenceCrop"):
    reference = reference.crop(screen["referenceCrop"])
elif screen.get("viewsOnBoard", 1) > 1:
    raise SystemExit("Multi-view board needs inspected referenceCrop; do not compare whole board to one screen.")
rendered = Image.open(folder / "rendered.png").convert("RGB")
reference = reference.resize(rendered.size, Image.Resampling.LANCZOS)
reference.save(folder / "reference-crop.png")
Image.blend(reference, rendered, 0.5).save(folder / "overlay.png")
diff = ImageChops.difference(reference, rendered)
diff.save(folder / "difference.png")
(folder / "comparison.json").write_text(json.dumps({
    "reference": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "crop": screen.get("referenceCrop"), "renderedSize": rendered.size,
    "meanAbsoluteChannelDifference": ImageStat.Stat(diff).mean,
    "acceptance": "REQUIRES_INSPECTION", "note": "Resampled layout comparison; illustrative plots and actual analytics differ. No uncalibrated pass threshold."
}, indent=2) + "\n")
print(folder / "overlay.png")
