"""Gradio UI — HTTP client for the DocumentReader Flask API.

Local only. Start the API first (``python run_server.py``), then ``python demo``.
One workspace: capture strip, fields / checks / images, Raw drawer.
"""

from __future__ import annotations

import sys
from pathlib import Path as _BootPath

_APP_ROOT = _BootPath(__file__).resolve().parent.parent
_PKG_DIR = _BootPath(__file__).resolve().parent
for _p in (_APP_ROOT, _APP_ROOT / "sdk", _PKG_DIR):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.append(_s)

def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(_APP_ROOT / ".env", override=False)


_load_env()

import base64
import json
import os
from pathlib import Path

import gradio as gr
import requests

import ui
from images_view import gallery_from_payload
from result_view import checks_html, fields_html, identity_line, kind_label, overall_results


APP_ROOT = Path(__file__).resolve().parent.parent
SAMPLES = APP_ROOT / "assets" / "examples" / "samples"
NO_BACK = SAMPLES / "_no_back.png"


def _env_port(primary: str, legacy: str, default: str) -> str:
    return os.environ.get(primary) or os.environ.get(legacy) or default


API = os.environ.get("API_BASE") or (
    f"http://127.0.0.1:{_env_port('PORT', 'DOCSDK_PORT', '14107')}"
)
API = API.rstrip("/")
DEMO_HOST = os.environ.get("DEMO_HOST") or os.environ.get("HOST") or "0.0.0.0"
DEMO_PORT = int(os.environ.get("DEMO_PORT", "14207"))
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def _fetch_license_status() -> dict:
    try:
        r = requests.get(f"{API}/api/licenseStatus", timeout=5)
        body = r.json() if r.ok else {}
        data = body.get("data") if isinstance(body, dict) else None
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _license_banner_md(status: dict | None = None) -> str:
    st = status if status is not None else _fetch_license_status()
    label = str(st.get("label") or "").strip()
    if not label:
        if st.get("licensed"):
            label = str(st.get("levelName") or "Licensed")
        else:
            label = "No license"
    rec = "on" if st.get("recognition") else "off"
    live = "on" if st.get("authenticity") else "off"
    return f"**License:** {label}  \nRecognition {rec} · Liveness {live}"


def _capability_notes(status: dict) -> list[str]:
    notes: list[str] = []
    if not status.get("authenticity"):
        notes.append("Liveness is **not available** on this license.")
    if not status.get("recognition"):
        notes.append("Recognition is **not available** on this license.")
    return notes



def _image_path(value) -> str | None:
    """Gradio Image(type=filepath) may return a path str, dict, Path, or FileData."""
    if value is None or value is False:
        return None
    if isinstance(value, Path):
        return str(value) if str(value).strip() else None
    if isinstance(value, dict):
        for key in ("path", "name", "orig_name"):
            p = value.get(key)
            if isinstance(p, str) and p.strip():
                return p
        return None
    path_attr = getattr(value, "path", None)
    if isinstance(path_attr, str) and path_attr.strip():
        return path_attr
    if isinstance(value, (list, tuple)) and value:
        return _image_path(value[0])
    if isinstance(value, str):
        s = value.strip()
        return s or None
    return None


def _b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def _list_images() -> list[Path]:
    if not SAMPLES.is_dir():
        return []
    return sorted(
        p for p in SAMPLES.iterdir() if p.is_file() and p.suffix.lower() in _IMAGE_SUFFIXES
    )


def _document_examples() -> list[list[str]]:
    files = {p.name: p for p in _list_images()}
    pairs: list[list[str]] = []
    used: set[str] = set()
    no_back = NO_BACK if NO_BACK.is_file() else None
    for path in sorted(files.values()):
        if path.name == NO_BACK.name:
            continue
        if "_front" not in path.stem:
            continue
        base = path.stem.rsplit("_front", 1)[0]
        back = None
        for suf in _IMAGE_SUFFIXES:
            cand = files.get(f"{base}_back{suf}")
            if cand:
                back = cand
                break
        # Placeholder keeps Gradio Examples 2-column aligned for front-only samples.
        pairs.append([str(path), str(back) if back else str(no_back or path)])
        used.add(path.name)
        if back:
            used.add(back.name)
    for path in _list_images():
        if path.name not in used and path.name != NO_BACK.name:
            pairs.append([str(path), str(no_back or path)])
    return pairs


