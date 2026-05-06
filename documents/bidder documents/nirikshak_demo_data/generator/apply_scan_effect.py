#!/usr/bin/env python3
"""
Scan-effect pipeline.

Takes a clean PDF (one our generator produced) and applies a "scan look":
- Rasterise pages at moderate DPI
- Apply slight rotation (0.5-2 degrees)
- Add gaussian noise and blur
- Convert to grayscale
- Recompress as JPEG (lossy)
- Reassemble as PDF

The result LOOKS like a low-quality fax/photocopy. This is what bidder_03's
turnover cert needs to exercise the system's OCR-confidence-gated routing
to Needs Review.

Usage:
    python3 apply_scan_effect.py <input.pdf> <output.pdf> [--severity light|medium|heavy]

Default severity is "medium". Use "heavy" for the bidder_03 smudged cert.
"""

import argparse
import random
import subprocess
import sys
import tempfile
from pathlib import Path

SEVERITY_PRESETS = {
    "light":  {"rotate_max": 0.8, "noise": 0.6, "blur": "0x0.5", "quality": 70, "dpi": 150},
    "medium": {"rotate_max": 1.5, "noise": 1.2, "blur": "0x0.8", "quality": 55, "dpi": 130},
    "heavy":  {"rotate_max": 2.5, "noise": 2.0, "blur": "0x1.2", "quality": 40, "dpi": 110},
}


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, **kw)


def apply_scan_effect(input_pdf: Path, output_pdf: Path, severity: str = "medium",
                      seed: int = None) -> None:
    if severity not in SEVERITY_PRESETS:
        sys.exit(f"Unknown severity: {severity}. Choose from: {list(SEVERITY_PRESETS)}")
    cfg = SEVERITY_PRESETS[severity]

    rng = random.Random(seed if seed is not None else hash(str(input_pdf)))

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)

        # 1. Rasterise PDF to images at the chosen DPI
        run([
            "pdftoppm", "-r", str(cfg["dpi"]), "-jpeg",
            str(input_pdf), str(td_path / "page"),
        ])

        page_files = sorted(td_path.glob("page-*.jpg"))
        if not page_files:
            sys.exit(f"No pages extracted from {input_pdf}")

        processed_files = []
        for i, page in enumerate(page_files):
            # Random per-page rotation in [-rotate_max, +rotate_max]
            rotate = rng.uniform(-cfg["rotate_max"], cfg["rotate_max"])
            # Random per-page brightness shift
            brightness = rng.uniform(-3, 3)

            out = td_path / f"scanned-{i:03d}.jpg"
            cmd = [
                "convert", str(page),
                "-colorspace", "Gray",                       # convert to grayscale
                "-rotate", f"{rotate:.2f}",                 # slight rotation
                "-background", "white", "-flatten",          # white border after rotation
                "-blur", cfg["blur"],                        # blur (mild)
                "-attenuate", str(cfg["noise"]),
                "+noise", "Gaussian",                        # gaussian noise
                "-modulate", f"{100 + brightness:.0f},90",  # slight brightness/sat
                "-quality", str(cfg["quality"]),             # JPEG compression
                str(out),
            ]
            run(cmd)
            processed_files.append(out)

        # 2. Reassemble JPEGs back into a PDF
        cmd = ["convert"] + [str(p) for p in processed_files] + [str(output_pdf)]
        run(cmd)


def main():
    ap = argparse.ArgumentParser(description="Apply scan-effect to a PDF.")
    ap.add_argument("input", help="Input clean PDF")
    ap.add_argument("output", help="Output scan-look PDF")
    ap.add_argument("--severity", default="medium",
                    choices=list(SEVERITY_PRESETS),
                    help="Scan-effect intensity (default: medium)")
    ap.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    args = ap.parse_args()

    in_path = Path(args.input).resolve()
    out_path = Path(args.output).resolve()
    if not in_path.exists():
        sys.exit(f"Input not found: {in_path}")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Applying scan effect ({args.severity}) → {out_path}")
    apply_scan_effect(in_path, out_path, args.severity, args.seed)
    print("Done.")


if __name__ == "__main__":
    main()
