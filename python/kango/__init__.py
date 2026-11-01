"""勘合（kango）— 届いた連絡を「自分の契約台帳」と「会社の公式ドメイン」の2つの割符で照合する。

  from kango import judge
  judge("【楽天カード】ご請求額が確定しました https://www.rakuten-card.co.jp/", ledger=["rakuten"])
  # -> {"level": "green" | "amber" | "red", "head": ..., "reasons": [...], ...}

守る線：AIを使わない（決定的な照合だけ）／「本物」「安全」と断定しない／文面を保存しない・送らない／
リンク先へアクセスしない。規則の説明は リポジトリの SPEC.md。
"""
from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path
from typing import Iterable, List, Optional

__all__ = ["judge", "load_brands", "BRANDS", "host_of", "is_official", "mimicked_brand"]


def _split(v: str) -> List[str]:
    return [s.strip() for s in (v or "").split("|") if s.strip()]


def load_brands(path: Optional[Path] = None) -> List[dict]:
    path = path or Path(__file__).with_name("brands.csv")
    with open(path, encoding="utf-8") as f:
        return [{"id": r["id"], "name": r["name"], "kind": r["kind"],
                 "words": _split(r["words"]), "domains": _split(r["domains"]),
                 "stems": _split(r["stems"]), "checked": r.get("checked") or None}
                for r in csv.DictReader(f)]


BRANDS = load_brands()

SHORTENERS = ("bit.ly", "t.co", "tinyurl.com", "is.gd", "x.gd", "t.ly", "cutt.ly", "ow.ly", "rebrand.ly")
# 詐欺によくある言いまわし（言葉ひとつでは赤にしない＝黄まで）
PRESSURE = (
    ("停止", "アカウントの停止で急がせる"), ("凍結", "凍結をちらつかせる"),
    ("24時間以内", "期限で急がせる"), ("本日中", "期限で急がせる"),
    ("支払い情報", "支払い情報を入力させようとする"), ("お支払い方法", "支払い方法を更新させようとする"),
    ("カード情報", "カード情報を求める"), ("暗証番号", "暗証番号を求める（正規の会社は聞きません）"),
    ("パスワード", "パスワードの入力を求める"), ("ギフトカード", "ギフトカードでの支払いを求める"),
    ("未納", "未納を理由に払わせる"), ("不在", "不在通知を装う"),
    ("ご本人確認", "本人確認を名目に入力させる"), ("異常なログイン", "不正ログインで不安をあおる"),
)
_URL = re.compile(r"https?://[^\s「」<>\"'）)]+", re.I)
# 見た目が似た文字（amaz0n・rakuten → rakut3n 等）を戻してから似せた住所を探す
_LOOKALIKE = str.maketrans({"0": "o", "1": "l", "3": "e", "5": "s", "4": "a"})

HEADS = {"green": "割符が合いました", "amber": "確かめきれません",
         "red": "割符が合いません。偽物の疑いが強いです"}
TODO = {
    "green": "念のため、リンクではなく公式アプリやいつものブックマークから開いて確かめてください。",
    "amber": "リンクは押さずに、公式アプリやいつものブックマークから開いて確かめてください。",
    "red": "リンクは押さないでください。入力してしまった時は、すぐにパスワードを変え、カード会社や銀行に連絡してください。",
}
HELPLINES = [{"label": "警察相談専用電話", "tel": "#9110"}, {"label": "消費者ホットライン", "tel": "188"}]


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").lower()


def host_of(url: str) -> Optional[str]:
    m = re.match(r"https?://([^/?#:]+)", url, re.I)
    return m.group(1).lower().rstrip(".") if m else None


def is_official(host: str, brand: dict) -> bool:
    return any(host == d or host.endswith("." + d) for d in brand["domains"])


def mimicked_brand(host: str, brands: Iterable[dict]) -> Optional[dict]:
    """公式でない住所に、会社の名前（似せた文字も含む）が入っていれば その会社。"""
    plain = host.translate(_LOOKALIKE)
    for b in brands:
        if is_official(host, b):
            continue
        if any(st in host or st in plain for st in b["stems"]):
            return b
    return None


def judge(text: str, ledger: Iterable[str], brands: Optional[List[dict]] = None) -> dict:
    """勘合の判定（決定的・純粋）。level は green / amber / red。"""
    brands = BRANDS if brands is None else brands
    owned = set(ledger or ())
    low = _norm(text)
    claimed = [b for b in brands if any(_norm(w) in low for w in b["words"])]
    hosts = [h for h in (host_of(u) for u in _URL.findall(unicodedata.normalize("NFKC", text or ""))) if h]
    reasons: List[dict] = []
    rank = 0   # 0 green / 1 amber / 2 red

    def say(code: str, msg: str, level: int) -> None:
        nonlocal rank
        reasons.append({"code": code, "text": msg})
        rank = max(rank, level)

    if not claimed:
        say("no_claim", "どの会社を名乗っているか読み取れませんでした。", 1)
    for b in claimed:
        if b["kind"] == "contract" and b["id"] not in owned:
            say("not_in_ledger", f"「{b['name']}」を名乗っていますが、あなたの割符（契約している会社）にありません。", 2)
        elif b["kind"] == "contract":
            say("in_ledger", f"「{b['name']}」はあなたの割符にあります。", 0)

    for h in dict.fromkeys(hosts):   # 同じ住所は1回だけ
        if h in SHORTENERS:
            say("shortener", f"リンク（{h}）は短縮URLで、行き先が見えません。", 1)
            continue
        if h.startswith("xn--") or ".xn--" in h:
            say("idn", f"リンク先「{h}」は、見た目を似せやすい特殊な文字の住所です。", 2)
            continue
        owner = next((b for b in brands if is_official(h, b)), None)
        if claimed and not any(is_official(h, b) for b in claimed):
            look = mimicked_brand(h, claimed)
            if look:
                say("mimic", f"リンク先「{h}」は「{look['name']}」に似せた住所ですが、公式の住所ではありません。", 2)
            else:
                say("off_domain", f"リンク先「{h}」は、名乗った会社の公式の住所ではありません。", 2)
        elif owner:
            say("official", f"リンク先「{h}」は「{owner['name']}」の公式の住所と一致しました。", 0)
        else:
            look = mimicked_brand(h, brands)
            if look:
                say("mimic", f"リンク先「{h}」は「{look['name']}」に似せた住所ですが、公式の住所ではありません。", 2)
            else:
                say("unknown_domain", f"リンク先「{h}」は、登録された公式の住所ではありません。", 1)

    tricks = list(dict.fromkeys(r for w, r in PRESSURE if w in low))
    if tricks:
        say("pressure", "詐欺によくある言いまわし：" + "、".join(tricks) + "。", 1)

    level = ("green", "amber", "red")[rank]
    return {"level": level, "head": HEADS[level], "reasons": reasons, "todo": TODO[level],
            "helplines": HELPLINES if level != "green" else [],
            "claimed": [b["id"] for b in claimed], "hosts": list(dict.fromkeys(hosts))}