def _empty() -> tuple[str, str, str, str, str]:
    return "Run Check liveness to see document type, score, and check counts.", "", "", "", ""


def _is_placeholder_back(path: str | None) -> bool:
    """True only for the Gradio Examples filler file — not for a missing Back."""
    if not path:
        return False
    try:
        name = Path(path).name
    except (TypeError, ValueError, OSError):
        return False
    return name == NO_BACK.name


def document_process(front, back):
    front = _image_path(front)
    back = _image_path(back)
    if not back or _is_placeholder_back(back):
        back = None
    lic = _fetch_license_status()
    notes = _capability_notes(lic)
    if not front:
        ident, fields, checks, gallery, raw = _empty()
        ident = "Front image required"
        if notes:
            ident = " · ".join(n.replace("**", "") for n in notes)
        return ident, fields, checks, gallery, raw

    if notes and not lic.get("recognition") and not lic.get("authenticity"):
        ident = " · ".join(n.replace("**", "") for n in notes)
        return ident, "", "", "", ""

    response = {
        "OCR": "normal",
        "MRZ": "normal",
        "Barcode": "normal",
        "Authenticity": "normal",
        "ImageQuality": "normal",
    }
    if back:
        body = {
            "images": [
                {"image": _b64(front), "page_idx": 0},
                {"image": _b64(back), "page_idx": 1},
            ],
            "options": {
                "multipageProcessing": True,
                "response": response,
            },
        }
    else:
        body = {
            "images": [_b64(front)],
            "options": {"response": response},
        }

    try:
        r = requests.post(
            f"{API}/api/document/liveness",
            json=body,
            timeout=180,
        )
    except Exception as ex:  # noqa: BLE001
        return f"Request failed: {ex}", "", "", "", ""

    try:
        payload = r.json()
    except Exception:  # noqa: BLE001
        return f"Invalid JSON (HTTP {r.status_code})", "", "", "", r.text or ""

    if not isinstance(payload, dict):
        return "Unexpected response shape.", "", "", "", json.dumps(payload, indent=2)

    ident = identity_line(payload)
    overall = "\n\n".join(
        f"**{kind_label(row['kind'])}** · {row['result']}" for row in overall_results(payload)
    )
    ident = f"{ident}\n\n{overall}"
    if notes:
        ident = "\n\n".join(notes) + "\n\n" + ident
    return (
        ident,
        fields_html(payload),
        checks_html(payload),
        gallery_from_payload(payload),
        json.dumps(payload, indent=2),
    )



def main() -> None:
    examples = _document_examples()
    with gr.Blocks(title="Document Liveness Demo") as demo:
        license_md = gr.Markdown(value=_license_banner_md())
        with gr.Row(elem_classes=["ix-capture"]):
            with gr.Column(scale=1, elem_classes=["ix-pages"]):
                front = gr.Image(type="filepath", label="Front", height=300)
                back = gr.Image(type="filepath", label="Back", height=300)
            with gr.Column(scale=1, elem_classes=["ix-side"]):
                if examples:
                    gr.Examples(
                        examples,
                        inputs=[front, back],
                        label="Examples",
                        elem_id="ix-examples",
                    )
                btn = gr.Button("Check liveness", variant="primary")
        identity = gr.Markdown(
            value="Run Check liveness to see document type, score, and check counts.",
            elem_classes=["ix-ident"],
        )
        with gr.Row(elem_classes=["ix-work"]):
            with gr.Column(scale=55):
                fields = gr.HTML(elem_classes=["ix-grouped"])
                checks = gr.HTML(elem_classes=["ix-grouped"])
            with gr.Column(scale=45):
                gallery = ui.result_gallery(label="Images", columns=2)
        with gr.Accordion("Raw JSON", open=False):
            raw = gr.Code(language="json", label="API response")
        btn.click(
            document_process,
            inputs=[front, back],
            outputs=[identity, fields, checks, gallery, raw],
        )
        btn.click(lambda: _license_banner_md(), outputs=[license_md])
        demo.load(lambda: _license_banner_md(), outputs=[license_md])

    print(f"Gradio demo -> http://{DEMO_HOST}:{DEMO_PORT}  (API {API})")
    from server.port_guard import free_port

    free_port(DEMO_PORT)
    demo.launch(server_name=DEMO_HOST, server_port=DEMO_PORT, css=ui.RESULT_CSS)


if __name__ == "__main__":
    main()
