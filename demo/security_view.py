"""Liveness tab: security checks from the customer process JSON."""
from __future__ import annotations

from typing import Any

from ix_payload import checks, document


def _page_side(page_index: Any) -> str:
    try:
        n = int(page_index)
    except (TypeError, ValueError):
        n = 0
    if n == 0:
        return "Front"
    if n == 1:
        return "Back"
    return f"Page {n}"


def _score_cell(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return ""
    return f"{float(value):.6f}"


def security_view_from_payload(payload: dict) -> tuple[str, list[list[str]]]:
    rows_in = checks(payload, "authenticity")
    if not rows_in:
        return (
            "*No liveness checks in this response. If you expected checks, this license may not include liveness.*",
            [],
        )
    ident = document(payload)
    title = ident.get("type") or "Document"
    fail = sum(1 for row in rows_in if row.get("result") == "fail")
    ok = sum(1 for row in rows_in if row.get("result") == "pass")
    skip = sum(1 for row in rows_in if row.get("result") in ("hold", "skip"))
    summary = (
        f"### {title}\n\n"
        f"{ok} pass · {fail} fail · {skip} skip"
    )
    rows: list[list[str]] = []
    for row in rows_in:
        page = _page_side(row.get("page", 0))
        label = str(row.get("result") or "skip")
        extra = _score_cell(row.get("score"))
        if extra:
            label = f"{label} · {extra}"
        reason = str(row.get("reason") or "").strip()
        if reason:
            label = f"{label} — {reason}"
        rows.append([page, str(row.get("id") or ""), label])
    return summary, rows
