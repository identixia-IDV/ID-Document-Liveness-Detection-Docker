#!/usr/bin/env python3
"""
Shared Gradio demo helpers for Identixia *-Linux products (local only).


Canonical copy: templates/linux-api/demo_ui.py
Kept inside the ``demo/`` package (run with ``python demo``).


UI conventions (every product demo):
  - Result tab: short markdown summary + Field/Value table
  - Raw JSON tab: full API response
  - Examples: every image under assets/examples/samples/ (or examples/)
"""


from __future__ import annotations


import json
from pathlib import Path
from typing import Any


import gradio as gr


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


# Identixia DocumentReader workspace (no Result / Liveness / Images / Raw tabs).
RESULT_CSS = """
:root {
  --ix-page: #E6E9EF;
  --ix-surface: #F7F8FA;
  --ix-text: #141A22;
  --ix-muted: #5A6573;
  --ix-stroke: #C5CCD8;
  --ix-accent: #0F766E;
}
.gradio-container, .gradio-container .main, .app {
  background: var(--ix-page) !important;
  color: var(--ix-text) !important;
  font-size: 13px !important;
}
.ix-capture {
  display: flex !important;
  flex-direction: row !important;
  align-items: stretch !important;
  gap: 0.75rem !important;
}
.ix-capture > div {
  flex: 1 1 0 !important;
  min-width: 0 !important;
}
.ix-pages {
  display: flex !important;
  flex-direction: column !important;
  gap: 0.65rem !important;
}
.ix-pages .image-container, .ix-pages .image-frame {
  min-height: 0 !important;
}
.ix-pages img, .ix-pages .image-container {
  max-height: 300px !important;
}
.ix-side {
  display: flex !important;
  flex-direction: column !important;
  justify-content: space-between !important;
  gap: 0.65rem !important;
  background: var(--ix-surface) !important;
  border: 1px solid var(--ix-stroke) !important;
  padding: 0.65rem !important;
}
.ix-side button,
.ix-side button.primary {
  width: 100% !important;
  margin-top: auto !important;
}
.ix-ident {
  background: #F7F8FA !important;
  border: 1px solid #C5CCD8 !important;
  padding: 0.65rem 0.85rem !important;
  color: var(--ix-text) !important;
  font-size: 13px !important;
  font-weight: 400 !important;
}
.ix-ident h3, .ix-ident h2 {
  margin: 0 0 0.35rem !important;
  font-size: 20px !important;
  font-weight: 600 !important;
  color: var(--ix-text) !important;
}
.ix-ident p { margin: 0.15rem 0 !important; color: var(--ix-text) !important; overflow-wrap: anywhere !important; word-break: break-word !important; }
#ix-examples,
.ix-examples {
  overflow: auto !important;
  flex: 1 1 auto !important;
}
#ix-examples table,
.ix-examples table {
  width: 100% !important;
}
#ix-examples img,
.ix-examples img {
  max-height: 110px !important;
  width: auto !important;
}
.ix-work { align-items: stretch; }
button.primary, .ix-side button {
  background: var(--ix-accent) !important;
  border-color: var(--ix-accent) !important;
}
.ix-result-table,
.ix-result-table .table-wrap,
.ix-result-table .wrap,
.ix-result-table .overflow-y-auto,
.ix-result-table .overflow-auto {
  max-height: none !important;
  height: auto !important;
  overflow: visible !important;
}
.ix-result-table table {
  table-layout: fixed !important;
  width: 100% !important;
}
.ix-result-table th,
.ix-result-table td {
  white-space: normal !important;
  overflow-wrap: anywhere !important;
  word-break: break-word !important;
  vertical-align: top !important;
}
.ix-result-table th:nth-child(1),
.ix-result-table td:nth-child(1) {
  width: 24% !important;
}
.ix-result-table th:nth-child(2),
.ix-result-table td:nth-child(2) {
  width: 56% !important;
}
.ix-result-table th:nth-child(3),
.ix-result-table td:nth-child(3) {
  width: 20% !important;
  min-width: 5.5rem !important;
  position: sticky;
  right: 0;
  background: var(--table-even-background-fill, var(--body-background-fill, #fff));
}
.ix-result-gallery,
.ix-result-gallery .grid-wrap,
.ix-result-gallery .gallery-container,
.ix-result-gallery .overflow-y-auto,
.ix-result-gallery .overflow-auto {
  max-height: none !important;
  height: auto !important;
  overflow: visible !important;
}
.ix-img-grid {
  display: grid !important;
  grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  gap: 0.55rem !important;
}
.ix-img-cell {
  margin: 0 !important;
  background: var(--ix-surface) !important;
  border: 1px solid var(--ix-stroke) !important;
  padding: 0.35rem !important;
}
.ix-img-cell img {
  display: block !important;
  width: 100% !important;
  height: auto !important;
  max-height: 220px !important;
  object-fit: contain !important;
  background: #fff !important;
}
.ix-img-cell figcaption {
  margin-top: 0.3rem !important;
  font-size: 11px !important;
  color: var(--ix-muted) !important;
  text-align: center !important;
}
.ix-grouped .ix-section {
  margin: 0 0 0.5rem !important;
  font-size: 15px !important;
  font-weight: 650 !important;
  color: var(--ix-text) !important;
}
.ix-grouped .ix-empty {
  color: var(--ix-muted) !important;
  font-style: italic !important;
  margin: 0 0 0.65rem !important;
}
.ix-grouped .ix-group {
  background: var(--ix-surface) !important;
  border: 1px solid var(--ix-stroke) !important;
  padding: 0.55rem 0.65rem 0.5rem !important;
  margin: 0 0 0.65rem !important;
}
.ix-grouped .ix-group-head {
  display: flex !important;
  align-items: center !important;
  gap: 0.45rem !important;
  margin: 0 0 0.45rem !important;
}
.ix-grouped .ix-pill {
  display: inline-block !important;
  background: rgba(15, 118, 110, 0.14) !important;
  color: var(--ix-accent) !important;
  font-size: 11px !important;
  font-weight: 700 !important;
  letter-spacing: 0.06em !important;
  padding: 0.16rem 0.5rem !important;
  border-radius: 999px !important;
  border: 1px solid rgba(15, 118, 110, 0.35) !important;
}
.ix-grouped .ix-count {
  color: var(--ix-muted) !important;
  font-size: 12px !important;
  font-weight: 600 !important;
}
.ix-grouped .ix-grid {
  display: grid !important;
  grid-template-columns: 1fr 1fr !important;
  gap: 0.3rem 0.7rem !important;
}
.ix-grouped .ix-cell { min-width: 0 !important; padding: 0.15rem 0 !important; }
.ix-grouped .ix-label {
  color: var(--ix-muted) !important;
  font-size: 12px !important;
  overflow-wrap: anywhere !important;
  word-break: break-word !important;
  white-space: pre-wrap !important;
  min-width: 0 !important;
}
.ix-grouped .ix-value {
  color: var(--ix-text) !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  user-select: text !important;
  overflow-wrap: anywhere !important;
  word-break: break-word !important;
  white-space: pre-wrap !important;
  min-width: 0 !important;
}
.ix-grouped .ix-check-row {
  padding: 0.28rem 0 !important;
  border-bottom: 1px solid var(--ix-stroke) !important;
}
.ix-grouped .ix-check-row:last-child { border-bottom: 0 !important; }
.ix-grouped .ix-check {
  display: flex !important;
  justify-content: space-between !important;
  gap: 0.75rem !important;
  align-items: baseline !important;
}
.ix-grouped .ix-check span {
  overflow-wrap: anywhere !important;
  word-break: break-word !important;
  min-width: 0 !important;
}
.ix-grouped .ix-extra {
  color: var(--ix-muted) !important;
  font-size: 12px !important;
  overflow-wrap: anywhere !important;
  word-break: break-word !important;
  white-space: pre-wrap !important;
}
.ix-grouped .ix-pass { color: var(--ix-accent) !important; }
.ix-grouped .ix-fail { color: #B91C1C !important; }
.ix-grouped .ix-skip { color: var(--ix-muted) !important; }
@media (max-width: 640px) {
  .ix-grouped .ix-grid { grid-template-columns: 1fr !important; }
}
"""




