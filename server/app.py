#!/usr/bin/env python3
"""Flask HTTP API — thin server over the sdk package (DocumentReader, Linux).

Exposes /api/* for Postman, curl, and the Gradio demo (``python3 demo``). Does not embed Gradio.
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

import json
import os
from pathlib import Path

def _load_env() -> None:
    """Load repo-root ``.env`` without overriding real process env.

    Prefers python-dotenv when installed; otherwise parses KEY=VALUE lines so
    LICENSE is always available at bootstrap even in minimal venvs.
    """
    env_path = _APP_ROOT / ".env"
    try:
        from dotenv import load_dotenv
    except ImportError:
        load_dotenv = None  # type: ignore[assignment]
    if load_dotenv is not None:
        load_dotenv(env_path, override=False)
        return
    if not env_path.is_file():
        return
    import os
    for raw in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if not key or key in os.environ:
            continue
        val = val.strip()
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        os.environ[key] = val



_load_env()

from flask import Flask, Response, request
from werkzeug.exceptions import HTTPException

import http_body
import license_ux
import sdk

ROOT = _APP_ROOT
app = Flask(__name__)


def envelope(success: bool, code: int, message: str, data=None, status: int = 200):
    return Response(
        json.dumps(
            {
                "success": success,
                "code": code,
                "message": message,
                "request_id": None,
                "data": data,
            }
        ),
        status=status,
        mimetype="application/json",
    )


def sdk_json(result):
    raw = result if isinstance(result, (bytes, bytearray)) else str(result).encode()
    return Response(raw, mimetype="application/json")


@app.after_request
def cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


@app.route("/api/<path:_unused>", methods=["OPTIONS"])
def options(_unused):
    return Response(status=204)


@app.get("/api/health")
def health():
    return envelope(True, 0, "OK", {"status": "ok"})


@app.get("/api/machinecode")
def machinecode():
    return envelope(True, 0, "OK", {"machinecode": sdk.get_machine_code()})


@app.get("/api/licenseStatus")
def license_status():
    license_ux.ensure_ready(ROOT, sdk.activate, sdk.init_sdk)
    return envelope(True, 0, "OK", sdk.get_license_status())


@app.get("/api/backend")
def backend():
    name = (os.environ.get("IDENTIXIA_BACKEND") or os.environ.get("IDENTIXIA_BACKEND") or "cpu").strip().lower()
    return envelope(
        True,
        0,
        "OK",
        {
            "product": "DocumentLiveness",
            "sdk_version": "1.0.0",
            "backend": name or "cpu",
        },
    )


@app.post("/api/activate")
def activate():
    raw = http_body.activate_license_bytes()
    if not raw:
        return envelope(False, -1, "Empty license", None)
    path = license_ux.save_license(ROOT, raw)
    res = sdk.activate(str(path))
    if hasattr(license_ux, "remember_loaded"):
        license_ux.remember_loaded(ROOT)
    if hasattr(license_ux, "mark_sdk_ready"):
        license_ux.mark_sdk_ready(False)
    mc = sdk.get_machine_code()
    if hasattr(license_ux, "ACTIVATION_ENGINE_FAILED") and res == license_ux.ACTIVATION_ENGINE_FAILED:
        return envelope(
            False,
            -2,
            "License accepted but engine failed to start",
            {"activated": True, "initialized": False, "machinecode": mc},
        )
    if res != 0:
        return envelope(
            False,
            -1,
            "Invalid license",
            {"activated": False, "initialized": False, "machinecode": mc},
        )
    if sdk.init_sdk() != 0:
        return envelope(
            False,
            -2,
            "License accepted but engine failed to start",
            {"activated": True, "initialized": False, "machinecode": mc},
        )
    if hasattr(license_ux, "mark_sdk_ready"):
        license_ux.mark_sdk_ready(True)
    return envelope(
        True,
        0,
        "Successfully activated",
        {"activated": True, "initialized": True, "machinecode": mc},
    )



def _split_document_pages():
    data = http_body.parse_body()
    images = data.get("images")
    if images is None:
        images = []
        # Legacy Postman/gitbook fields: image + image2 (also image1/front/back).
        for key in ("image", "image1", "image2", "front", "back"):
            if data.get(key) is not None:
                images.append(data[key])
    elif not isinstance(images, list):
        images = [images]
    norm = []
    for i, item in enumerate(images):
        if isinstance(item, dict):
            entry = dict(item)
            if entry.get("page_idx") is None and len(images) >= 2:
                entry["page_idx"] = i
            norm.append(entry)
        elif item is not None:
            if len(images) >= 2:
                norm.append({"image": item, "page_idx": i})
            else:
                norm.append(item)
    images = norm
    extra = {}
    if isinstance(data.get("options"), dict):
        extra.update({k: v for k, v in data["options"].items() if k != "response"})
        if "response" in data["options"]:
            extra["response"] = data["options"]["response"]
    elif "response" in data:
        # Overwritten by document_liveness forced flags.
        extra["response"] = data["response"]
    if "isCropped" in data:
        extra["isCropped"] = data["isCropped"]
    if "multipageProcessing" in data:
        extra["multipageProcessing"] = data["multipageProcessing"]
    elif len(images) >= 2:
        extra["multipageProcessing"] = True
    return images or [], data.get("rfid") or "", extra


@app.post("/api/document/liveness")
@app.post("/api/documentLiveness")
def document_liveness():
    """Authenticity / security only. Caller response flags are ignored."""
    license_ux.ensure_ready(ROOT, sdk.activate, sdk.init_sdk)
    images, rfid, extra = _split_document_pages()
    return sdk_json(sdk.document_liveness(images, rfid, extra or None))


@app.errorhandler(HTTPException)
def http_error(ex: HTTPException):
    if ex.code == 404:
        return envelope(False, -10, "Not found", None, 404)
    return envelope(False, -19, ex.description or str(ex), None, ex.code or 500)


@app.errorhandler(Exception)
def fail(ex: Exception):
    if isinstance(ex, HTTPException):
        return http_error(ex)
    return envelope(False, -19, str(ex), None, 500)


def main() -> None:
    license_ux.bootstrap(
        ROOT,
        get_machine_code=sdk.get_machine_code,
        activate=sdk.activate,
        init_sdk=sdk.init_sdk,
    )
    port = int(os.environ.get("PORT", os.environ.get("DOCSDK_PORT", "14107")))
    host = os.environ.get("HOST") or os.environ.get("DOCSDK_BIND_HOST", "0.0.0.0")
    print("API listening on http://{0}:{1}".format(host, port))
    try:
        import port_guard

        port_guard.free_port(port)
    except Exception as exc:
        # Inside Docker the port is rarely busy; never block API startup.
        print("port_guard skipped: {0}".format(exc))
    app.run(host=host, port=port, threaded=True)


if __name__ == "__main__":
    main()
