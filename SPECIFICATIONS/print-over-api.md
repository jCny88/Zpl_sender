

# Specification: Send ZPL to a Labeler REST API

## Purpose

Define a Python command-line script that reads a YAML configuration file, reads
the configured ZPL file, Base64-encodes its contents, and submits a label
request to the configured labeler over HTTP.

## Input and configuration

- The script takes exactly one command-line argument: the path to a YAML
  configuration file. It must not expose other command-line options; runtime
  inputs belong in the YAML file.
- Example invocation: `python send_zpl.py config.yaml`.
- The configuration file path is resolved relative to the current working
  directory. The `zpl_file` path in the configuration is resolved relative to
  the directory containing that configuration file; absolute paths are also
  accepted.
- The configuration contains:
  - `zpl_file`: path to the input ZPL file. Defaults to `labels.zpl` in the
    configuration file's directory when omitted.
  - `labeler_ip`: final octet suffix of the labeler host. Defaults to `6`;
    allowed values are `6`, `7`, `8`, or `9`.
  - `labeler_name`: defaults to `OLPNLabeler`; allowed values are
    `OLPNLabeler` or `ShippingLabeler`.
  - `labeler_number`: defaults to `1`; allowed values are `1` or `2`.
  - `exotec_id`: required text value to populate `Container.ExotecID`; any
    text is acceptable.
  - `dry_run`: defaults to `false`. When `true`, print the request URL and JSON
    body without making an HTTP request.
  - `drop_header_lines`: defaults to `0`. Drop this many leading physical
    lines from the ZPL file before Base64 encoding; the value must be a
    non-negative integer and must not remove all label data.
- Configuration must be parsed safely (without constructing arbitrary Python
  objects). Reject invalid YAML, a non-mapping root value, invalid option
  values, and unreadable input files with a clear error and non-zero exit
  status.
- The labeler module name is formed as
  `{labeler_name}0{labeler_number}` (for example, `OLPNLabeler01`).
- `RequestID` does not need to be unique. Populate it with a timestamp to help
  correlate and debug requests, formatted as an ISO 8601 timestamp in the
  Europe/Paris timezone.

### Configuration example

```yaml
zpl_file: labels.zpl
labeler_ip: 6
labeler_name: OLPNLabeler
labeler_number: 1
exotec_id: testtest
dry_run: true
drop_header_lines: 0
```

Omitted optional settings use the defaults listed above. `zpl_file` may also
be omitted to use `labels.zpl` next to the configuration file. `exotec_id`
must be provided.

## HTTP request

- Method: `POST`
- Content type: `application/json`
- URL template:

  `http://172.23.0.7{labeler_ip}/{labeler_name}0{labeler_number}/label/request`

- Example with default settings:
  `http://172.23.0.76/OLPNLabeler01/label/request`
- The request body must be JSON with the structure shown below.
- `Label` contains the input ZPL bytes encoded using standard Base64 and
  represented as an ASCII string. Do not decode, transform, or reformat the ZPL
  before encoding it.
- `Header.Date` is the current date in the Europe/Paris timezone, formatted as
  `YYYY-MM-DD`.
- `Container.BarcodeList` and `ControlLabelBarcode` remain empty, as shown in
  the example payload.
- Use a 5-second request timeout. Do not retry failed requests.
- Treat HTTP `200 OK` as success. The observed success response has no body
  (`Content-Length: 0`).

## Request body example


