"""勘合の関所（せきしょ）— AI に渡す前の文書（.md など）に、隠れた命令や隠した文字が混ざっていないかを調べる。

  from kango.sekisho import check
  check(open("README.md", encoding="utf-8").read(), trusted_hosts=["github.com"])
  # -> {"level": "red" | "amber" | "none", "head": ..., "findings": [...], "sha256": ..., "approved": bool}

  python -m kango.sekisho 受け取った.md --trusted github.com

AI エージェントは、渡された文書の中の「指示らしい文」に従ってしまうことがあります（プロンプトインジェクション）。
関所は、AI に渡す前に、決まった規則だけで文書を調べ、見つけた場所（行と文字）を返します。

守る線（勘合と同じ）：AI を使わない（同じ入力には同じ答え）／「安全」と断定しない（何も見つからない時の答えは
"none"＝見つかりませんでした、で、青ではない）／文書を保存せず外へ送らない／リンク先へアクセスしない。
規則と、守れないことの説明は docs/sekisho.md。
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Iterable, List, Optional

__all__ = ["check", "fingerprint", "RULES"]

# 目に見えない文字。表示されないので、人には読めず AI にだけ届く。
#   ゼロ幅の文字・向きを変える文字（文字の並びを見た目と変える）・タグ文字（英字を丸ごと隠せる）
_INVISIBLE = re.compile("[​-‏‪-‮⁠-⁤⁦-⁩﻿\U000e0000-\U000e007f]")
_COMMENT = re.compile(r"<!--(.*?)-->", re.S)
# HTML で見えなくした所（display:none・visibility:hidden・文字の大きさ0・白い文字・hidden 属性）
_HIDDEN_STYLE = re.compile(
    r"<[a-z][^>]*(?:style\s*=\s*[\"'][^\"']*(?:display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0(?![.\d]*[1-9])"
    r"|color\s*:\s*(?:#fff(?:fff)?\b|white\b))|\shidden(?:\s|>|=))[^>]*>",
    re.I)
_URL = re.compile(r"https?://[^\s<>\"'`)\]]+", re.I)
_IMAGE = re.compile(r"!\[[^\]]*\]\(\s*(https?://[^\s)]+)", re.I)
_BASE64 = re.compile(r"[A-Za-z0-9+/]{120,}={0,2}")

# 言いまわしの規則：(コード, 言いまわし, 何が問題か, どう確かめるか)
# 言いまわしは、文書の外（目に見える所）にあれば黄、隠した所（コメント・見えない HTML）にあれば赤にする。
RULES = [
    ("override",
     r"(?:ignore|disregard|forget)\s+(?:all\s+|any\s+)?(?:the\s+)?(?:previous|prior|above|earlier)\s+(?:instructions?|prompts?|rules?)"
     r"|(?:以前|前|これまで|上記|今まで)の(?:指示|命令|ルール|設定|プロンプト)を(?:すべて|全て)?(?:無視|忘れ|取り消)"
     r"|system\s*prompt|システムプロンプト|you\s+are\s+now\b|あなたは(?:今から|これから)",
     "AI への指示を書きかえようとする言いまわしです。",
     "この文書が、AI の役割や指示を変える必要のある文書か確かめてください。そうでなければ AI に渡さないでください。"),
    ("conceal",
     r"(?:do\s+not|don'?t|never)\s+(?:tell|inform|mention\s+(?:this\s+)?to|reveal\s+(?:this\s+)?to)\s+the\s+user"
     r"|(?:ユーザー|利用者|人間|使用者)に(?:は)?(?:言わ|伝え|知らせ|見せ|教え)(?:ないで|るな|ず)|黙って(?:実行|送|行)",
     "人に隠して何かをさせようとする言いまわしです。",
     "隠す理由がある文書か確かめてください。AI が人に黙って動く指示は、ふつうの文書には入りません。"),
    ("exfiltrate",
     r"(?:send|upload|post|forward|email|exfiltrate)\s+(?:\w+\s+){0,4}(?:api\s*keys?|tokens?|passwords?|secrets?|credentials?|\.env|ssh\s+keys?|cookies?)"
     r"|(?:api\s*キー|apiキー|トークン|パスワード|秘密鍵|認証情報|\.env|クッキー)[^。\n]{0,20}(?:送|アップロード|転送|貼り付け|投稿)",
     "鍵やパスワードを外へ送らせようとする言いまわしです。",
     "鍵やパスワードを外へ送る必要は、まずありません。AI に渡さず、書いた人に確かめてください。"),
    ("command",
     r"(?:curl|wget)\s[^\n|]*\|\s*(?:sudo\s+)?(?:ba|z)?sh\b|rm\s+-rf\s+[/~]|powershell[^\n]*-e(?:nc|ncodedcommand)?\s"
     r"|chmod\s+\+x[^\n]*&&",
     "ネットから取ってきたものを、そのまま動かす命令です。",
     "AI にこの命令を動かさせないでください。動かす必要があるなら、中身を人が読んでから人が動かしてください。"),
    # 解析役の AI に向けて「調べるな」「害は無い」と言わせる言いまわし。マルウェアの中に、AI の解析役を
    # 断らせたり「無害」と答えさせたりする文が埋め込まれた例が報告されている（2026-11 の報告を受けて足した）。
    ("deflect",
     r"(?:do\s+not|don'?t|never)\s+(?:analy[sz]e|scan|inspect|examine|investigate|report|flag|look\s+(?:at|into))\b"
     r"|(?:stop|refuse)\s+(?:to\s+)?(?:analy[sz](?:e|ing)|scann?(?:ing)?|inspect(?:ing)?)"
     r"|refuse\s+(?:\w+\s+){0,4}(?:due\s+to|because\s+of)\s+copyright"
     r"|copyright(?:ed)?\b[^.\n]{0,40}\b(?:refuse|cannot\s+(?:be\s+)?analy[sz]|must\s+not\s+(?:be\s+)?analy[sz])"
     r"|(?:this|the)\s+(?:file|code|program|sample|script|binary|document|executable)\s+is\s+"
     r"(?:completely\s+|totally\s+|perfectly\s+)?(?:harmless|benign|clean|not\s+malicious|not\s+(?:a\s+)?malware|safe(?=\s*[.!]|\s*$))"
     r"|(?:respond|reply|answer|report|classify)\s+(?:\w+\s+){0,3}(?:with|as)\s+[\"']?(?:no\s+malware\s+detected|benign|safe|clean|harmless)"
     r"|no\s+malware\s+detected"
     r"|(?:解析|分析|調査|スキャン|検査)(?:を|は)?(?:断|拒否|拒ん|しないで|するな|せず|やめ|中止)"
     r"|(?:調べ|解析し|分析し|スキャンし|検査し)(?:ないで|るな)"
     r"|著作権[^。\n]{0,30}(?:断|拒否|拒ん|解析できません|解析しないで|お答えできません)"
     r"|(?:この|本|当)(?:ファイル|プログラム|コード|文書|ソフト|サンプル)(?:は|には)[^。\n]{0,10}"
     r"(?:無害|危険(?:では|じゃ)(?:ない|ありません)|悪意(?:は|が)?(?:ない|ありません)|マルウェアでは(?:ない|ありません)|安全(?:です|だ|。|$))",
     "AI の解析役に、調べるのをやめさせたり「無害」と答えさせたりする言いまわしです。",
     "文書が自分で「無害です」「調べないで」と言う理由は、ふつうありません。AI の答えをうのみにせず、人が中身を確かめてください。"),
]
_RULES = [(code, re.compile(pat, re.I), why, how) for code, pat, why, how in RULES]

_FIXED = {
    "invisible": ("目に見えない文字が入っています。人には読めず、AI にだけ届きます。",
                  "見えない文字を消してから渡すか、書いた人に理由を確かめてください。"),
    "hidden_html": ("HTML で見えなくした所があります。画面には出ず、AI にだけ届きます。",
                    "見えない所に何が書かれているか、ソースを開いて人が確かめてください。"),
    "comment": ("コメント（<!-- -->）があります。画面には出ず、AI にだけ届きます。",
                "コメントの中身を人が読んでください。指示らしい文があれば渡さないでください。"),
    "image_beacon": ("画像の住所に、続きの文字（?〜）が付いています。AI が画像を開くと、その文字が相手に届きます。",
                     "画像の住所に、秘密や会話の中身が入るような書き方がないか確かめてください。"),
    "outside_link": ("信用する住所の一覧にない住所へのリンクです。",
                     "AI にこのリンクを開かせる前に、人が住所を確かめてください。"),
    "encoded": ("長い暗号のような文字の並び（base64 など）があります。中身が読めません。",
                "中身を人が確かめるまで、AI に「解いて実行して」と言わせないでください。"),
}


def fingerprint(text: str) -> str:
    """文書の指紋（sha256）。人が確かめた文書の指紋を控えておけば、同じ文書かを照らし合わせられる（割符）。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _host(url: str) -> str:
    rest = url.split("://", 1)[-1]
    rest = re.split(r"[/?#\\]", rest, maxsplit=1)[0]
    rest = rest.rsplit("@", 1)[-1].split(":", 1)[0]
    return rest.lower().rstrip(".")


