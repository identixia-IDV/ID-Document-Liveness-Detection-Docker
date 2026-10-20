"""Images panel: portrait / signature / cropped pages from the process JSON.

Renders HTML (not Gradio Gallery) so multipage results do not hit Gradio's
threaded gallery postprocess — that path fails on constrained hosts and drops
the whole Recognize response even when the API returned front + back.
"""
from __future__ import annotations

import base64
import html
from typing import Any

from ix_payload import images


def _page_label(page: Any) -> str:
    try:
        n = int(page)
    except (TypeError, ValueError):
        return ""
    if n == 0:
        return "Front"
    if n == 1:
        return "Back"
    return f"Page {n}"


def _data_uri(raw: str) -> str | None:
    s = (raw or "").strip()
    if not s:
        return None
    if s.startswith("data:") and "," in s[:128]:
        return s
    try:
        blob = base64.b64decode(s, validate=False)
    except Exception:
        return None
    if len(blob) < 32:
        return None
    mime = "image/jpeg"
    if blob[:8] == b"\x89PNG\r\n\x1a\n":
        mime = "image/png"
    elif blob[:4] == b"RIFF" and blob[8:12] == b"WEBP":
        mime = "image/webp"
    b64 = base64.b64encode(blob).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _image_uri(item: dict) -> str | None:
    for key in ("data", "image"):
        val = item.get(key)
        if isinstance(val, str) and val.strip():
            return _data_uri(val)
        if isinstance(val, dict):
            inner = val.get("image") or val.get("value") or val.get("data")
            if isinstance(inner, str) and inner.strip():
                return _data_uri(inner)
    return None


def gallery_from_payload(payload: dict) -> str:
    """HTML image grid captioned with name + Front/Back when multipage."""
    rows = images(payload)
    if not rows:
        return '<h2 class="ix-section">Images</h2><p class="ix-empty">No images in this response.</p>'

    pages = {
        int(row["page"])
        for row in rows
        if row.get("page") is not None and str(row.get("page")).lstrip("-").isdigit()
    }
    multipage = len(pages) > 1
    cells: list[str] = []
    for i, item in enumerate(rows):
        uri = _image_uri(item)
        if not uri:
            continue
        name = html.escape(str(item.get("id") or item.get("name") or f"image {i + 1}"))
        side = _page_label(item.get("page")) if multipage else ""
        caption = f"{name} · {side}" if side else name
        cells.append(
            '<figure class="ix-img-cell">'
            f'<img src="{uri}" alt="{caption}" loading="lazy"/>'
            f"<figcaption>{html.escape(caption)}</figcaption>"
            "</figure>"
        )
    if not cells:
        return '<h2 class="ix-section">Images</h2><p class="ix-empty">No images in this response.</p>'
    return (
        '<h2 class="ix-section">Images</h2>'
        f'<div class="ix-img-grid">{"".join(cells)}</div>'
    )
