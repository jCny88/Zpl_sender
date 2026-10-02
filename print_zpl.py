#!/usr/bin/env python3
"""Send a raw ZPL file to a macOS (CUPS) printer queue."""

import argparse
import subprocess
from pathlib import Path


DEFAULT_PRINTER = "Zebra_Technologies_ZTC_ZD220_203dpi_ZPL"  # CUPS queue name (see note below)


def print_zpl(data: bytes, printer_name: str) -> None:
    """Send raw ZPL bytes to a CUPS printer queue, bypassing any filtering."""
    result = subprocess.run(
        ["lp", "-d", printer_name, "-o", "raw"],
        input=data,
        capture_output=True,
    )
    if result.returncode != 0:
        raise OSError(
            f"lp failed (exit {result.returncode}): "
            f"{result.stderr.decode(errors='replace').strip()}"
        )
    print(result.stdout.decode(errors="replace").strip())


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a raw ZPL file to a CUPS printer")
    parser.add_argument(
        "file",
        nargs="?",
        type=Path,
        default=Path("labels.zpl"),
        help="ZPL file to print (default: labels.zpl)",
    )
    parser.add_argument("-p", "--printer", default=DEFAULT_PRINTER)
    args = parser.parse_args()

    data = args.file.read_bytes()
    print_zpl(data, args.printer)
    print(f"Queued {args.file} ({len(data)} bytes) on {args.printer}")


if __name__ == "__main__":
    main()