```json
{
   "Header":{
       "Date": "<current date in Europe/Paris, YYYY-MM-DD>",
       "ModuleName": "{{labeler_name}}0{{labeler_number}}",
       "Type": "LabelRequest"
    },
    "RequestID" : "<ISO 8601 timestamp in Europe/Paris>",
    "Container":{
        "ExotecID": "<any text value>",
        "BarcodeList": []
    },
    "Label": "XlhBXkRGWVNISVBQLTFeTEwxMTYwXlBXODE2XkxTMF5GTzY3OCwzOTFeR0IxMTIsNzk1LDFeRlNeRk81MTUsMzkxXkdCMTYzLDc5NSwxXkZTXkZPMzM5LDM5MV5HQjE3OCw3OTUsMV5GU15GTzU4LDM5MV5HQjI4MSw3OTUsMV5GU15GTzYzOSw5XkdCMTUxLDM4MiwxXkZTXkZPNTU2LDEzOV5HQjgzLDI1MywxXkZTXkZPNDcyLDEzOV5HQjg1LDI1MiwxXkZTXkZPMzg3LDEzOF5HQjg1LDI1MywxXkZTXkZPMzA0LDEzOV5HQjg1LDI1MywxXkZTXkZPMjIxLDEzOV5HQjg0LDI1MiwxXkZTXkZPNTksOV5HQjE2MSwzODIsMV5GU15GTzUsOF5HQjUzLDExNzgsMV5GU15GTzY0LDM5NF5HQjMsMiwxXkZTXkZUNjkzLDEwM15BMEIsNTksNTVeRkhcXF5GTjYwNl5GU15GTzYwNiw0MDFeR0I2NCw5Miw2NF5GU15GVDY1Nyw0OTNeQTBCLDUxLDQ4XkZSXkZIXFxeRk42MDReRlNeRk80NzYsMTM4XkdCNzQsMTIyLDc0XkZTXkZUNTM1LDI2MF5BMEIsNTksNTVeRlJeRkhcXF5GTjYwNV5GU15GTzEwNCwxNF5HQjY0LDEwNiw2NF5GU15GVDE1NSwxMjBeQTBCLDUxLDQ4XkZSXkZIXFxeRk45NjdeRlNeRk8xMDgsMTU5XkdCNjEsMjI1LDYxXkZTXkZUMTU2LDM4NF5BMEIsNDgsMzNeRlJeRkhcXF5GTjk4M15GU15GVDIwNSwxOTFeQTBCLDI4LDI4XkZIXFxeRk45ODReRlNeRlQ1NDYsMzc3XkEwQiwyOCwyOF5GSFxcXkZOOTc3XkZTXkZUNTA3LDM3OF5BMEIsMjgsMjheRkhcXF5GTjk3OF5GU15GVDkzLDE0OF5BMEIsMjgsMjheRkhcXF5GTjYwM15GU15GVDkzLDM4M15BMEIsMjgsMjheRkhcXF5GTjYwMV5GU15GVDIwNiwzODJeQTBCLDMxLDI0XkZIXFxeRk45NjheRlNeRlQzNzIsMzUwXkEwQiw3OSw3OV5GSFxcXkZOOTY2XkZTXkZPMjEyLDE5Nl5HQjk5LDE1Miw5OV5GU15GVDI5MSwzNDheQTBCLDc5LDc5XkZSXkZIXFxeRk45NzBeRlNeRlQ2MTgsMjk5XkEwQiw1MSw1MF5GSFxcXkZOOTk5XkZTXkZUNDEwLDM4NF5BQUIsMTgsMTBeRkhcXF5GRF5GU15GVDczMSwzODZeQTBCLDI4LDI4XkZIXFxeRk45ODFeRlNeRlQ1NDgsNDYyXkEwQiwyOCwyOF5GSFxcXkZOOTg4XkZTXkZUNTQ4LDQ3N15BMEIsMjgsMjheRkhcXF5GRC9eRlNeRlQ1NTAsNTI0XkEwQiwyOCwyOF5eRkhcXF5GTjk4OV5GU15GVDU5NCw1NDleQTBCLDM5LDM4XkZIXFxeRk45NTBeRlNeRlQ3ODYsNDUwXkEwQiwyOCwyOF5GSFxcXkZOOTgyXkZTXkZUNzU2LDU1NV5BMEIsMjgsMjheRkhcXF5GTjk5MV5GU15GVDc1NCw1NTZeQTBCLDI4LDI4XkZIXFxeRk45OTBeRlNeRlQ3NTAsMTAyNV5BMEIsMjgsMjheRkhcXF5GTjk5Ml5GU15GVDY2Myw4NzZeQTBCLDIzLDI0XkZIXFxeRk45NTheRlNeRlQ2MjgsODc3XkEwQiwyMywyNF5GSFxcXkZOOTg3XkZTXkZUNTkxLDg3N15BMEIsMjMsMjReRkhcXF5GTjk4NV5GU15GVDU1Myw4NzVeQTBCLDIzLDI0XkZIXFxeRk45NzleRlNeRlQ0OSwzODNeQTBCLDIzLDI0XkZIXFxeRk45NzJeRlNeRlQ0OCw1MTBeQTBCLDIzLDI0XkZIXFxeRk45NjleRlNeRlQ1MSw5MjReQTBCLDIzLDI0XkZIXFxeRk45NjBeRlNeRlQyNiw5MjNeQTBCLDIzLDI0XkZIXFxeRk45NzReRlNeRlQ2OTAsMzA4XkEwQiw1NCw1Ml5GSFxcXkZONjAyXkZTXkZUNzc0LDI1N15BMEIsMjMsMjReRkhcXF5GTjk4Nl5GU15GVDQ1MSwzODheQTBCLDU2LDU1XkZSXkZIXFxeRk45OTReRlNeRlQ0MTAsMTAyOV5BMEIsMjcsMjZeRkhcXF5GTjk2Ml5GU15GVDUwOSwxMDI5XkEwQiwyNywyNl5GSFxcXkZOOTYxXkZTXkZUNjg0LDM4M15BQUIsMjcsMTVeRkhcXF5GREJveDpeRlNeRlQ0NzgsMTAyOV5BMEIsMjcsMjZeRkhcXF5GTjk2M15GU15GVDY2MCwxMDI1XkFBQiwxOCwxMF5GSFxcXkZERGVsaXZlcnk6XkZTXkZUNzE0LDU3Nl5BQUIsMjcsMTVeRkhcXF5GRFF1YW50aXR5Ol5GU15GVDc3OSwxMDI2XkFBQiwxOCwxMF5GSFxcXkZOOTk1XkZTXkZUNjI1LDEwMjVeQUFCLDE4LDEwXkZIXFxeRkRSZWZlcmVuY2U6XkZTXkZUNTUzLDEwMjNeQUFCLDE4LDEwXkZIXFxeRkRBZmZlY3RhdGlvbjpeRlNeRlQ1OTMsMTAyNF5BQUIsMTgsMTBeRkhcXF5GRFlvdXIgUmVmOl5GU15GVDcxMCwxMDI1XkFBQiwyNywxNV5GSFxcXkZEUGFydCBOdW1iZXI6XkZTXkZUNzcyLDM4M15BQUIsMTgsMTBeRkhcXF5GRFBpY2sgQ2FyZDpeRlNeRlQ0NDUsMTAyN15BMEIsMjcsMjZeRkhcXF5GTjk2NF5GU15GVDI0LDEwMjdeQUFCLDE4LDEwXkZIXFxeRkRTaGlwcGVyOl5GU15GVDM3OCwxMDI1XkEwQiwyNywyNl5GSFxcXkZOOTY1XkZTXkJZNCwzLDI0M15GVDMwMywxMTAwXkJDQiwsWSxOXkZOOTk3XkZTXkJZMywzLDY5XkZUNjMxLDU1XkJDSSwsWSxOXkZOOTk2XkZTXlBRMSwwLDEsWV5YWl5YQV5YRllTSElQUC0xLlpQTF5GTjk5OV5GRFMwMV5GU15GTjk5OF5GRCAvIF5GU15GTjk5N15GRD47MDA0MzM4OTExMDMwMDY0MjYzODNeRlNeRk45OTZeRkQ+OzQzMzg5MTEwMzAwNjQyNjM4M15GU15GTjk5NV5GRE9kYWNlIGNvbm5lY3RlZCBzb2NrZXQgMTZBIFNTTy1QaW4gQUxVXkZTXkZOOTkyXkZEUzUzMDU1OSAvIFM1MzA1NTleRlNeRk45OTReRkQgICAgMC40NiBrZ15GU15GTjk5M15GRF5GU15GTjk5MV5GRF5GU15GTjk5MF5GRDJeRlNeRk45ODleRkReRlNeRk45ODheRkReRlNeRk45ODdeRkQwMjM4OTA2Njg0XkZTXkZOOTg2XkZEODEyMzg3XkZTXkZOOTg1XkZEU2FsZXMgb2ZmX0dyb3BfVGVzdF8wMV5GU15GTjk1MF5GRF5GU15GTjk4M15GRDYtRlItRFBEICAgICAgIF5GU15GTjk4Ml5GRF5GU15GTjk4MF5GREZyYW5jZV5GU15GTjk3OV5GRF5GU15GTjk3OF5GRDEyLzA2LzIwMjZeRlNeRk45NzdeRkQwODozMDowMF5GU15GTjk3Nl5GRF5GU15GTjk3NV5GRF5GU15GTjk3NF5GRFNjaG5laWRlciBFbGVjdHJpYyBTQVNeRlNeRk45NzNeRkReRlNeRk45NzJeRkRHVUlDSEFJTlZJTExFLUZSQU5DRV5GU15GTjk3MF5GREZSMzNeRlNeRk45NjleRkQyNzkzMF5GU15GTjk2N15GRERQTE1eRlNeRk45ODReRkRDVjAyMzU3NTkyXkZTXkZOOTY4XkZEUk9VVEUzXkZTXkZOOTY2XkZEXkZTXkZOOTY1XkZEWUVTU1MgTE9HSVNUSVFVRSBDRVNUQVMgLSBDREVTIFVSR15GU15GTjk2NF5GRDI1IENIRU1JTiBERSBNQVJUSUNPVF5GU15GTjk2M15GRF5GU15GTjk2Ml5GRFNBTEVTIEZMT1cgNV5GU15GTjk2MV5GRDMzNjEwICAgIENFU1RBU15GU15GTjk2MF5GRFJVRSBSLkdBUlJPUyAtWkFDIExPTkcgQlVJU1NPTl5GU15GTjk3MV5GRF5GU15GTjk1OV5GRF5GU15GTjk4MV5GREVWIFBBQyA2TSAxMTIgQ15GU15GTjk1OF5GRDgzMzcxMjU1Nl5GU15GTjk1N15GRF5GU15GTjk1Nl5GRF5GU15GTjYwMV5GRDU1MDgwMTJeRlNeRk42MDJeRkQwNjQyNjM4XkZTXkZONjAzXkZEMTA0MTggU15GU15GTjYwNF5GRDFeRlNeRk42MDVeRkQ1MzBeRlNeRk42MDZeRkRMRF5GU15GVDc1MCwxMDI1XkEwQiwyOCwyOF5GSFxcXkZOOTkyXkZTXkZPNzA5LDExMDBeR0I2OCw1OCw2OF5GU15GVDc2MywxMTYwXkEwQiw1NCwxMDheRlJeRkhcXF5GRENeRlNeWFo=",
  "ControlLabelBarcode": ""
}
```

