"""コマンド（python -m kango）のテスト。"""
import io
import json

import pytest

from kango.__main__ import main

TEXT = "【楽天カード】ご請求額が確定しました https://www.rakuten-card.co.jp/"


def test_prints_the_verdict_and_reason_codes(capsys):
    assert main(["--ledger", "rakuten", TEXT]) == 0
    out = capsys.readouterr().out
    assert out.startswith("青：割符が合いました\n")
    assert "（in_ledger）" in out and "（official）" in out and "相談先" not in out


def test_reads_the_text_from_stdin(capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("【三菱UFJ銀行】口座が凍結されています"))
    assert main(["--ledger", "rakuten,docomo"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("赤：") and "（not_in_ledger）" in out
    assert "#9110" in out and "188" in out


def test_json(capsys):
    assert main(["--json", "--ledger", "rakuten", TEXT]) == 0
    v = json.loads(capsys.readouterr().out)
    assert v["level"] == "green" and [r["code"] for r in v["reasons"]] == ["in_ledger", "official"]


def test_empty_ledger_is_allowed_but_noted(capsys):
    assert main(["--json", TEXT]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["level"] == "red" and "台帳が空です" in captured.err


def test_brands(capsys):
    assert main(["--brands"]) == 0
    rows = [line.split("\t") for line in capsys.readouterr().out.splitlines()]
    assert ["amazon", "Amazon", "contract"] == rows[0][:3]
    assert any(r[0] == "yamato" and r[2] == "everyone" for r in rows)


def test_unknown_ledger_id_is_an_error(capsys):
    # 打ち間違えた id を黙って無視すると、本物の連絡が赤になるので止める
    with pytest.raises(SystemExit) as e:
        main(["--ledger", "rakuton", TEXT])
    assert e.value.code == 2 and "rakuton" in capsys.readouterr().err


def test_empty_text_is_an_error(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("  \n"))
    with pytest.raises(SystemExit) as e:
        main(["--ledger", "rakuten"])
    assert e.value.code == 2
