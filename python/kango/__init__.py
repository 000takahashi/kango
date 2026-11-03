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
# 乗っ取りの入口によくある頼みごと（顔認証・指紋・パスキーそのものではなく、本人に操作させる手口）。
# 言葉だけでは赤にしない＝黄まで。照合は正規化した文面（NFKC・小文字）に対して行う。
TAKEOVER = (
    (r"(パスキー|顔認証|指紋認証|生体認証).{0,6}(再登録|再設定|作り直|登録し直|設定し直|登録をし直|設定をし直)",
     "パスキーや顔認証を作り直させようとする"),
    (r"(自撮り|セルフィー|顔写真(?!付)|顔の(写真|画像|動画)).{0,30}(身分証|免許証|マイナンバーカード|パスポート|在留カード|送信|送って|送付|アップロード)",
     "顔写真や身分証を送らせようとする"),
    (r"(身分証|免許証|マイナンバーカード|パスポート|在留カード).{0,30}(自撮り|セルフィー|顔写真(?!付)|顔の(写真|画像|動画))",
     "顔写真や身分証を送らせようとする"),
    (r"(アカウント|ログイン).{0,6}(復旧|復元|ロック解除|ロックを解除|制限解除|制限を解除)",
     "アカウントの復旧を名目に操作させる"),
    (r"(確認コード|認証コード|認証番号|ワンタイムパスワード|セキュリティコード|qrコード|二次元コード|[0-9]桁の(番号|コード|数字)).{0,20}(教えて|伝えて|読み上げて|お知らせください|返信して|読み取って|読みとって|スキャンして)",
     "確認コードやQRコードを渡させようとする"),
    (r"(遠隔操作|リモート操作|リモートサポート|画面共有|画面を共有|anydesk|teamviewer|quick ?support|クイックサポート|airdroid)",
     "遠隔操作や画面共有をさせようとする"),
)
_TAKEOVER = tuple((re.compile(p), r) for p, r in TAKEOVER)
# リンク＝ http: か https: のあとに / か \ が続く文字の並び（ブラウザは \ も / とみなし、/ が1つでも開く）。
# 空白・かぎかっこ・山かっこ・引用符・閉じかっこ・読点「、」で終わる。
_URL = re.compile(r"https?:[/\\]+[^\s「」『』【】<>\"'）)、]+", re.I)
# リンクの「住所の部分」（最初の / \ ? # まで）
_AUTH = re.compile(r"https?:[/\\]+([^/\\?#]*)", re.I)
# 見た目の「住所の部分」（\ を区切りと思わずに読んだ時。ここに @ や \ があれば見せかけ）
_SHOWN = re.compile(r"https?:[/\\]+([^/?#]*)", re.I)
# https:// の無いリンク（rakuten-card-login.com/abc など。メッセージアプリはこれも押せるリンクにする）。
# 英数字とハイフンの並びを . でつなぎ、最後が英字2〜24文字。前後に英数字や @ が付くもの（メールアドレスなど）は数えない。
_BARE = re.compile(r"(?<![a-z0-9@._%+\-])((?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,24})(?![a-z0-9\-@])"
                   r"(?:[/?#][^\s「」『』【】<>\"'）)、]*)?", re.I)