def _trusted(host: str, trusted: List[str]) -> bool:
    return any(host == t or host.endswith("." + t) for t in trusted)


def _line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def _quote(s: str) -> str:
    s = _INVISIBLE.sub(lambda m: "<U+%04X>" % ord(m.group()), s.strip())
    return s if len(s) <= 80 else s[:77] + "..."


def check(text: str, trusted_hosts: Optional[Iterable[str]] = None,
          approved: Optional[Iterable[str]] = None) -> dict:
    """文書を調べる。

    trusted_hosts: 信用する住所（例 ["github.com"]）。渡すと、それ以外へのリンクを黄（outside_link）にする。
    approved: 人が前に確かめた文書の指紋（fingerprint の値）。同じなら approved=True を返す（答えの色は変えない）。
    """
    findings: List[dict] = []

    def add(code, sev, pos, quote, why=None, how=None):
        w, h = (why, how) if why else _FIXED[code]
        findings.append({"code": code, "sev": sev, "line": _line_of(text, pos), "quote": _quote(quote),
                         "why": w, "how": h})

    for m in _INVISIBLE.finditer(text):
        if m.group() == "﻿" and m.start() == 0:
            continue  # 文書の先頭の BOM は、ふつうに付くもの
        add("invisible", "red", m.start(), text[max(0, m.start() - 10):m.end() + 10])

    # 隠した所（コメント・見えない HTML）の範囲。言いまわしがここにあれば赤。
    hidden = []
    for m in _COMMENT.finditer(text):
        hidden.append((m.start(), m.end()))
        add("comment", "amber", m.start(), m.group())
    for m in _HIDDEN_STYLE.finditer(text):
        close = text.find("</", m.end())
        end = close if close != -1 else min(len(text), m.end() + 400)
        hidden.append((m.start(), end))
        add("hidden_html", "red", m.start(), text[m.start():end])

    # 言いまわしは、見えない文字を抜いて、全角と半角をそろえてから読む（「無​視」のような分け書きを防ぐ）。
    # 抜いた文字の数だけ位置がずれるので、元の位置への対応表を持つ。
    kept = [i for i, ch in enumerate(text) if not _INVISIBLE.match(ch)]
    plain = "".join(unicodedata.normalize("NFKC", text[i]) if len(unicodedata.normalize("NFKC", text[i])) == 1
                    else text[i] for i in kept)
    for code, rx, why, how in _RULES:
        for m in rx.finditer(plain):
            pos = kept[m.start()]
            sev = "red" if any(a <= pos < b for a, b in hidden) else "amber"
            add(code, sev, pos, m.group(), why, how)

    for m in _IMAGE.finditer(text):
        if "?" in m.group(1) and not _trusted(_host(m.group(1)), list(trusted_hosts or [])):
            add("image_beacon", "amber", m.start(1), m.group(1))
    if trusted_hosts is not None:
        trusted = [t.lower().strip(".") for t in trusted_hosts if t.strip()]
        for m in _URL.finditer(text):
            if not _trusted(_host(m.group()), trusted):
                add("outside_link", "amber", m.start(), m.group())
    for m in _BASE64.finditer(text):
        add("encoded", "amber", m.start(), m.group())

    findings.sort(key=lambda f: (f["line"], f["code"]))
    level = "red" if any(f["sev"] == "red" for f in findings) else "amber" if findings else "none"
    head = {"red": "赤：隠れた指示か、隠した文字があります。AI に渡さないでください。",
            "amber": "黄：確かめてほしい所があります。人が読んでから渡してください。",
            "none": "見つかりませんでした（安全という意味ではありません）。"}[level]
    fp = fingerprint(text)
    return {"level": level, "head": head, "findings": findings, "sha256": fp,
            "approved": fp in set(approved or [])}


