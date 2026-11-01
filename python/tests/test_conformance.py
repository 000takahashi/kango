"""共通の見本（conformance/cases.json）を、すべて動かして確かめる。

Swift の swift/Tests/KangoTests/ConformanceTests.swift も、同じ見本を動かします。
見本を足す時は cases.json に足してください（説明は conformance/README.md）。"""
import json
import re
from pathlib import Path

import pytest

import kango

ROOT = Path(__file__).resolve().parents[2]
CASES = json.loads((ROOT / "conformance" / "cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES["cases"])
def test_case(case):
    r = kango.judge(case["text"], case.get("ledger", CASES["ledger"]))
    got = {"level": r["level"], "codes": [x["code"] for x in r["reasons"]],
           "claimed": r["claimed"], "hosts": r["hosts"]}
    assert got == {k: case[k] for k in got}, f'{case["note"]}：{case["text"]}'


def test_every_reason_code_has_a_case():
    # SPEC.md の表にある理由のコードが、どれも1回は見本に出てくること（見本の無い規則を作らない）
    spec = set(re.findall(r"^\| `([a-z_]+)` \|", (ROOT / "SPEC.md").read_text(encoding="utf-8"), re.M))
    seen = {code for case in CASES["cases"] for code in case["codes"]}
    assert len(CASES["cases"]) >= 40, "見本が読めていません"
    assert spec == seen, (spec - seen, seen - spec)
