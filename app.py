#!/usr/bin/env python3
import json
import glob
import os
import subprocess
from flask import Flask, render_template, request

app = Flask(__name__)

PRINTER = "Zebra_Technologies_ZTC_ZD220-203dpi_ZPL"
TEMPLATE_DIR = "templates_zpl"  # folder holding label_template*.json files

UNITS_PER_INCH = {"in": 1.0, "mm": 1 / 25.4, "cm": 1 / 2.54}

MEDIA_TYPE_MAP = {"gap": "^MNY", "continuous": "^MNN", "mark": "^MNM"}
PRINT_MODE_MAP = {"tear_off": "^MMT", "peel_off": "^MMP"}
ORIENTATION_MAP = {"normal": "^PON", "inverted": "^POI"}
ROTATION_LETTER = {"normal": "N", "R": "R", "I": "I", "B": "B"}


def to_dots(field, dpi):
    value = field["value"]
    unit = field["unit"].lower()
    if unit in ("dots", "px"):
        return int(round(value))
    if unit in UNITS_PER_INCH:
        return int(round(value * UNITS_PER_INCH[unit] * dpi))
    raise ValueError(f"Unsupported unit: {unit}")


def list_templates():
    """Return available template filenames (without path) from TEMPLATE_DIR."""
    paths = glob.glob(os.path.join(TEMPLATE_DIR, "*.json"))
    return sorted(os.path.basename(p) for p in paths)


def load_template(filename):
    path = os.path.join(TEMPLATE_DIR, filename)
    with open(path) as f:
        tpl = json.load(f)
    dpi = tpl["dpi"]
    return {
        "dpi": dpi,
        "width_dots": to_dots(tpl["width"], dpi),
        "height_dots": to_dots(tpl["height"], dpi),
        "x": to_dots(tpl["x"], dpi),
        "y": to_dots(tpl["y"], dpi),
        "font_size": to_dots(tpl["font_size"], dpi),
        "font": tpl.get("font", "0"),
        "media_type": tpl.get("media_type", "gap"),
        "darkness": tpl.get("darkness", 15),
        "print_speed": tpl.get("print_speed", 4),
        "print_mode": tpl.get("print_mode", "tear_off"),
        "orientation": tpl.get("orientation", "normal"),
        "rotation": tpl.get("rotation", "normal"),
    }


def build_zpl(text, tpl):
    lines = text.split("\n")
    font = tpl["font"]
    font_size = tpl["font_size"]
    line_height = int(font_size * 1.3)
    rotation = tpl["rotation"]
    rot_letter = ROTATION_LETTER.get(rotation, "N")

    if rotation == "normal":
        dx, dy = 0, line_height
    elif rotation == "R":
        dx, dy = -line_height, 0
    elif rotation == "B":
        dx, dy = line_height, 0
    elif rotation == "I":
        dx, dy = 0, line_height
    else:
        dx, dy = 0, line_height

    fields = []
    for i, line in enumerate(lines):
        x = tpl["x"] + i * dx
        y = tpl["y"] + i * dy
        fields.append(f"^FO{x},{y}^A{font}{rot_letter},{font_size},{font_size}^FD{line}^FS")
    body = "\n".join(fields)

    media_cmd = MEDIA_TYPE_MAP.get(tpl["media_type"], "^MNY")
    mode_cmd = PRINT_MODE_MAP.get(tpl["print_mode"], "^MMT")
    orient_cmd = ORIENTATION_MAP.get(tpl["orientation"], "^PON")

    return f"""^XA
^PW{tpl['width_dots']}
^LL{tpl['height_dots']}
{media_cmd}
^MD{tpl['darkness']}
^PR{tpl['print_speed']}
{mode_cmd}
{orient_cmd}
{body}
^XZ"""


def send(zpl, printer=PRINTER):
    subprocess.run(["lp", "-d", printer, "-o", "raw"], input=zpl.encode("utf-8"), check=True)


@app.route("/", methods=["GET", "POST"])
def index():
    message = None
    error = None
    templates = list_templates()
    selected_template = request.form.get("template") or (templates[0] if templates else None)
    text_value = request.form.get("text", "")

    if request.method == "POST":
        try:
            if not selected_template:
                raise RuntimeError("No template files found in templates_zpl/")
            tpl = load_template(selected_template)
            zpl = build_zpl(text_value, tpl)
            send(zpl)
            message = f"Sent to printer using {selected_template}"
        except Exception as e:
            error = str(e)

    return render_template(
        "index.html",
        templates=templates,
        selected_template=selected_template,
        text_value=text_value,
        message=message,
        error=error,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
