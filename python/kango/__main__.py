"""勘合をコマンドで試す。

  echo "【楽天カード】ご請求額が確定しました https://www.rakuten-card.co.jp/" | python -m kango --ledger rakuten
  python -m kango --ledger rakuten,docomo --json < message.txt
  python -m kango --brands

文面は保存せず、外へ送らず、リンク先へもアクセスしません。
届いた文面は、文面を省いて起動し、貼り付けてから Ctrl-D で渡すのがおすすめです（引数や echo で渡すと、シェルの履歴に文面が残ります）。
答えの色によらず、終了コードは 0 です（色は --json の "level" で読めます）。
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from . import BRANDS, judge

LABELS = {"green": "青", "amber": "黄", "red": "赤"}


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m kango",
        description="勘合で文面を照らし合わせ、青・黄・赤で答えます。"
                    "AI を使わず、文面を保存せず、リンク先へもアクセスしません。",
        epilog="届いた文面は、文面を省いて起動し、貼り付けてから Ctrl-D で渡すのがおすすめです"
               "（引数や echo で渡すと、シェルの履歴に文面が残ります）。",
    )
    p.add_argument("text", nargs="?", help="照らし合わせる文面（省くと標準入力から読みます）")
    p.add_argument("--ledger", default="", metavar="ID,ID",
                   help="契約台帳＝取引している会社の id をカンマ区切りで（例：rakuten,docomo）")
    p.add_argument("--json", action="store_true", help="答えを JSON で出す")
    p.add_argument("--brands", action="store_true", help="台帳に入れられる会社の一覧を出す（id・名前・種類・確かめた日）")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    p = _parser()
    a = p.parse_args(argv)

    if a.brands:
        for b in BRANDS:
            print("\t".join([b["id"], b["name"], b["kind"], b["checked"] or "未確認"]))
        return 0

    ledger = [s.strip() for s in a.ledger.split(",") if s.strip()]
    unknown = [s for s in ledger if s not in {b["id"] for b in BRANDS}]
    if unknown:
        p.error("会社の一覧にない id です：" + "、".join(unknown) + "（--brands で一覧を出せます）")
    if not ledger:
        print("（台帳が空です。取引している会社を --ledger で渡してください。--brands で一覧を出せます）", file=sys.stderr)

    text = a.text
    if text is None:
        if sys.stdin.isatty():
            print("文面を貼り付けて、最後に Ctrl-D（Windows は Ctrl-Z のあと Enter）を押してください。", file=sys.stderr)
        text = sys.stdin.read()
    if not text.strip():
        p.error("文面が空です")

    v = judge(text, ledger)
    if a.json:
        print(json.dumps(v, ensure_ascii=False, indent=2))
        return 0
    print(f"{LABELS[v['level']]}：{v['head']}")
    for r in v["reasons"]:
        print(f"・{r['text']}（{r['code']}）")
    print(f"次にすること：{v['todo']}")
    for h in v["helplines"]:
        print(f"相談先：{h['label']} {h['tel']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