def _main(argv: Optional[List[str]] = None) -> int:
    import argparse
    import json
    import sys

    p = argparse.ArgumentParser(prog="python -m kango.sekisho",
                                description="AI に渡す前の文書を、決まった規則だけで調べます。"
                                            "AI を使わず、文書を保存せず、リンク先へもアクセスしません。")
    p.add_argument("file", nargs="?", help="調べる文書（省くと標準入力から読みます）")
    p.add_argument("--trusted", default=None, metavar="HOST,HOST",
                   help="信用する住所をカンマ区切りで（例：github.com）。それ以外へのリンクを黄にします")
    p.add_argument("--approved", default=None, metavar="FILE",
                   help="人が確かめた文書の指紋（sha256）を1行に1つ書いたファイル")
    p.add_argument("--json", action="store_true", help="答えを JSON で出す")
    p.add_argument("--findings", action="store_true",
                   help="答えを akaire-findings/v1 の形の JSON で出す（アカイレなどの表示に渡せます）")
    a = p.parse_args(argv)

    if a.file:
        with open(a.file, encoding="utf-8", errors="replace") as f:
            text = f.read()
    else:
        text = sys.stdin.read()
    trusted = None if a.trusted is None else [s.strip() for s in a.trusted.split(",") if s.strip()]
    approved = None
    if a.approved:
        with open(a.approved, encoding="utf-8") as f:
            approved = [s.split()[0] for s in f if s.strip() and not s.startswith("#")]
    r = check(text, trusted_hosts=trusted, approved=approved)

    if a.findings:
        src = a.file or "stdin"
        sev = {"red": "red", "amber": "orange"}
        out = {"schema": "akaire-findings/v1", "tool": "kango-sekisho", "sources": [src],
               "disclaimer": "決まった規則で見つけた候補です。何も見つからなくても安全とは限りません。最後は人が確かめてください。",
               "findings": [{"tool": "kango-sekisho", "src": "%s L%d" % (src, f["line"]),
                             "loc": {"line": f["line"], "quote": f["quote"]}, "sev": sev[f["sev"]],
                             "label": f["code"], "why": f["why"], "how": f["how"], "source": ""}
                            for f in r["findings"]]}
        print(json.dumps(out, ensure_ascii=False, indent=2))
    elif a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(r["head"])
        if r["approved"]:
            print("・人が前に確かめた文書と同じです（指紋が一致）。")
        for f in r["findings"]:
            print("・%d行目 %s（%s）%s" % (f["line"], "赤" if f["sev"] == "red" else "黄", f["code"], f["why"]))
            print("    「%s」" % f["quote"])
            print("    → %s" % f["how"])
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
