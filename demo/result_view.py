"""Result tab: document identity and fields from the customer process JSON."""
from __future__ import annotations

import html
from typing import Any

from ix_payload import checks, doc_result, document, fields, process_meta


def _cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _score_cell(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return ""
    return f"{float(value):.6f}"


def _result_label(result: Any) -> str:
    s = str(result or "").strip().lower()
    if s == "pass":
        return "pass"
    if s == "fail":
        return "fail"
    if s == "skip" or s == "hold":
        return "hold"
    return s or "—"



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


_OVERALL_KINDS = ("validity", "capture", "authenticity")
_FIELD_SOURCE_ORDER = ("visual", "zone", "code")
_CHECK_RESULT_RANK = {"fail": 0, "pass": 1, "hold": 2, "skip": 2}

_SOURCE_LABELS = {"visual": "VISUAL", "zone": "ZONE", "code": "CODE", "chip": "CHIP"}
_KIND_LABELS = {
    "validity": "Validity",
    "capture": "Capture",
    "authenticity": "Liveness",
    "liveness": "Liveness",
}


def source_label(source: str) -> str:
    key = str(source or "").strip().lower()
    if key in _SOURCE_LABELS:
        return _SOURCE_LABELS[key]
    return key.upper() if key else "FIELD"


def kind_label(kind: str) -> str:
    key = str(kind or "").strip().lower()
    if key in _KIND_LABELS:
        return _KIND_LABELS[key]
    return key.capitalize() if key else "Check"


def _html_esc(value: str) -> str:
    return html.escape(value, quote=True)


def overall_results(payload: dict) -> list[dict[str, str]]:
    """Kind-level roll-up: any fail → fail, else any pass → pass, else skip."""
    check_list = checks(doc_result(payload))
    out: list[dict[str, str]] = []
    for kind in _OVERALL_KINDS:
        results = [
            str(row.get("result") or "").strip().lower()
            for row in check_list
            if str(row.get("kind") or "") == kind
        ]
        if "fail" in results:
            verdict = "fail"
        elif "pass" in results:
            verdict = "pass"
        else:
            verdict = "skip"
        out.append({"kind": kind, "result": verdict})
    return out


def field_groups(payload: dict) -> list[dict[str, Any]]:
    """Fields grouped by source. Source is the heading; value is the primary line."""
    buckets: dict[str, list[dict[str, str]]] = {}
    extra: list[str] = []
    for row in fields(doc_result(payload)):
        value = _cell(row.get("value"))
        if not value or value == "null":
            continue
        source = str(row.get("source") or "field")
        if source not in buckets:
            buckets[source] = []
            if source not in _FIELD_SOURCE_ORDER:
                extra.append(source)
        buckets[source].append(
            {
                "id": str(row.get("id") or ""),
                "value": value,
                "score": _score_cell(row.get("score")),
            }
        )
    out: list[dict[str, Any]] = []
    for source in (*_FIELD_SOURCE_ORDER, *extra):
        items = buckets.get(source) or []
        if items:
            out.append({"source": source, "items": items})
    return out


def check_groups(payload: dict) -> list[dict[str, Any]]:
    """Checks grouped by kind, fail first. Kind is the heading."""
    buckets: dict[str, list[dict[str, str]]] = {k: [] for k in _OVERALL_KINDS}
    extra: list[str] = []
    rows = checks(doc_result(payload))
    multipage = len({row.get("page") for row in rows if row.get("page") is not None}) > 1
    for row in rows:
        kind = str(row.get("kind") or "check")
        extra_bits: list[str] = []
        reason = str(row.get("reason") or "").strip()
        if reason:
            extra_bits.append(reason)
        score = _score_cell(row.get("score"))
        if score:
            extra_bits.append(score)
        check_id = str(row.get("id") or "")
        # Page labels only when more than one page was processed.
        if multipage and row.get("page") is not None:
            check_id = f"{_page_side(row.get('page'))} · {check_id}"
        item = {
            "id": check_id,
            "result": _result_label(row.get("result")),
            "extra": " · ".join(extra_bits),
            "page": "" if row.get("page") is None else str(row.get("page")),
        }
        if kind not in buckets:
            buckets[kind] = []
            extra.append(kind)
        buckets[kind].append(item)

    def _rank(item: dict[str, str]) -> tuple[int, int]:
        try:
            page_n = int(item.get("page") or 0)
        except (TypeError, ValueError):
            page_n = 0
        return (page_n, _CHECK_RESULT_RANK.get(item["result"], 9))

    out: list[dict[str, Any]] = []
    for kind in (*_OVERALL_KINDS, *extra):
        items = buckets.get(kind) or []
        if items:
            out.append({"kind": kind, "items": sorted(items, key=_rank)})
    return out


def fields_html(payload: dict) -> str:
    groups = field_groups(payload)
    if not groups:
        return '<h2 class="ix-section">Fields</h2><p class="ix-empty">No fields in this response.</p>'
    parts: list[str] = []
    for group in groups:
        label = source_label(str(group["source"]))
        cells: list[str] = []
        for item in group["items"]:
            extra = f'<div class="ix-extra">{_html_esc(item["score"])}</div>' if item["score"] else ""
            cells.append(
                '<div class="ix-cell">'
                f'<div class="ix-label">{_html_esc(item["id"])}</div>'
                f'<div class="ix-value">{_html_esc(item["value"])}</div>'
                f"{extra}</div>"
            )
        parts.append(
            '<div class="ix-group">'
            '<div class="ix-group-head">'
            f'<span class="ix-pill">{_html_esc(label)}</span>'
            f'<span class="ix-count">{len(group["items"])}</span>'
            "</div>"
            f'<div class="ix-grid">{"".join(cells)}</div>'
            "</div>"
        )
    return '<h2 class="ix-section">Fields</h2>' + "".join(parts)


def checks_html(payload: dict) -> str:
    groups = check_groups(payload)
    if not groups:
        return '<h2 class="ix-section">Checks</h2><p class="ix-empty">No checks in this response.</p>'
    parts: list[str] = []
    for group in groups:
        label = kind_label(str(group["kind"]))
        rows: list[str] = []
        for item in group["items"]:
            result = item["result"]
            cls = "ix-pass" if result == "pass" else "ix-fail" if result == "fail" else "ix-skip"
            extra = f'<div class="ix-extra">{_html_esc(item["extra"])}</div>' if item["extra"] else ""
            rows.append(
                '<div class="ix-check-row">'
                '<div class="ix-check">'
                f"<span>{_html_esc(item['id'])}</span>"
                f'<span class="{cls}">{_html_esc(result)}</span>'
                f"</div>{extra}</div>"
            )
        parts.append(
            '<div class="ix-group">'
            '<div class="ix-group-head">'
            f'<span class="ix-pill">{_html_esc(label)}</span>'
            f'<span class="ix-count">{len(group["items"])}</span>'
            "</div>"
            f"{''.join(rows)}</div>"
        )
    return '<h2 class="ix-section">Checks</h2>' + "".join(parts)


def fields_markdown(payload: dict) -> str:
    groups = field_groups(payload)
    if not groups:
        return "*No fields in this response.*"
    parts: list[str] = []
    for group in groups:
        parts.append(f"### {source_label(str(group['source']))}")
        for item in group["items"]:
            block = f"**{item['id']}**\n\n{item['value']}"
            if item["score"]:
                block += f"\n\n{item['score']}"
            parts.append(block)
    return "\n\n".join(parts)


def checks_markdown(payload: dict) -> str:
    groups = check_groups(payload)
    if not groups:
        return "*No checks in this response.*"
    parts: list[str] = []
    for group in groups:
        parts.append(f"### {kind_label(str(group['kind']))}")
        for item in group["items"]:
            block = f"**{item['id']}** · {item['result']}"
            if item["extra"]:
                block += f"\n\n{item['extra']}"
            parts.append(block)
    return "\n\n".join(parts)


def identity_line(payload: dict) -> str:
    body = doc_result(payload)
    ident = document(body)
    doc_type = ident.get("type") or "—"
    country = ident.get("country") or "—"
    score = ident.get("score")
    score_s = f"{float(score):.2f}" if isinstance(score, (int, float)) else "—"
    meta = process_meta(body)
    code = meta["status"]
    message = str(meta.get("message") or "").strip() or "—"
    state = "ok" if code == 0 else "failed"
    field_n = len(fields(body))
    check_list = checks(body)
    pass_n = sum(1 for row in check_list if str(row.get("result") or "") == "pass")
    fail_n = sum(1 for row in check_list if str(row.get("result") or "") == "fail")
    skip_n = max(0, len(check_list) - pass_n - fail_n)
    from ix_payload import images as _images

    pages = {
        int(row["page"])
        for row in check_list
        if row.get("page") is not None
        and str(row.get("page")).strip() != ""
        and str(row.get("page")).lstrip("-").isdigit()
    }
    for row in _images(body):
        if row.get("page") is not None and str(row.get("page")).lstrip("-").isdigit():
            pages.add(int(row["page"]))
    pages_sorted = sorted(pages)
    page_bit = f"{len(pages_sorted)} pages · " if len(pages_sorted) > 1 else ""
    return (
        f"### {doc_type} · {country} · {score_s}\n\n"
        f"**{state}** · status={code if code is not None else '—'} · {message}\n\n"
        f"{page_bit}{field_n} fields · {len(check_list)} checks · {pass_n} pass · {fail_n} fail · {skip_n} skip"
    )


def field_table_rows(payload: dict) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in fields(doc_result(payload)):
        value = _cell(row.get("value"))
        extra = _score_cell(row.get("score"))
        if extra:
            value = f"{value} · {extra}"
        rows.append([str(row.get("id") or ""), value, str(row.get("source") or "field")])
    return rows


def check_table_rows(payload: dict) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in checks(doc_result(payload)):
        label = _result_label(row.get("result"))
        extra = _score_cell(row.get("score"))
        if extra:
            label = f"{label} · {extra}"
        reason = str(row.get("reason") or "").strip()
        if reason:
            label = f"{label} — {reason}"
        rows.append([str(row.get("id") or ""), str(row.get("kind") or "check"), label])
    return rows


def build_result_view(payload: dict) -> tuple[str, list[list[str]]]:
    body = doc_result(payload)
    meta = process_meta(body)
    code = meta["status"]
    message = meta.get("message") or ""
    ident = document(body)
    doc_type = ident.get("type") or "—"
    country = ident.get("country") or "—"
    score = ident.get("score")
    score_s = f"{float(score):.6f}" if isinstance(score, (int, float)) else "—"
    ok = code == 0
    summary = (
        f"**{'ok' if ok else 'failed'}** · status={code} · {message}\n\n"
        f"**{doc_type}** · {country}\n\n"
        f"score: {score_s}"
    )
    rows: list[list[str]] = [
        ["class", _cell(ident.get("class") or ident.get("type")), "identity"],
        ["country", _cell(ident.get("country")), "identity"],
        ["score", score_s, "identity"],
        ["code", _cell(code), "session"],
        ["jobId", _cell(meta.get("jobId") or meta.get("transactionId")), "session"],
        ["detail", _cell(message), "session"],
    ]
    for row in checks(body, "validity"):
        label = _result_label(row.get("result"))
        reason = str(row.get("reason") or "").strip()
        if reason:
            label = f"{label} — {reason}"
        extra = _score_cell(row.get("score"))
        if extra:
            label = f"{label} · {extra}"
        rows.append([str(row.get("id") or ""), label, "validity"])
    for row in checks(body, "capture"):
        label = _result_label(row.get("result"))
        extra = _score_cell(row.get("score"))
        if extra:
            label = f"{label} · {extra}"
        rows.append([str(row.get("id") or ""), label, "capture"])
    for row in fields(body):
        value = _cell(row.get("value"))
        extra = _score_cell(row.get("score"))
        if extra:
            value = f"{value} · {extra}"
        source = str(row.get("source") or "field")
        rows.append([str(row.get("id") or ""), value, source])
    return summary, rows
