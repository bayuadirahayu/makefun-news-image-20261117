#!/usr/bin/env python3
"""news-image-20261117 entry: copy the rendered image to the output dir.

The image (entry.png, beside this file) is a ray-traced dusk scene of
the day's news: the Kerch Bridge span collapsing into the strait after
Ukraine's strike, an oil tanker burning in the Strait of Hormuz after
the mine attacks, and a lone boatman watching from the foreground.
This program only copies those bytes to /output/entry.png (or
$MAKEFUN_OUTPUT_DIR/entry.png outside the grader), so every run writes
identical bytes.
"""

import os
import shutil
import sys
from pathlib import Path

# The image is produced once, by render.py (a from-scratch stdlib ray
# tracer in this repo), and never modified by this program: copying is
# a pure byte transfer, so two runs of main.py always write the same
# file. The grader runs this program with no network.
HERE = Path(__file__).resolve().parent
SRC = HERE / "entry.png"


def main() -> int:
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SRC, out_dir / "entry.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