def result_dataframe(*, headers: list[str] | None = None, label: str = "Extracted fields"):
    """Field table that expands with rows (no inner scrollbar)."""
    cols = headers or ["Field", "Value", "Source"]
    kw = dict(
        headers=cols,
        datatype=["str"] * len(cols),
        interactive=False,
        wrap=True,
        label=label,
        elem_classes=["ix-result-table"],
    )
    if len(cols) == 3:
        kw["column_widths"] = ["24%", "56%", "20%"]
    try:
        return gr.Dataframe(**kw, max_height=None)
    except TypeError:
        kw.pop("column_widths", None)
        try:
            return gr.Dataframe(**kw, max_height=None)
        except TypeError:
            return gr.Dataframe(**kw)




def result_gallery(*, label: str = "Images", columns: int = 2):
    """HTML image grid (avoids Gradio Gallery thread postprocess on multipage)."""
    del columns  # layout is CSS-driven (2 columns)
    return gr.HTML(label=label, elem_classes=["ix-result-gallery", "ix-grouped"])



def samples_dir(root: Path) -> Path:
    for rel in ("assets/examples/samples", "assets/samples", "examples/samples", "examples"):
        p = root / rel
        if p.is_dir():
            return p
    return root / "assets" / "examples" / "samples"




def list_images(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(
        p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
    )




def list_image_paths(directory: Path) -> list[str]:
    return [str(p) for p in list_images(directory)]




def list_pair_examples(directory: Path) -> list[list[str]]:
    """Match-style pairs: ``pair(N)_1.*`` + ``pair(N)_2.*`` when both exist."""
    files = {p.name: p for p in list_images(directory)}
    pairs: list[list[str]] = []
    seen: set[str] = set()
    for name, path in sorted(files.items()):
        stem = path.stem  # pair(1)_1
        if "_1" not in stem or stem in seen:
            continue
        other_stem = stem.rsplit("_1", 1)[0] + "_2"
        for suf in IMAGE_SUFFIXES:
            other = files.get(other_stem + suf)
            if other:
                pairs.append([str(path), str(other)])
                seen.add(stem)
                seen.add(other_stem)
                break
    return pairs




def cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)




