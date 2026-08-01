# Zpl_sender

Python script to print labels on a Zebra ZD220 (203 dpi) from a Raspberry Pi, via CUPS raw printing.

## Requirements

- Printer set up in CUPS and reachable via `lp`
- Confirm the exact CUPS printer name:

```bash
lpstat -p
```

Expected output includes something like:

```
printer Zebra_Technologies_ZTC_ZD220-203dpi_ZPL is idle.
```

## Files

- `print_label.py` — main script
- `label_template.json` — label geometry + printer settings

## Usage

```bash
python print_label.py "Hello Julien"
```

Multi-line text:

```bash
python print_label.py $'Line one\nLine two\nLine three'
```

Custom template or printer:

```bash
python print_label.py "test" -t other_template.json -p Some_Other_Printer
```

## Template reference (`label_template.json`)

```json
{
  "dpi": 203,
  "width": {"value": 100, "unit": "mm"},
  "height": {"value": 152, "unit": "mm"},
  "x": {"value": 30, "unit": "dots"},
  "y": {"value": 30, "unit": "dots"},
  "font_size": {"value": 40, "unit": "dots"},
  "font": "0",
  "media_type": "gap",
  "darkness": 15,
  "print_speed": 4,
  "print_mode": "tear_off",
  "orientation": "normal"
}
```

### Dimension fields (`width`, `height`, `x`, `y`, `font_size`)

Each is an object: `{"value": X, "unit": Y}`. Supported units:

| Unit | Meaning |
|---|---|
| `in` | inches |
| `mm` | millimeters |
| `cm` | centimeters |
| `dots` / `px` | raw printer dots (no conversion) |

Units can be mixed freely between fields (e.g. label size in `mm`, offset in `dots`). All values are converted internally to dots at the given `dpi` (203 for ZD220).

### `font`

Selects the ZPL font used for text fields.

| Code | Style |
|---|---|
| `0` | Default scalable font (recommended — size fully controlled by `font_size`) |
| `A` | Fixed, 9×5 dots — smallest |
| `B` | Fixed, 11×7 |
| `D` | Fixed, 18×10 |
| `E` | OCR-B |
| `F` | 26×13, bold-ish |
| `G` | 60×40, large |

Rotation (`N`/`R`/`I`/`B` = 0°/90°/180°/270°) is currently hardcoded to `N` (normal) in the field command; not yet exposed in the template.

### `media_type`

Controls how the printer senses label boundaries (`^MN` command). Mismatched media type is the most common cause of label drift or double-feeding.

| JSON value | ZPL | Sensor | When to use |
|---|---|---|---|
| `gap` | `^MNY` | Transmissive (light through liner) | Standard die-cut labels with gaps between them — most common |
| `continuous` | `^MNN` | None (relies on `^LL` length) | Continuous roll, no gaps, cut manually |
| `mark` | `^MNM` | Reflective (black line on liner back) | Labels with a printed registration mark instead of a gap |

**How to check which stock you have:**
- Hold the roll to light — visible gap between labels → `gap`
- Black bar printed on the liner back at each boundary → `mark`
- One continuous strip, no separation → `continuous`

**To verify/calibrate on the printer itself:**

```bash
echo "^XA~JC^XZ" | lp -d Zebra_Technologies_ZTC_ZD220-203dpi_ZPL -o raw
```

This runs auto-calibration, measuring actual label/gap length and sensor type.

### `darkness`

Print darkness/burn level, `0`–`30`. Default `15`. Increase if print looks faint, decrease if labels look burnt or barcodes smear.

### `print_speed`

Print speed in inches/second. Typical range for ZD220: `2`–`6`. Default `4`. Lower speed generally improves quality for small text or barcodes.

### `print_mode`

| JSON value | ZPL |
|---|---|
| `tear_off` | `^MMT` — standard, pull to tear (default for base ZD220) |
| `peel_off` | `^MMP` — only relevant if a peel/liner mechanism is attached |

### `orientation`

Flips the **entire label** 180° (printer-level, `^PO` command) — different from per-field text rotation.

| JSON value | ZPL | Effect |
|---|---|---|
| `normal` | `^PON` | Standard |
| `inverted` | `^POI` | 180° flip — useful if labels print upside-down due to roll loading, or need to face the opposite direction |

## Notes / troubleshooting

- If printing does nothing or errors, first test raw ZPL directly to isolate CUPS vs script issues:

```bash
printf "^XA^FO50,50^A0N,40,40^FDtest^FS^XZ" | lp -d Zebra_Technologies_ZTC_ZD220-203dpi_ZPL -o raw
```

- `/dev/usb/lp0` is **not** used in this setup — printing goes through CUPS (`lp` command), not a raw device node.
- If labels drift, double-feed, or misalign, check `media_type` against actual label stock and re-run `~JC` calibration.

## Possible next steps

- Barcode support (`^BC` and similar)
- Per-field font/rotation control (not just label-level orientation)
- Custom downloaded fonts (TTF converted to Zebra format via `~DU`/`^CW`)
- Multi-field templates (e.g. name + date + barcode) instead of single text blob

