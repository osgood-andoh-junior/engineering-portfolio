import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.security_models import AuditRecord

GENESIS = "0" * 64


def digest(record_id: int, previous: str, payload: dict) -> str:
    data = json.dumps(
        [record_id, previous, payload],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256(data.encode()).hexdigest()


def append(db: Session, actor: str, action: str, **details: Any) -> None:
    db.execute(text("SELECT pg_advisory_xact_lock(726031025)"))
    last = db.scalar(select(AuditRecord).order_by(AuditRecord.id.desc()).limit(1))
    index, previous = (last.id + 1, last.digest) if last else (1, GENESIS)
    payload = {"actor": actor, "action": action, "time": datetime.now(UTC).isoformat(), **details}
    db.add(
        AuditRecord(
            id=index, previous=previous, digest=digest(index, previous, payload), payload=payload
        )
    )
    db.flush()


def export(db: Session) -> list[dict]:
    return [
        {"id": row.id, "previous": row.previous, "digest": row.digest, "payload": row.payload}
        for row in db.scalars(select(AuditRecord).order_by(AuditRecord.id))
    ]


def verify(records: list[dict], checkpoint: tuple[int, str] | None = None) -> dict:
    previous = GENESIS
    anchored = checkpoint is None or checkpoint == (0, GENESIS)
    for index, record in enumerate(records, 1):
        try:
            valid = (
                record["id"] == index
                and record["previous"] == previous
                and record["digest"] == digest(index, previous, record["payload"])
            )
        except (KeyError, TypeError, ValueError):
            valid = False
        if not valid:
            return {"valid": False, "failure_at": index, "reason": "Record or link differs"}
        previous = record["digest"]
        anchored = anchored or checkpoint == (index, previous)
    return {
        "valid": anchored,
        "count": len(records),
        "digest": previous,
        "anchored": checkpoint is not None and anchored,
        "reason": None if anchored else "Independent checkpoint does not match",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("export", type=Path)
    parser.add_argument("--checkpoint", type=Path)
    args = parser.parse_args()
    checkpoint = json.loads(args.checkpoint.read_text()) if args.checkpoint else None
    result = verify(
        json.loads(args.export.read_text()),
        (checkpoint["count"], checkpoint["digest"]) if checkpoint else None,
    )
    print(json.dumps(result))
    raise SystemExit(0 if result["valid"] else 1)
