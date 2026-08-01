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
    }

def build_zpl(text, tpl):
    return f"""^XA
^PW{tpl['width_dots']}
^LL{tpl['height_dots']}
^FO{tpl['x']},{tpl['y']}
^A0N,{tpl['font_size']},{tpl['font_size']}
^FD{text}^FS
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
