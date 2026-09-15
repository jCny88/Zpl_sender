#!/usr/bin/env python3
"""Create one Code 128 ZPL label for every row in a CSV file."""

import argparse
import csv
from pathlib import Path


def build_label(
    barcode: str,
    label_height: int,
    barcode_height: int | None,
    label_width: int,
    x: int,
    y: int,
) -> str:
    """Build one raw ZPL label containing a Code 128 barcode."""
    if not barcode:
        raise ValueError("Barcode values cannot be empty")
    if any(character in barcode for character in "^~"):
        raise ValueError(f"Barcode contains a ZPL control character: {barcode!r}")

    return (
        "^XA\n"
        "^MMC\n"
        f"^PW{label_width}\n"
        f"^LL{label_height}\n"
        "^LS0\n"
        f"^BY5,3{f',{barcode_height}' if barcode_height is not None else ''}"
        f"^FT{x},{y}^BCN,,Y,N\n"
        f"^FD>;{barcode}^FS\n"
        "^PQ1,1,1,Y\n"
        "^XZ\n"
    )


def read_barcodes(csv_path: Path, column: str, skip_header: bool) -> list[str]:
    with csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
        rows = csv.reader(csv_file)
        if skip_header:
            next(rows, None)

        barcodes = []
        for row_number, row in enumerate(rows, start=2 if skip_header else 1):
            if not row or not any(cell.strip() for cell in row):
                continue
            try:
                value = row[int(column)] if column.isdigit() else row[0]
            except (IndexError, ValueError) as error:
                raise ValueError(
                    f"Row {row_number} does not contain column {column!r}"
                ) from error
            barcodes.append(value.strip())
        return barcodes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create Code 128 ZPL labels from one CSV column"
    )
    parser.add_argument(
        "csv_file",
        type=Path,
        nargs="?",
        default=Path("barcodes.csv"),
        help="Input CSV file (default: barcodes.csv)",
    )
    parser.add_argument(
        "output_file",
        type=Path,
        nargs="?",
        default=Path("labels.zpl"),
        help="Output ZPL file (default: labels.zpl)",
    )
    parser.add_argument(
        "--label-height",
        type=int,
        default=400,
        help="Label height in printer dots (default: 400)",
    )
    parser.add_argument(
        "--barcode-height",
        type=int,
        default=300,
        help="Barcode height in printer dots (default: 300)",
    )
    parser.add_argument(
        "--column",
        default="0",
        help="Zero-based CSV column index; defaults to the first column",
    )
    parser.add_argument(
        "--skip-header",
        action="store_true",
        help="Skip the first CSV row",
    )
    parser.add_argument("--label-width", type=int, default=812)
    parser.add_argument("--x", type=int, default=50)
    parser.add_argument(
        "--y",
        type=int,
        default=350,
        help="Barcode top position in dots for a 4 inch continuous label",
    )
    args = parser.parse_args()

    if args.label_height <= 0 or (
        args.barcode_height is not None and args.barcode_height <= 0
    ):
        parser.error("--label-height and --barcode-height, when provided, must be positive")
    if args.label_width <= 0 or args.x < 0 or args.y < 0:
        parser.error("--label-width must be positive and --x/--y cannot be negative")

    labels = [
        build_label(
            barcode,
            args.label_height,
            args.barcode_height,
            args.label_width,
            args.x,
            args.y,
        )
        for barcode in read_barcodes(args.csv_file, args.column, args.skip_header)
    ]
    args.output_file.write_text("\n".join(labels), encoding="ascii")
    print(f"Created {len(labels)} labels in {args.output_file}")


if __name__ == "__main__":
    main()