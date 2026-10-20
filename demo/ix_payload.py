"""Document process JSON helpers. Engine publishes identity, readings, tests, images, session."""

from __future__ import annotations

from typing import Any


def _as_dict(v: Any) -> dict:
    return v if isinstance(v, dict) else {}


def _first(obj: dict, *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in obj and obj[key] is not None:
            return obj[key]
    return default


def _origin(value: Any) -> str:
    s = str(value or "").strip().lower()
    return {
        "ocr": "visual",
        "mrz": "zone",
        "barcode": "code",
        "rfid": "chip",
    }.get(s, s)


def _group(value: Any) -> str:
    s = str(value or "").strip().lower()
    return {
        "verify": "validity",
        "quality": "capture",
        "security": "authenticity",
        "liveness": "authenticity",
    }.get(s, s)


def _outcome(value: Any) -> str:
    s = str(value or "").strip().lower()
    return "hold" if s == "skip" else s


def _field_name(value: Any) -> str:
    s = str(value or "")
    return {
        "surname": "familyName",
        "givenNames": "firstNames",
        "documentNumber": "docNumber",
        "hologramIntegrity": "foilCheck",
        "portrait": "face",
    }.get(s, s)


def process_meta(payload: dict | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"code": -1, "jobId": "", "detail": "invalid response", "at": ""}
    session = payload.get("session") if isinstance(payload.get("session"), dict) else {}
    meta = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    status = _first(session, "code", default=_first(meta, "status", default=payload.get("code", payload.get("errorCode"))))
    try:
        status = int(status)
    except (TypeError, ValueError):
        status = -1
    detail = _first(session, "detail", default=_first(meta, "message"))
    if not isinstance(detail, str):
        detail = payload.get("message") if isinstance(payload.get("message"), str) else ""
    if detail == "ok":
        detail = "ready"
    if detail == "processing failed":
        detail = "failed"
    return {
        "code": status,
        "status": status,
        "jobId": str(_first(session, "jobId", default=_first(meta, "transactionId", default="")) or ""),
        "transactionId": str(_first(session, "jobId", default=_first(meta, "transactionId", default="")) or ""),
        "detail": str(detail or ""),
        "message": str(detail or ""),
        "at": str(_first(session, "at", default=_first(meta, "timestamp", default="")) or ""),
        "timestamp": str(_first(session, "at", default=_first(meta, "timestamp", default="")) or ""),
    }


def is_document_json(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    if payload.get("api") in ("doc/1", "face/1"):
        return False
    if "documentName" in payload:
        return False
    if isinstance(payload.get("session"), dict) and "code" in payload["session"]:
        return True
    meta = payload.get("metadata")
    if isinstance(meta, dict) and "status" in meta:
        return True
    return "code" in payload and (
        "readings" in payload or "fields" in payload or "identity" in payload or "document" in payload
    )


def doc_result(payload: dict | None) -> dict:
    if not isinstance(payload, dict):
        return {
            "session": process_meta(None),
            "identity": {},
            "readings": [],
            "tests": [],
            "images": [],
        }
    return payload


def fields(payload: dict | None) -> list[dict]:
    body = doc_result(payload)
    raw = body.get("readings")
    if not isinstance(raw, list):
        raw = body.get("fields")
    rows = [row for row in raw if isinstance(row, dict)] if isinstance(raw, list) else []
    out: list[dict] = []
    for row in rows:
        item = dict(row)
        item["name"] = _field_name(_first(row, "name", "id", default=""))
        item["id"] = item["name"]
        item["origin"] = _origin(_first(row, "origin", "source", default=""))
        item["source"] = item["origin"]
        out.append(item)
    return out


def checks(payload: dict | None, kind: str | None = None) -> list[dict]:
    body = doc_result(payload)
    raw = body.get("tests")
    if not isinstance(raw, list):
        raw = body.get("checks")
    rows = [row for row in raw if isinstance(row, dict)] if isinstance(raw, list) else []
    out: list[dict] = []
    for row in rows:
        item = dict(row)
        item["name"] = _field_name(_first(row, "name", "id", default=""))
        item["id"] = item["name"]
        item["group"] = _group(_first(row, "group", "kind", default=""))
        item["kind"] = item["group"]
        item["outcome"] = _outcome(_first(row, "outcome", "result", default=""))
        item["result"] = item["outcome"]
        item["note"] = _first(row, "note", "reason", default="")
        item["reason"] = item["note"]
        out.append(item)
    if kind is None:
        return out
    want = _group(kind)
    return [row for row in out if row.get("group") == want]


def images(payload: dict | None) -> list[dict]:
    raw = doc_result(payload).get("images")
    rows = [row for row in raw if isinstance(row, dict)] if isinstance(raw, list) else []
    out: list[dict] = []
    for row in rows:
        item = dict(row)
        item["name"] = _field_name(_first(row, "name", "id", default=""))
        item["id"] = item["name"]
        if "data" not in item and "image" in item:
            item["data"] = item["image"]
        if "image" not in item and "data" in item:
            item["image"] = item["data"]
        out.append(item)
    return out


def document(payload: dict | None) -> dict:
    body = doc_result(payload)
    ident = _as_dict(body.get("identity"))
    if not ident:
        ident = _as_dict(body.get("document"))
    out = dict(ident)
    if "class" not in out and "type" in out:
        out["class"] = out["type"]
    if "type" not in out and "class" in out:
        out["type"] = out["class"]
    return out
