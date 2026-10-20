"""Document Liveness Python kit — ctypes bindings to libDocLivenessSDK.so (lib/cpu/).

Product wrapper exports the DocumentFullSDK_* C ABI (same symbols as Full).
"""

from __future__ import annotations

import base64
import ctypes
import io
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "lib" / "cpu"
SO = LIB / "libDocLivenessSDK.so"
ENGINE = LIB / "libdcrliveness.so"

os.chdir(ROOT)
os.environ["LD_LIBRARY_PATH"] = str(LIB) + (
    (":" + os.environ["LD_LIBRARY_PATH"]) if os.environ.get("LD_LIBRARY_PATH") else ""
)

if not SO.is_file():
    raise FileNotFoundError(
        f"missing {SO} — run: download the runtime zip from https://github.com/identixia-IDV/ID-Document-Liveness-Detection-Docker/releases/latest into lib/cpu "
        "(export copies SDK lib/ → App lib/cpu/)"
    )

# Engine first so wrapper dlopen resolves; RTLD_GLOBAL matches Face Docker Apps.
if ENGINE.is_file():
    ctypes.CDLL(str(ENGINE), mode=os.RTLD_GLOBAL)
_dll = ctypes.CDLL(str(SO), mode=os.RTLD_GLOBAL)

_dll.DocumentFullSDK_initialize.restype = ctypes.c_int
_dll.DocumentFullSDK_initialize.argtypes = []
_dll.DocumentFullSDK_activate.restype = ctypes.c_int
_dll.DocumentFullSDK_activate.argtypes = [ctypes.c_char_p]
_dll.DocumentFullSDK_getMachineCode.restype = ctypes.c_int
_dll.DocumentFullSDK_getMachineCode.argtypes = [ctypes.c_char_p]
_dll.DocumentFullSDK_documentProcess.restype = ctypes.c_int
_dll.DocumentFullSDK_documentProcess.argtypes = [
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_char_p,
]
_dll.DocumentFullSDK_generalProcess.restype = ctypes.c_int
_dll.DocumentFullSDK_generalProcess.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]


def _opt_sym(name, restype, argtypes):
    fn = getattr(_dll, name, None)
    if fn is None:
        return None
    fn.restype = restype
    fn.argtypes = argtypes
    return fn


_start_new_session = _opt_sym(
    "DocumentFullSDK_startNewSession", ctypes.c_int, [ctypes.c_char_p, ctypes.c_char_p]
)
_start_new_page = _opt_sym(
    "DocumentFullSDK_startNewPage", ctypes.c_int, [ctypes.c_char_p, ctypes.c_char_p]
)
_unload = _opt_sym("DocumentFullSDK_unload", ctypes.c_int, [ctypes.c_char_p])
_get_license_status = _opt_sym(
    "DocumentFullSDK_getLicenseStatus", ctypes.c_int, [ctypes.c_char_p]
)


_MC_BUF = 768
_STATUS_BUF = 512
_OUT_MIN = 1_000_000
_OUT_MAX = 16 * 1024 * 1024
_MAX_IMG = 8 * 1024 * 1024


def _b(v) -> bytes:
    if v is None:
        return b""
    if isinstance(v, bytes):
        return v
    return str(v).encode("utf-8")


def _out(*parts: bytes):
    n = min(max(_OUT_MIN, sum(len(p) for p in parts) * 2 + 262144), _OUT_MAX)
    return ctypes.create_string_buffer(n)


def _fit_b64(image_b64: str, max_bytes: int = _MAX_IMG) -> bytes:
    """Normalize stills to baseline JPEG for the engine. PDFs stay as-is.

    Always re-encodes raster images (do not pass through source JPEGs). Some
    camera/sample JPEGs decode for OCR but fail barcode until re-saved.
    """
    raw = _b(image_b64).strip()
    data = base64.b64decode(raw, validate=False)
    if data[:4] == b"%PDF":
        return raw
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(data))
        img.load()
        if getattr(img, "n_frames", 1) > 1:
            img.seek(0)
        img = img.convert("RGB")
    except Exception:
        return raw

    def _jpeg(im, quality: int) -> bytes:
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=quality, optimize=True)
        return base64.b64encode(buf.getvalue())

    out = _jpeg(img, 90)
    edge = max(img.size)
    while len(out) > max_bytes and edge > 640:
        edge = int(edge * 0.85)
        thumb = img.copy()
        thumb.thumbnail((edge, edge), Image.Resampling.LANCZOS)
        out = _jpeg(thumb, 85)
    return out


def get_machine_code() -> str:
    """Return … machine code."""
    buf = ctypes.create_string_buffer(_MC_BUF)
    _dll.DocumentFullSDK_getMachineCode(buf)
    return buf.value.decode("utf-8", errors="replace")




