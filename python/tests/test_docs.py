"""docs/threat-model.md の表（手口と勘合の答え）が、勘合の本当の答えと同じかを確かめる。
表を直したのに勘合と食い違っていたら、ここで落ちる（swift/Tests/KangoTests/DocsTests.swift と同じ確かめ方）。"""
from pathlib import Path

import kango

LEDGER = ["amazon", "rakuten", "docomo", "yucho"]
LEVELS = {"青": "green", "黄": "amber", "赤": "red"}
DOC = Path(__file__).resolve().parents[2] / "docs" / "threat-model.md"


def _rows():
    """| 手口 | `文面の例` | 答え | `理由のコード` … | の行を読む。"""
    for line in DOC.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        if len(cells) < 6 or cells[3] not in LEVELS:
            continue
        example = cells[2].split("`")
        if len(example) < 3:
            continue
        yield example[1], LEVELS[cells[3]], cells[4].split("`")[1::2]


def test_threat_model_table_matches_judge():
    rows = list(_rows())
    assert len(rows) >= 20, "表が読めていません"
    for text, level, codes in rows:
        r = kango.judge(text, LEDGER)
        assert (r["level"], [x["code"] for x in r["reasons"]]) == (level, codes), text
