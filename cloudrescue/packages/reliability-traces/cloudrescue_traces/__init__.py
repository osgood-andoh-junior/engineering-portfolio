"""Portable validation of bounded workload traces."""

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

FIELDS = ("time_ms", "requests", "fault")
FAULTS = frozenset({"healthy", "latency", "error", "disconnect"})


@dataclass(frozen=True, slots=True)
class Frame:
    time_ms: int
    requests: int
    fault: str


def integer(value: object) -> int:
    if type(value) is int:
        return value
    if isinstance(value, str) and value.isascii() and value.isdecimal() and len(value) <= 8:
        return int(value)
    raise ValueError("Expected a bounded nonnegative integer")


def unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field")
        result[key] = value
    return result


def load(path: Path) -> list[Frame]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        source = stream.read(65537)
    if len(source) > 65536:
        raise ValueError("Trace exceeds 64 KiB")
    if path.suffix.lower() == ".csv":
        reader = csv.DictReader(source.splitlines(), strict=True)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError("CSV columns must be time_ms,requests,fault")
        rows = list(reader)
    elif path.suffix.lower() == ".json":
        rows = json.loads(source, object_pairs_hook=unique_fields)
    else:
        raise ValueError("Choose a local JSON or CSV trace")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 30:
        raise ValueError("Provide 1–30 frames")
    normalized = []
    origin = None
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != set(FIELDS):
            raise ValueError("Unexpected trace fields")
        timestamp = integer(row["time_ms"])
        count = integer(row["requests"])
        fault = row["fault"]
        origin = timestamp if origin is None else origin
        if timestamp - origin != index * 1000:
            raise ValueError("Frames must be ordered at one-second intervals")
        if not 1 <= count <= 8 or not isinstance(fault, str) or fault not in FAULTS:
            raise ValueError("Invalid request count or fault")
        normalized.append(Frame(timestamp - origin, count, fault))
    return normalized


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps([asdict(row) for row in load(args.trace)], indent=2))
    except (ValueError, OSError, csv.Error) as exc:
        parser.error(str(exc))