def get_license_status() -> dict:
    """Return license capability dict from DocumentFullSDK_getLicenseStatus."""
    fallback = {
        "licensed": False,
        "level": -1,
        "levelName": "None",
        "recognition": False,
        "authenticity": False,
        "label": "No license",
    }
    if _get_license_status is None:
        return fallback
    buf = ctypes.create_string_buffer(_STATUS_BUF)
    if int(_get_license_status(buf)) != 0:
        return fallback
    try:
        data = json.loads(buf.value.decode("utf-8", errors="replace") or "{}")
        return data if isinstance(data, dict) else fallback
    except Exception:  # noqa: BLE001
        return fallback




def activate(license_path: str) -> int:
    """Activate with a license file path, or a license key string."""
    return int(_dll.DocumentFullSDK_activate(_b(license_path)))


def init_sdk() -> int:
    return int(_dll.DocumentFullSDK_initialize())


def start_new_session(options: dict | None = None) -> str:
    """Start a document session."""
    if _start_new_session is None:
        return '{"msg":"DocumentFullSDK_startNewSession not in this libDocLivenessSDK.so"}'
    opts = options or {"scenario": "FullProcess", "series": False}
    options_b = _b(json.dumps(opts, separators=(",", ":")))
    out = _out(options_b)
    _start_new_session(options_b, out)
    return out.value.decode("utf-8", errors="replace")


def start_new_page(options: dict | None = None) -> str:
    """Start an additional page in the current session."""
    if _start_new_page is None:
        return '{"msg":"DocumentFullSDK_startNewPage not in this libDocLivenessSDK.so"}'
    opts = options or {}
    options_b = _b(json.dumps(opts, separators=(",", ":")))
    out = _out(options_b)
    _start_new_page(options_b, out)
    return out.value.decode("utf-8", errors="replace")


def unload() -> str:
    """Unload the SDK."""
    if _unload is None:
        return '{"msg":"DocumentFullSDK_unload not in this libDocLivenessSDK.so"}'
    out = _out()
    _unload(out)
    return out.value.decode("utf-8", errors="replace")


def document_process(images, rfid: str = "", options: dict | None = None) -> str:
    opts = dict(options or {
        "response": {
            "OCR": "normal",
            "MRZ": "normal",
            "Barcode": "normal",
            "ImageQuality": "normal",
            "Authenticity": "normal",
        }
    })
    items = list(images or [])
    multipage = len(items) >= 2
    if multipage and "multipageProcessing" not in opts:
        opts["multipageProcessing"] = True
    norm = []
    for i, item in enumerate(items):
        if isinstance(item, dict):
            entry = {"image": _fit_b64(item["image"]).decode()}
            if item.get("page_idx") is not None:
                entry["page_idx"] = int(item["page_idx"])
            elif multipage:
                entry["page_idx"] = i
            # Visible light (6), same as mobile stills — helps back-side barcode.
            if item.get("light") is not None:
                entry["light"] = int(item["light"])
            elif multipage:
                entry["light"] = 6
            norm.append(entry)
        else:
            if multipage:
                norm.append(
                    {"image": _fit_b64(item).decode(), "page_idx": i, "light": 6}
                )
            else:
                norm.append(_fit_b64(item).decode())
    images_json = _b(json.dumps(norm, separators=(",", ":")))
    options_b = _b(json.dumps(opts, separators=(",", ":")))
    rfid_b = _b(rfid or "")
    out = _out(images_json, rfid_b, options_b)
    _dll.DocumentFullSDK_documentProcess(images_json, rfid_b, options_b, out)
    return out.value.decode("utf-8", errors="replace")


def general_process(image: str, options: dict | None = None) -> str:
    opts = options or {}
    image_b = _fit_b64(image)
    options_b = _b(json.dumps(opts, separators=(",", ":")))
    out = _out(image_b, options_b)
    _dll.DocumentFullSDK_generalProcess(image_b, options_b, out)
    return out.value.decode("utf-8", errors="replace")




_RECOGNITION_RESPONSE = {
    "OCR": "normal",
    "MRZ": "normal",
    "Barcode": "normal",
    "ImageQuality": "normal",
    "Authenticity": "none",
    "RFID": "none",
}


_LIVENESS_RESPONSE = {
    "OCR": "none",
    "MRZ": "none",
    "Barcode": "none",
    "ImageQuality": "none",
    "Authenticity": "normal",
    "RFID": "none",
}




def _forced_process_options(response: dict, extra: dict | None) -> dict:
    opts = dict(extra or {})
    opts.pop("response", None)
    opts["response"] = dict(response)
    return opts




def document_recognition(images, rfid: str = "", extra: dict | None = None) -> str:
    """OCR / MRZ / barcode / image quality only. Authenticity is always off."""
    return document_process(
        images, rfid, _forced_process_options(_RECOGNITION_RESPONSE, extra)
    )




def document_liveness(images, rfid: str = "", extra: dict | None = None) -> str:
    """Authenticity / security only. OCR / MRZ / barcode / image quality are always off."""
    return document_process(
        images, rfid, _forced_process_options(_LIVENESS_RESPONSE, extra)
    )
