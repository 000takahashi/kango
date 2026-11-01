"""見本の形では書けない約束を確かめる（swift/Tests/KangoTests/JudgeTests.swift と同じこと）。

色と理由のコードは、test_conformance.py が共通の見本（conformance/cases.json）で確かめています。"""
import json
from pathlib import Path

import kango

ROOT = Path(__file__).resolve().parents[2]
CASES = json.loads((ROOT / "conformance" / "cases.json").read_text(encoding="utf-8"))


def _all():
    for case in CASES["cases"]:
        yield case, kango.judge(case["text"], case.get("ledger", CASES["ledger"]))


def test_brands_load():
    assert any(b["id"] == "amazon" and b["kind"] == "contract" for b in kango.BRANDS)
    assert any(b["id"] == "yamato" and b["kind"] == "everyone" for b in kango.BRANDS)


def test_green_never_says_genuine_or_safe():
    # 青は「割符が合いました」まで。「本物です」「安全です」とは言わない
    for case, r in _all():
        if r["level"] == "green":
            words = r["head"] + r["todo"] + "".join(x["text"] for x in r["reasons"])
            assert "本物" not in words and "安全" not in words, case["text"]


def test_helplines_unless_green():
    # 青以外では、相談先（#9110・188）を添える
    for case, r in _all():
        tels = [h["tel"] for h in r["helplines"]]
        assert tels == ([] if r["level"] == "green" else ["#9110", "188"]), case["text"]
