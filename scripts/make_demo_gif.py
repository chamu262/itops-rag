"""Record docs/img/demo.gif from real CLI runs (no API key needed).

Runs each command for real against a fresh temporary index, captures its output, then renders a terminal-style
animation (typed command, then the output) with Pillow. Nothing in the frames is hand-written.

    python scripts/make_demo_gif.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "img" / "demo.gif"
CLI = str(Path(sys.executable).with_name("itops-rag"))

COLS, ROWS = 96, 24
FONT_SIZE, PAD = 15, 18
BG, FG, PROMPT, DIM = (24, 26, 31), (220, 223, 228), (120, 190, 140), (140, 148, 160)


def font() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in ("/System/Library/Fonts/Menlo.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, FONT_SIZE)
    return ImageFont.load_default()


def run(args: list[str], index: str) -> str:
    env = {
        **os.environ,
        "COLUMNS": str(COLS - 2),
        "TERM": "dumb",
        "NO_COLOR": "1",
        "ITOPS_RAG_INDEX_DIR": index,
    }
    res = subprocess.run([CLI, *args], capture_output=True, text=True, env=env, cwd=ROOT, check=True)
    return res.stdout.rstrip()


def render(
    lines: list[tuple[str, tuple[int, int, int]]], f: ImageFont.FreeTypeFont | ImageFont.ImageFont
) -> Image.Image:
    cw = int(f.getlength("M"))
    lh = FONT_SIZE + 5
    img = Image.new("RGB", (cw * COLS + 2 * PAD, lh * ROWS + 2 * PAD + 22), BG)
    d = ImageDraw.Draw(img)
    for i, color in enumerate(((237, 106, 94), (245, 191, 79), (98, 197, 84))):
        d.ellipse((PAD + i * 20, 10, PAD + i * 20 + 11, 21), fill=color)
    for row, (text, color) in enumerate(lines[-ROWS:]):
        d.text((PAD, PAD + 22 + row * lh), text, font=f, fill=color)
    return img


def main() -> None:
    f = font()
    with tempfile.TemporaryDirectory() as tmp:
        index = str(Path(tmp) / "index")
        steps = [
            (
                ["ingest", "data/demo/kestrel-cloud", "--store", "sqlite"],
                "itops-rag ingest data/demo/kestrel-cloud",
            ),
            (
                ["search", "AADSTS53003 blocked sign-in", "-k", "4"],
                'itops-rag search "AADSTS53003 blocked sign-in" -k 4',
            ),
            (
                ["ask", "How do I upgrade our Kubernetes cluster to 1.31?"],
                'itops-rag ask "How do I upgrade our Kubernetes cluster to 1.31?"',
            ),
            (["eval"], "itops-rag eval"),
        ]
        frames: list[Image.Image] = []
        durations: list[int] = []
        for args, shown in steps:
            output = run(args, index)
            screen: list[tuple[str, tuple[int, int, int]]] = []
            for n in range(0, len(shown) + 1, 3):
                frames.append(render([*screen, ("$ " + shown[:n] + "▌", PROMPT)], f))
                durations.append(45)
            screen.append(("$ " + shown, PROMPT))
            out_lines = [ln[: COLS - 1] for ln in output.splitlines()]
            for n in range(1, len(out_lines) + 1, 2):
                frames.append(render(screen + [(ln, FG) for ln in out_lines[:n]], f))
                durations.append(60)
            frames.append(render(screen + [(ln, FG) for ln in out_lines] + [("", DIM)], f))
            durations.append(2600)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=True)
    print(f"wrote {OUT.relative_to(ROOT)} ({len(frames)} frames, {OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
