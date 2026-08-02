#!/usr/bin/env python3
import json
import argparse
import subprocess

PRINTER = "Zebra_Technologies_ZTC_ZD220-203dpi_ZPL"

UNITS_PER_INCH = {
    "in": 1.0,
    "mm": 1 / 25.4,
    "cm": 1 / 2.54,
}

MEDIA_TYPE_MAP = {
    "gap": "^MNY",       # web/gap sensing
    "continuous": "^MNN",  # continuous media, no gaps
    "mark": "^MNM",      # black mark sensing
}

PRINT_MODE_MAP = {
    "tear_off": "^MMT",
    "peel_off": "^MMP",
}

ORIENTATION_MAP = {
    "normal": "^PON",
    "inverted": "^POI",
}

ROTATION_MAP = {
    "normal": "^FWN",
    "R": "^FWR",
    "I": "^FWI",
    "B": "^FWB",
}

def to_dots(field, dpi):
    value = field["value"]
    unit = field["unit"].lower()
    if unit in ("dots", "px"):
        return int(round(value))
    if unit in UNITS_PER_INCH:
        return int(round(value * UNITS_PER_INCH[unit] * dpi))
    raise ValueError(f"Unsupported unit: {unit}")

def load_template(path="label_template.json"):
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

ROTATION_LETTER = {
    "normal": "N",
    "R": "R",
    "I": "I",
    "B": "B",
}

def build_zpl(text, tpl):
    lines = text.split("\\n")
    font = tpl.get("font", "0")
    font_size = tpl["font_size"]
    line_height = int(font_size * 1.3)
    rotation = tpl.get("rotation", "normal")
    rot_letter = ROTATION_LETTER.get(rotation, "N")

    # stacking axis depends on rotation direction
    if rotation == "normal":
        dx, dy = 0, line_height        # stack downward
    elif rotation == "R":
        dx, dy = line_height, 0        # stack rightward
    elif rotation == "B":
        dx, dy = -line_height, 0       # stack leftward
    elif rotation == "I":
        dx, dy = 0, -line_height       # stack upward
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
    subprocess.run(
        ["lp", "-d", printer, "-o", "raw"],
        input=zpl.encode("utf-8"),
        check=True,
    )

def main():
    parser = argparse.ArgumentParser(description="Print a ZPL label")
    parser.add_argument("text", help="Text to print on the label")
    parser.add_argument("-t", "--template", default="label_template.json")
    parser.add_argument("-p", "--printer", default=PRINTER)
    args = parser.parse_args()

    tpl = load_template(args.template)
    zpl = build_zpl(args.text, tpl)
    send(zpl, args.printer)
    print(f"Sent to {args.printer}:\n{zpl}")

if __name__ == "__main__":
    main()