The Base64 value above is a sample label. The script must populate `Label`
from the selected input file. Placeholder values above describe runtime
behavior; `ExotecID` may be any text value.

## Required behavior

1. Load the YAML configuration safely, apply documented defaults, validate
   values, and resolve the ZPL input path.
2. Read the selected file as bytes so the encoded content matches the source
   file exactly. Drop the configured number of complete leading lines,
   including their line terminators, before encoding.
3. Base64-encode those bytes using the standard Base64 alphabet and place the
   resulting string in `Label`. Build the request URL and
   `Header.ModuleName` from the validated configuration values. Populate
   `Header.Date` with today's date in the
   Europe/Paris timezone and `RequestID` with an ISO 8601 timestamp in the
   Europe/Paris timezone.
   `Container.ExotecID` may contain any text; keep `BarcodeList` and
   `ControlLabelBarcode` empty.
4. Serialize the payload as JSON. If `dry_run` is true, print the URL and JSON
   body and exit successfully without making a request. Otherwise, send it as
   an HTTP POST request with a 5-second timeout. Do not retry.
5. Treat HTTP `200 OK` as success, including when the response has no body.
   Report failures with enough information to diagnose them (for example,
   connection timeout or HTTP status code) and exit with a non-zero status.

## Acceptance criteria