# ファイル名（meisai.pdf など）は住所として数えない（どれもトップレベルドメインではない）
_FILE_EXT = frozenset("pdf html htm jpg jpeg png gif txt csv doc docx xls xlsx ppt pptx js css json xml php exe apk".split())
# 住所にふつう使う文字（英小文字・数字・. ・-）。これ以外を含む住所＝見た目を似せる手口か、壊れた住所
_HOST_OK = re.compile(r"[a-z0-9.\-]+")
# 電話番号＝0（または +81）で始まり、区切り（空白・かっこ・ハイフン類＝数字の間に3文字まで）を除いて10〜11桁（+81 の時は9〜10桁）。
# 前後に数字が続くもの（注文番号など）は数えない。番号が本物かは確かめられない＝黄まで。
_PHONE = re.compile(r"(?<![0-9])(?:\+81[ ()\-‐−–ー]{0,3}|0)[1-9](?:[ ()\-‐−–ー]{0,3}[0-9]){8,9}(?![0-9])")
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
    """リンクの本当の行き先の住所（ホスト名）。ブラウザと同じ読み方をする：
    \\ は / と同じ・@ より前（利用者名とパスワード）は住所ではない・: の後ろは番号（ポート）・「。」は「.」と同じ。"""
    m = _AUTH.match(url)
    if not m:
        return None
    h = m.group(1).rsplit("@", 1)[-1]
    h = h.split("]", 1)[0] + "]" if h.startswith("[") else h.split(":", 1)[0]
    h = h.replace("。", ".").lower().rstrip(".")
    return h or None


def _scan(text: str):
    """文面を、リンク・https:// の無いリンクの住所・それ以外の文字（電話番号を探す所）に分ける。"""
    t = unicodedata.normalize("NFKC", text or "")
    urls = _URL.findall(t)
    rest = _URL.sub(" ", t)
    bare = [m.group(1).lower() for m in _BARE.finditer(rest)
            if m.group(1).rsplit(".", 1)[-1].lower() not in _FILE_EXT]
    return urls, bare, _BARE.sub(" ", rest)


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
    urls, bare, plain = _scan(text)
    hosts = [h for h in (host_of(u) for u in urls) if h] + bare
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

    # 「@」や「\」で本当の行き先をごまかす書き方（https://本物の住所@偽の住所/・https://偽の住所\@本物の住所/）
    tricked = [host_of(u) for u in urls if any(c in _SHOWN.match(u).group(1) for c in "@\\")]
    for h in dict.fromkeys(h for h in tricked if h):
        say("disguised", f"リンクの住所に「@」や「\\」を使った見せかけがあります。本当の行き先は「{h}」です。", 2)

    for h in dict.fromkeys(hosts):   # 同じ住所は1回だけ
        if h in SHORTENERS:
            say("shortener", f"リンク（{h}）は短縮URLで、行き先が見えません。", 1)
            continue
        if h.startswith("xn--") or ".xn--" in h or not _HOST_OK.fullmatch(h):
            say("idn", f"リンク先「{h}」は、ふつうの住所には使わない文字を含んでいます。見た目を似せる手口に使われます。", 2)
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

    # リンク（https:// の無いものも）の中の数字は数えない（住所はリンクとして照合済み）
    if _PHONE.search(plain):
        say("phone", "電話番号が書かれています。この番号が本物かは確かめられません。"
            "電話する時は、公式サイトやカードの裏面など、自分で確かめた番号からかけてください。", 1)

    tricks = list(dict.fromkeys(r for w, r in PRESSURE if w in low))
    if tricks:
        say("pressure", "詐欺によくある言いまわし：" + "、".join(tricks) + "。", 1)

    asks = list(dict.fromkeys(r for p, r in _TAKEOVER if p.search(low)))
    if asks:
        say("takeover", "乗っ取りの入口によくある頼みごと：" + "、".join(asks) + "。"
            "本物の会社は、ふつうメールやSMSのリンク・電話でこれを頼みません。公式アプリから自分で確かめてください。", 1)

    # 何ひとつ照らし合わせられなかった（配送・郵便・国税庁を名乗り、リンクが無い等）＝青にしない。
    # 青は、何か1つでも割符が合った時（in_ledger・official）だけ。
    if not reasons:
        say("nothing_to_check", "割符（契約している会社）や公式の住所へのリンクなど、照らし合わせられるものがありませんでした。", 1)

    level = ("green", "amber", "red")[rank]
    return {"level": level, "head": HEADS[level], "reasons": reasons, "todo": TODO[level],
            "helplines": HELPLINES if level != "green" else [],
            "claimed": [b["id"] for b in claimed], "hosts": list(dict.fromkeys(hosts))}
