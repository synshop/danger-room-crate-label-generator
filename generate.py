#!/usr/bin/env python3
"""Generate makerspace tool-crate label PDFs from a CSV file.

Usage:
    python generate.py tools.csv [--out out] [--icons icons] [--template template.html]

Each CSV row produces one 9"x5" landscape PDF in --out.
"""
import argparse
import csv
import re
import sys
from io import BytesIO
from pathlib import Path

import qrcode
import qrcode.image.svg
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML


CATEGORY_COLORS = {
    "power-saw":  "#c62828",  # red
    "sander":     "#ef6c00",  # orange
    "drill":      "#f9a825",  # yellow
    "hand-tool":  "#2e7d32",  # green
    "measuring":  "#1565c0",  # blue
    "specialty":  "#6a1b9a",  # purple
    "misc":       "#546e7a",  # gray
}

# CSV-key -> (icon-filename, display-label)
PPE_LIBRARY = {
    "ear":        ("ear.svg",        "EAR PROT."),
    "eye":        ("eye.svg",        "EYE PROT."),
    "gloves":     ("gloves.svg",     "GLOVES"),
    "facemask":   ("facemask.svg",   "FACE MASK"),
    "respirator": ("respirator.svg", "RESPIRATOR"),
    "faceshield": ("faceshield.svg", "FACE SHIELD"),
    "head":       ("head.svg",       "HARD HAT"),
    "foot":       ("foot.svg",       "STEEL TOE"),
}


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_-]+", "-", text).strip("-")
    return text


def make_qr_svg(url: str) -> str:
    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(url, image_factory=factory, box_size=10, border=2)
    buf = BytesIO()
    img.save(buf)
    return buf.getvalue().decode("utf-8")


def render_label(row: dict, out_dir: Path, template, icons_dir: Path) -> Path:
    color = CATEGORY_COLORS.get(row["category"], CATEGORY_COLORS["misc"])
    ppe_keys = [p.strip() for p in row["ppe"].split(",") if p.strip()]
    ppe_items = []
    for key in ppe_keys:
        if key not in PPE_LIBRARY:
            print(f"warn: unknown PPE '{key}' for {row['crate_id']}", file=sys.stderr)
            continue
        svg_file, label = PPE_LIBRARY[key]
        ppe_items.append({
            "label": label,
            "svg_path": (icons_dir / svg_file).resolve().as_uri(),
        })
    checklist = [c.strip() for c in row["checklist"].split("|") if c.strip()]
    qr_svg = make_qr_svg(row["manual_url"])

    html = template.render(
        tool_name=row["tool_name"],
        crate_id=row["crate_id"],
        manual_url=row["manual_url"],
        category=row["category"],
        category_color=color,
        ppe=ppe_items,
        checklist=checklist,
        qr_svg=qr_svg,
    )

    out_path = out_dir / f"{row['crate_id']}_{slugify(row['tool_name'])}.pdf"
    HTML(string=html, base_url=str(icons_dir.parent.resolve())).write_pdf(out_path)
    return out_path


def main():
    ap = argparse.ArgumentParser(description="Generate label PDFs from CSV")
    ap.add_argument("csv", type=Path)
    ap.add_argument("--out", type=Path, default=Path("out"))
    ap.add_argument("--icons", type=Path, default=Path("icons"))
    ap.add_argument("--template", type=Path, default=Path("template.html"))
    args = ap.parse_args()

    args.out.mkdir(exist_ok=True)
    env = Environment(loader=FileSystemLoader(args.template.parent or "."))
    template = env.get_template(args.template.name)

    with args.csv.open() as f:
        for row in csv.DictReader(f):
            path = render_label(row, args.out, template, args.icons)
            print(f"wrote {path}")


if __name__ == "__main__":
    main()
