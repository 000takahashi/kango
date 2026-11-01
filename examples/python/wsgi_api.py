"""勘合を HTTP の窓口（API）にする最小の例。Python の標準ライブラリだけで動く（docs/integration.md）。

  POST /  {"text": "届いた文面", "ledger": ["rakuten", ...]}
  → 200   {"level", "head", "reasons", "todo", "helplines"}

- 届いた文面と台帳は保存しない・ログに出さない（この例は受け取った中身をどこにも書かない）。
- 本番では、この前に TLS（https）・回数の上限・必要なら本人確認を置く。

動かして確かめる：python examples/python/wsgi_api.py          （通信せずに自分で確かめる）
手元で開く　　　：python examples/python/wsgi_api.py --serve  （http://127.0.0.1:8000/）
"""
import json
import sys

from kango import judge

MAX_TEXT = 4000      # 文面の長さの上限（文字）
MAX_LEDGER = 100     # 台帳の会社の数の上限
MAX_BODY = 64 * 1024  # 受け取る大きさの上限（バイト）


def app(environ, start_response):
    def reply(status, body):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        start_response(status, [("Content-Type", "application/json; charset=utf-8"),
                                ("Content-Length", str(len(data))), ("Cache-Control", "no-store")])
        return [data]

    if environ.get("REQUEST_METHOD") != "POST":
        return reply("405 Method Not Allowed", {"error": "post_only"})
    try:
        size = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        return reply("400 Bad Request", {"error": "invalid_length"})
    if size <= 0 or size > MAX_BODY:
        return reply("413 Payload Too Large", {"error": "too_large"})
    try:
        req = json.loads(environ["wsgi.input"].read(size).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return reply("400 Bad Request", {"error": "invalid_json"})
    text = req.get("text") if isinstance(req, dict) else None
    ledger = req.get("ledger", []) if isinstance(req, dict) else None
    if not isinstance(text, str) or not 0 < len(text) <= MAX_TEXT:
        return reply("400 Bad Request", {"error": "invalid_text"})
    if not isinstance(ledger, list) or len(ledger) > MAX_LEDGER or not all(isinstance(x, str) for x in ledger):
        return reply("400 Bad Request", {"error": "invalid_ledger"})
    v = judge(text, ledger)
    return reply("200 OK", {k: v[k] for k in ("level", "head", "reasons", "todo", "helplines")})


def _call(body: bytes):
    """通信せずに app を呼ぶ（自分で確かめる用）"""
    import io
    got = {}
    out = b"".join(app({"REQUEST_METHOD": "POST", "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)},
                       lambda status, headers: got.update(status=status)))
    return got["status"], json.loads(out)


if __name__ == "__main__":
    if "--serve" in sys.argv:
        from wsgiref.simple_server import make_server
        print("http://127.0.0.1:8000/ で待っています（Ctrl+C で止まります）")
        make_server("127.0.0.1", 8000, app).serve_forever()
    ok = json.dumps({"text": "【楽天カード】ご請求額が確定しました https://www.rakuten-card.co.jp/", "ledger": ["rakuten"]})
    status, body = _call(ok.encode("utf-8"))
    assert status.startswith("200") and body["level"] == "green", (status, body)
    assert _call(b'{"text": ""}')[0].startswith("400")
    assert _call(b"not json")[0].startswith("400")
    assert _call(b'{"text": "x", "ledger": "rakuten"}')[0].startswith("400")
    print("ok")