- The script accepts exactly one argument: a YAML configuration path. Missing
  or extra arguments fail with a usage message and non-zero exit status.
- With `dry_run: true`, the script prints the POST URL and serialized payload,
  exits successfully, and makes no network request.
- With `config.yaml` containing the example settings, the script reads
  `labels.zpl` from the same directory as `config.yaml` and targets
  `http://172.23.0.76/OLPNLabeler01/label/request`.
- Omitting `zpl_file` reads `labels.zpl` from the configuration file's
  directory; relative and absolute configured ZPL paths resolve as specified.
- `drop_header_lines` defaults to zero; a positive value removes exactly that
  many leading lines before Base64 encoding, preserving all remaining bytes.
  Negative/non-integer values and values that remove all file content fail
  before any request is sent.
- Each allowed configuration value produces the corresponding URL and module
  name; invalid values are rejected before making a request.
- Malformed YAML, non-mapping configuration, unreadable files, and invalid
  configuration values produce clear errors and a non-zero exit status.
- With `drop_header_lines: 0`, decoding `Label` reproduces the input file
  byte-for-byte. With a positive value, it reproduces the bytes after exactly
  that many leading lines and their line terminators have been removed.
- The request body is valid JSON and uses `Content-Type: application/json`.
- `Header.Date` is today's date in the Europe/Paris timezone, `RequestID`
  contains a timestamp, `ExotecID` accepts text, and both barcode fields remain
  empty.
- An HTTP `200 OK` response is success even when the response body is empty;
  other HTTP statuses, file-read failures, and connection/time-out errors fail
  without retry and do not produce a success exit status.

## Open questions

None currently.
