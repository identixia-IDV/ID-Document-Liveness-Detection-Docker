"""Contract tests for the customer process JSON — no native library required."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "demo"))

from ix_payload import document, fields, is_document_json  # noqa: E402
from result_view import build_result_view, check_groups, field_groups, overall_results  # noqa: E402
from security_view import security_view_from_payload  # noqa: E402

FIXTURE = json.loads((Path(__file__).resolve().parent / "document-process.json").read_text(encoding="utf-8"))
ALLOWED = {"session", "identity", "readings", "tests", "images"}


def test_top_level_keys():
    extra = set(FIXTURE) - ALLOWED
    assert not extra
    assert list(FIXTURE) == ["identity", "readings", "tests", "images", "session"]
    assert "documentName" not in FIXTURE
    assert "ocr" not in FIXTURE
    assert "security" not in FIXTURE
    assert "api" not in FIXTURE
    assert is_document_json(FIXTURE)


def test_field_rows():
    rows = fields(FIXTURE)
    assert rows[0]["name"] == "familyName"
    assert rows[0]["value"] == "DOE"
    assert rows[0]["origin"] == "visual"
    assert "score" in rows[0]


def test_ui_renders_without_native_library():
    summary, rows = build_result_view(FIXTURE)
    assert "Passport" in summary
    assert any(r[0] == "familyName" and "DOE" in r[1] and r[2] == "visual" for r in rows)
    sec_summary, sec_rows = security_view_from_payload(FIXTURE)
    assert "Passport" in sec_summary
    assert sec_rows[0][1] == "foilCheck"
    assert document(FIXTURE)["class"] == "Passport"


def test_overall_results_golden_all_pass():
    assert overall_results(FIXTURE) == [
        {"kind": "validity", "result": "pass"},
        {"kind": "capture", "result": "pass"},
        {"kind": "authenticity", "result": "pass"},
    ]


def test_overall_results_fail_wins():
    payload = json.loads(json.dumps(FIXTURE))
    payload["tests"].append({"name": "expiry2", "group": "validity", "outcome": "fail"})
    payload["tests"].append({"name": "glare", "group": "capture", "outcome": "hold"})
    rows = {r["kind"]: r["result"] for r in overall_results(payload)}
    assert rows == {"validity": "fail", "capture": "pass", "authenticity": "pass"}


def test_field_groups_by_source_order():
    groups = field_groups(FIXTURE)
    assert [g["source"] for g in groups] == ["visual", "zone"]
    assert [item["id"] for item in groups[0]["items"]] == ["familyName", "firstNames"]
    assert groups[1]["items"][0]["id"] == "docNumber"
    assert groups[0]["items"][0]["value"] == "DOE"
    assert groups[0]["items"][0]["score"]


def test_check_groups_kind_order_fail_first():
    payload = json.loads(json.dumps(FIXTURE))
    payload["tests"].append({"name": "expiry2", "group": "validity", "outcome": "fail", "note": "expired"})
    payload["tests"].append({"name": "glare", "group": "capture", "outcome": "hold"})
    groups = check_groups(payload)
    assert [g["kind"] for g in groups] == ["validity", "capture", "authenticity"]
    assert [item["id"] for item in groups[0]["items"]] == ["expiry2", "expiry"]
    assert groups[0]["items"][0]["result"] == "fail"
    assert groups[0]["items"][0]["extra"] == "expired"
    assert [item["id"] for item in groups[1]["items"]] == ["focus", "glare"]
