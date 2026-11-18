import csv
import io
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, text

from backend import audit_chain
from backend.api_support import DB
from backend.benchmark import benchmark, csv_rows
from backend.identity import (
    Admin,
    OperatorActor,
    Viewer,
    check_password,
    digest_token,
    issue,
    password_hash,
)
from backend.security_models import (
    AuditRecord,
    AuditVerification,
    BenchmarkRun,
    Operator,
    OperatorSession,
)
from backend.telemetry import snapshot

router = APIRouter()


@router.get("/telemetry")
def telemetry(actor: Viewer):
    return {"scope": "api_process", "events": snapshot()}


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]{2,47}$")]
    password: Annotated[str, Field(min_length=1, max_length=128)]


class Account(Login):
    password: Annotated[str, Field(min_length=12, max_length=128)]
    role: Literal["viewer", "operator", "administrator"]


class AccountChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["viewer", "operator", "administrator"]
    active: bool


@router.post("/identity/login")
def login(payload: Login, db: DB):
    account = db.get(Operator, payload.username)
    valid = check_password(payload.password, account.password if account else None)
    if not valid or not account or not account.active:
        audit_chain.append(db, payload.username, "login_denied")
        db.commit()
        raise HTTPException(401, "Invalid credentials")
    token = issue(db, account)
    audit_chain.append(db, account.username, "login")
    db.commit()
    return {"token": token, "expires_in": 1800}


@router.get("/identity/me")
def me(actor: Viewer):
    return {"username": actor.username, "role": actor.role}


class Logout(BaseModel):
    token: Annotated[str, Field(min_length=1, max_length=512)]


@router.post("/identity/logout")
def logout(payload: Logout, db: DB, actor: Viewer):
    session = db.get(OperatorSession, digest_token(payload.token))
    if session and session.username == actor.username:
        db.delete(session)
        audit_chain.append(db, actor.username, "logout")
        db.commit()
    return {"signed_out": True}


@router.get("/identity/accounts")
def accounts(db: DB, actor: Admin):
    return [
        {"username": row.username, "role": row.role, "active": row.active}
        for row in db.scalars(select(Operator).order_by(Operator.username))
    ]


@router.post("/identity/accounts", status_code=201)
def add_account(payload: Account, db: DB, actor: Admin):
    db.execute(text("SELECT pg_advisory_xact_lock(726031026)"))
    if db.scalar(select(Operator.username).limit(1)) is None:
        raise HTTPException(
            409, "Provision the first administrator with the local identity command"
        )
    if db.get(Operator, payload.username):
        raise HTTPException(409, "Username is already in use")
    db.add(
        Operator(
            username=payload.username,
            password=password_hash(payload.password),
            role=payload.role,
            active=True,
        )
    )
    audit_chain.append(
        db,
        actor.username,
        "account_created",
        target=payload.username,
        after={"role": payload.role, "active": True},
    )
    db.commit()
    return {"username": payload.username, "role": payload.role, "active": True}


@router.put("/identity/accounts/{username}")
def edit_account(username: str, payload: AccountChange, db: DB, actor: Admin):
    db.execute(text("SELECT pg_advisory_xact_lock(726031026)"))
    account = db.get(Operator, username)
    if account is None:
        raise HTTPException(404, "Account not found")
    if (
        account.active
        and account.role == "administrator"
        and (not payload.active or payload.role != "administrator")
    ):
        count = db.scalar(
            select(func.count())
            .select_from(Operator)
            .where(Operator.active.is_(True), Operator.role == "administrator")
        )
        if count == 1:
            raise HTTPException(409, "Keep at least one active administrator")
    before = {"role": account.role, "active": account.active}
    account.role, account.active = payload.role, payload.active
    audit_chain.append(
        db,
        actor.username,
        "account_updated",
        target=username,
        before=before,
        after=payload.model_dump(),
    )
    db.commit()
    return {"username": username, **payload.model_dump()}


@router.get("/identity/events")
def authorization_events(db: DB, actor: Admin):
    query = (
        select(AuditRecord)
        .where(
            AuditRecord.payload["action"].astext.in_(
                [
                    "login",
                    "login_denied",
                    "logout",
                    "authorization_denied",
                    "account_created",
                    "account_updated",
                ]
            )
        )
        .order_by(AuditRecord.id.desc())
        .limit(50)
    )
    return [{"id": row.id, **row.payload} for row in db.scalars(query)]


class BenchmarkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    seed: Annotated[int, Field(ge=0, le=2147483647)] = 42


def run_view(row: BenchmarkRun):
    return {
        "id": row.id,
        "created_at": row.created_at,
        **{key: value for key, value in row.payload.items() if key not in {"raw", "workloads"}},
    }


@router.post("/benchmarks", status_code=201)
def run_benchmark(payload: BenchmarkRequest, db: DB, actor: OperatorActor):
    if not db.scalar(text("SELECT pg_try_advisory_xact_lock(726031027)")):
        raise HTTPException(409, "A benchmark is already running")
    row = BenchmarkRun(actor=actor.username, payload=benchmark(payload.seed))
    db.add(row)
    db.commit()
    return run_view(row)


@router.get("/benchmarks")
def runs(db: DB, actor: Viewer):
    return [
        {"id": index, "seed": seed, "created_at": created}
        for index, seed, created in db.execute(
            select(
                BenchmarkRun.id,
                BenchmarkRun.payload["master_seed"].as_integer(),
                BenchmarkRun.created_at,
            )
            .order_by(BenchmarkRun.id.desc())
            .limit(30)
        )
    ]


@router.get("/benchmarks/{index}")
def run_detail(index: int, db: DB, actor: Viewer):
    row = db.get(BenchmarkRun, index)
    if not row:
        raise HTTPException(404, "Benchmark not found")
    return run_view(row)


@router.get("/benchmarks/{index}/export/{format}")
def run_export(index: int, format: Literal["json", "csv"], db: DB, actor: Viewer):
    row = db.get(BenchmarkRun, index)
    if not row:
        raise HTTPException(404, "Benchmark not found")
    if format == "json":
        import json

        body, media = json.dumps(row.payload), "application/json"
    else:
        rows = csv_rows(row.payload)
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=sorted({key for row in rows for key in row}))
        writer.writeheader()
        writer.writerows(rows)
        body, media = output.getvalue(), "text/csv"
    return Response(
        body,
        media_type=media,
        headers={"Content-Disposition": f"attachment; filename=cloudrescue-{index}.{format}"},
    )


@router.get("/audit-chain/export")
def audit_export(db: DB, actor: Admin):
    return audit_chain.export(db)


class Checkpoint(BaseModel):
    count: Annotated[int, Field(ge=0)]
    digest: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


@router.post("/audit-chain/verify")
def audit_verify(db: DB, actor: Admin, checkpoint: Checkpoint | None = None):
    result = audit_chain.verify(
        audit_chain.export(db), (checkpoint.count, checkpoint.digest) if checkpoint else None
    )
    db.add(AuditVerification(actor=actor.username, result=result, created_at=datetime.now(UTC)))
    db.commit()
    return result