def flatten_rows(
    obj: Any,
    *,
    prefix: str = "",
    source: str = "",
    skip_keys: set[str] | None = None,
    max_rows: int = 200,
) -> list[list[str]]:
    """Flatten nested JSON into [Field, Value, Source] rows."""
    skip = skip_keys or set()
    rows: list[list[str]] = []


    def walk(node: Any, path: str) -> None:
        if len(rows) >= max_rows:
            return
        if isinstance(node, dict):
            for key, value in node.items():
                if key in skip:
                    continue
                child = f"{path}.{key}" if path else str(key)
                if isinstance(value, (dict, list)):
                    # Prefer compact attribute {value, confidence/status}
                    if (
                        isinstance(value, dict)
                        and "value" in value
                        and not any(isinstance(value[k], (dict, list)) for k in value)
                    ):
                        val = value.get("value")
                        extra = []
                        if "confidence" in value:
                            extra.append(f"conf={cell(value['confidence'])}")
                        if "status" in value:
                            extra.append(f"status={cell(value['status'])}")
                        if "range" in value:
                            extra.append(f"range={cell(value['range'])}")
                        shown = cell(val)
                        if extra:
                            shown = f"{shown} ({', '.join(extra)})"
                        rows.append([child, shown, source])
                    else:
                        walk(value, child)
                else:
                    rows.append([child, cell(value), source])
        elif isinstance(node, list):
            if not node:
                rows.append([path or "[]", "[]", source])
                return
            # Short list of scalars
            if all(not isinstance(x, (dict, list)) for x in node):
                rows.append([path, cell(node), source])
                return
            for i, item in enumerate(node):
                walk(item, f"{path}[{i}]")
        else:
            rows.append([path or "value", cell(node), source])


    walk(obj, prefix)
    return rows




def result_outputs(
    payload: Any,
    *,
    summary: str,
    source: str = "api",
    skip_keys: set[str] | None = None,
) -> tuple[str, list[list[str]], str]:
    rows = flatten_rows(payload, source=source, skip_keys=skip_keys)
    raw = json.dumps(payload, indent=2, ensure_ascii=False) if payload is not None else ""
    return summary, rows, raw




def error_outputs(message: str) -> tuple[str, list[list[str]], str]:
    return f"**Error:** {message}", [], ""




def result_panel(*, placeholder: str = "*Run an action to see fields.*"):
    """Create Result + Raw JSON tabs. Returns (summary, table, raw) components."""
    with gr.Tabs():
        with gr.Tab("Result"):
            summary = gr.Markdown(value=placeholder)
            table = result_dataframe()
        with gr.Tab("Raw JSON"):
            raw = gr.Code(language="json", label="API response")
    return summary, table, raw
