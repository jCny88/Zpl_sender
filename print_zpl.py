#!/usr/bin/env python3
"""Send a raw ZPL file to a Windows printer queue."""

import argparse
import ctypes
from ctypes import wintypes
from pathlib import Path


DEFAULT_PRINTER = "ZDesigner ZD621-203dpi ZPL"

winspool = ctypes.WinDLL("winspool.drv")


class DocInfo1(ctypes.Structure):
    _fields_ = [
        ("doc_name", wintypes.LPWSTR),
        ("output_file", wintypes.LPWSTR),
        ("data_type", wintypes.LPWSTR),
    ]


winspool.OpenPrinterW.argtypes = [
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.HANDLE),
    wintypes.LPVOID,
]
winspool.OpenPrinterW.restype = wintypes.BOOL
winspool.StartDocPrinterW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    ctypes.POINTER(DocInfo1),
]
winspool.StartDocPrinterW.restype = wintypes.DWORD
winspool.StartPagePrinter.argtypes = [wintypes.HANDLE]
winspool.StartPagePrinter.restype = wintypes.BOOL
winspool.WritePrinter.argtypes = [
    wintypes.HANDLE,
    wintypes.LPVOID,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
]
winspool.WritePrinter.restype = wintypes.BOOL
winspool.EndPagePrinter.argtypes = [wintypes.HANDLE]
winspool.EndPagePrinter.restype = wintypes.BOOL
winspool.EndDocPrinter.argtypes = [wintypes.HANDLE]
winspool.EndDocPrinter.restype = wintypes.BOOL
winspool.ClosePrinter.argtypes = [wintypes.HANDLE]
winspool.ClosePrinter.restype = wintypes.BOOL


def _check(result, operation):
    if not result:
        error_code = ctypes.get_last_error()
        raise OSError(error_code, f"{operation} failed", error_code)


def print_zpl(data: bytes, printer_name: str) -> None:
    printer_handle = wintypes.HANDLE()
    _check(
        winspool.OpenPrinterW(printer_name, ctypes.byref(printer_handle), None),
        f"Opening printer {printer_name!r}",
    )

    try:
        document = DocInfo1("ZPL label", None, "RAW")
        _check(
            winspool.StartDocPrinterW(printer_handle, 1, ctypes.byref(document)),
            "Starting print job",
        )
        try:
            _check(winspool.StartPagePrinter(printer_handle), "Starting print page")
            try:
                buffer = ctypes.create_string_buffer(data)
                bytes_written = wintypes.DWORD()
                _check(
                    winspool.WritePrinter(
                        printer_handle,
                        buffer,
                        len(data),
                        ctypes.byref(bytes_written),
                    ),
                    "Writing ZPL data",
                )
                if bytes_written.value != len(data):
                    raise OSError(
                        f"Only {bytes_written.value} of {len(data)} bytes were queued"
                    )
            finally:
                _check(winspool.EndPagePrinter(printer_handle), "Ending print page")
        finally:
            _check(winspool.EndDocPrinter(printer_handle), "Ending print job")
    finally:
        _check(winspool.ClosePrinter(printer_handle), "Closing printer")


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a raw ZPL file to a Windows printer")
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
    if not hasattr(ctypes, "WinDLL"):
        raise SystemExit("This script requires Windows.")
    main()