#!/usr/bin/env python3
"""Send a ZPL file to a labeler REST API using YAML configuration."""

import argparse
import base64
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import yaml


DEFAULTS = {
    "zpl_file": "labels.zpl",
    "labeler_ip": 6,
    "labeler_name": "OLPNLabeler",
    "labeler_number": 1,
    "dry_run": False,
    "drop_header_lines": 0,
}
ALLOWED_KEYS = {*DEFAULTS, "exotec_id"}
ALLOWED_LABELER_IPS = {6, 7, 8, 9}
ALLOWED_LABELER_NAMES = {"OLPNLabeler", "ShippingLabeler"}
ALLOWED_LABELER_NUMBERS = {1, 2}
PARIS_TZ = ZoneInfo("Europe/Paris")
REQUEST_TIMEOUT_SECONDS = 5


class ConfigurationError(ValueError):
    """Raised when configuration values are missing or invalid."""


class UnexpectedHTTPStatusError(Exception):
    """Raised when the labeler returns a status other than HTTP 200."""


def load_config(config_path: Path) -> tuple[dict[str, Any], Path]:
    try:
        with config_path.open("r", encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file)
    except yaml.YAMLError as error:
        raise ConfigurationError(f"Invalid YAML in {config_path}: {error}") from error
    except UnicodeError as error:
        message = f"Configuration file is not valid UTF-8: {config_path}"
        raise ConfigurationError(message) from error

    if not isinstance(config, dict):
        raise ConfigurationError("The YAML document must contain a mapping.")

    unknown_keys = set(config) - ALLOWED_KEYS
    if unknown_keys:
        unknown = ", ".join(sorted(str(key) for key in unknown_keys))
        raise ConfigurationError(f"Unknown configuration key(s): {unknown}")

    settings = {**DEFAULTS, **config}
    for key in ("zpl_file", "labeler_name", "exotec_id"):
        if not isinstance(settings[key], str) or not settings[key].strip():
            raise ConfigurationError(f"{key} must be a non-empty string.")

    for key, allowed_values in (
        ("labeler_ip", ALLOWED_LABELER_IPS),
        ("labeler_number", ALLOWED_LABELER_NUMBERS),
    ):
        value = settings[key]
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value not in allowed_values
        ):
            allowed = ", ".join(str(item) for item in sorted(allowed_values))
            raise ConfigurationError(f"{key} must be one of: {allowed}.")

    if (
        not isinstance(settings["labeler_name"], str)
        or settings["labeler_name"] not in ALLOWED_LABELER_NAMES
    ):
        allowed = ", ".join(sorted(ALLOWED_LABELER_NAMES))
        raise ConfigurationError(f"labeler_name must be one of: {allowed}.")

    if not isinstance(settings["dry_run"], bool):
        raise ConfigurationError("dry_run must be true or false.")

    drop_header_lines = settings["drop_header_lines"]
    if type(drop_header_lines) is not int or drop_header_lines < 0:
        raise ConfigurationError("drop_header_lines must be a non-negative integer.")

    config_dir = config_path.parent
    zpl_file = Path(settings["zpl_file"])
    if not zpl_file.is_absolute():
        zpl_file = config_dir / zpl_file

    return settings, zpl_file


def drop_header_lines(zpl_bytes: bytes, line_count: int) -> bytes:
    if line_count == 0:
        return zpl_bytes

    lines = zpl_bytes.splitlines(keepends=True)
    if line_count >= len(lines):
        raise ConfigurationError(
            f"drop_header_lines ({line_count}) would remove all ZPL data."
        )
    return b"".join(lines[line_count:])


def build_request(settings: dict[str, Any], zpl_bytes: bytes) -> tuple[str, dict[str, Any]]:
    module_name = f"{settings['labeler_name']}0{settings['labeler_number']}"
    request_time = datetime.now(PARIS_TZ)
    url = (
        f"http://172.23.0.7{settings['labeler_ip']}/"
        f"{module_name}/label/request"
    )
    payload = {
        "Header": {
            "Date": request_time.date().isoformat(),
            "ModuleName": module_name,
            "Type": "LabelRequest",
        },
        "RequestID": request_time.isoformat(),
        "Container": {
            "ExotecID": settings["exotec_id"],
            "BarcodeList": [],
        },
        "Label": base64.b64encode(zpl_bytes).decode("ascii"),
        "ControlLabelBarcode": "",
    }
    return url, payload


def send_request(url: str, payload: dict[str, Any]) -> None:
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        if response.status != 200:
            raise UnexpectedHTTPStatusError(
                f"Labeler returned unexpected HTTP status {response.status}."
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Send a ZPL file to a labeler using a YAML configuration file."
    )
    parser.add_argument("config", type=Path, help="YAML configuration file")
    args = parser.parse_args(argv)
    config_path = args.config.resolve()

    try:
        settings, zpl_file = load_config(config_path)
        zpl_bytes = zpl_file.read_bytes()
        zpl_bytes = drop_header_lines(zpl_bytes, settings["drop_header_lines"])
        url, payload = build_request(settings, zpl_bytes)
    except (ConfigurationError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    if settings["dry_run"]:
        print("DRY RUN: no HTTP request sent.")
        print(f"POST {url}")
        print(json.dumps(payload, indent=2))
        return 0

    try:
        send_request(url, payload)
    except HTTPError as error:
        message = f"Error: labeler returned HTTP {error.code}: {error.reason}"
        print(message, file=sys.stderr)
        return 1
    except UnexpectedHTTPStatusError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except (URLError, TimeoutError, OSError) as error:
        print(f"Error: request to labeler failed: {error}", file=sys.stderr)
        return 1

    print(f"Label request accepted by {url} (HTTP 200 OK).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
