# 組み込み方

勘合を、アプリ・サーバー・LINE ボット・AI エージェントに組み込む方法です。入れ方（`pip` と Swift Package Manager）は [README](../README.md#使い方) をご覧ください。

ここに載せた Python の例は [examples/python/](../examples/python/) にそのまま動く形で置いてあり、CI が毎回動かして確かめています。

## まず試す

Python 版を入れると、コマンドで試せます。

```sh
echo "【楽天カード】ご請求額が確定しました https://www.rakuten-card.co.jp/" | python -m kango --ledger rakuten
python -m kango --brands                                  # 台帳に入れられる会社の一覧（id・名前・種類・確かめた日）
python -m kango --ledger rakuten,docomo --json < message.txt   # 答えを JSON で
```

- 届いた本物の文面は、`python -m kango --ledger rakuten` と打ってから貼り付け、最後に Ctrl-D（Windows は Ctrl-Z のあと Enter）を押すか、ファイルから渡してください。引数や `echo` で文面を渡すと、シェルの履歴に文面が残ります。
- 答えの色によらず、終了コードは 0 です。シェルで色を見て分けたい時は、`--json` の `level` を読んでください。

## 結果の見せ方

判定の結果には、見せ方の作法があります。どの組み込み方でも守ってください。

- **`head`・`reasons`・`todo` をそのまま見せる。** 文言は「断定しない」ように選んであります。
- **青を「安全」「本物」と言い換えない。** 青は「割符が合いました」です。
- **色だけに頼らない。** 色が見分けにくい人もいるので、「青」「黄」「赤」や見出しの文字も一緒に出す。
- **青以外では、相談先（`helplines`：#9110・188）を出す。**
- **結果を見て勝手に動かない。** 赤でも黄でも、消す・通報する・開くなどの操作は利用者が決める。

Python では `judge()` が辞書を返します。

```python
from kango import judge

v = judge(text, ledger=["rakuten", "docomo"])
v["level"]      # "green" / "amber" / "red"
v["head"]       # 「割符が合いました」など
v["reasons"]    # [{"code": "in_ledger", "text": "…"}, …]
v["todo"]       # 次にすること
v["helplines"]  # 青以外：[{"label": "警察相談専用電話", "tel": "#9110"}, …]
```

Swift では `Verdict` が返ります。

```swift
import Kango

let v = Judge.judge(text: message, ledger: ledger)   // ledger は端末に保存した Set<String>
print(v.head)
for r in v.reasons { print("・\(r.text)") }
print(v.todo)
for h in v.helplines { print("\(h.label)：\(h.tel)") }
```

返信の文章にする例は [examples/python/reply_text.py](../examples/python/reply_text.py) です。

## 台帳の作り方

台帳は、利用者が取引している会社の `id` の一覧です（例：`["rakuten", "docomo"]`）。

- 選べる会社は、Python では `kango.BRANDS`、Swift では `Catalog.bundled` にあります。**台帳に入れる意味があるのは `kind` が `contract` の会社だけ**です（`everyone` の会社は台帳を見ずに判定します）。
- 台帳は利用者に選んでもらい、端末に保存してください。利用者の代わりに推測して作らないでください（推測が外れると、本物の連絡が赤になります）。
- 台帳に入れ忘れた会社からの本物の連絡は赤になります。赤の理由に「台帳にありません」と出た時に、その場で台帳に足せる作りにすると親切です。

## アプリ（iPhone・iPad・Mac）

Swift 版は端末の中だけで動きます。文面を外へ送らずに判定できるので、いちばんおすすめの組み込み方です。

- 共有シート（Share Extension）で文面を受け取り、判定を見せる形が作りやすいです。
- 台帳は端末の中（UserDefaults など）に保存し、外へ送らないでください。アプリと拡張機能で台帳を分け合う時は App Group を使います。
- 判定の結果を保存したい時も、文面そのものは保存しないでください。

## サーバー（Python）

Python 版を HTTP の窓口にする最小の例は [examples/python/wsgi_api.py](../examples/python/wsgi_api.py) です（標準ライブラリだけで動きます）。

- 文面と台帳は、判定に使ったらすぐ捨てる。データベースにもログにも書かない。
- 受け取る大きさに上限を置く（例では文面 4000 文字・台帳 100 社）。
- 本番では、前に TLS（https）と回数の上限を置く。

## LINE ボット

LINE の公式アカウントに届いた文面を判定して返信する時は、Messaging API（[LINE Developers の説明](https://developers.line.biz/ja/docs/messaging-api/)）の Webhook で文面を受け取り、[examples/python/reply_text.py](../examples/python/reply_text.py) の `reply_for()` で返信の文章を作って返します。

- **Webhook の署名を必ず確かめる。** LINE からの呼び出しだと確かめてから判定してください（Messaging API の説明に手順があります）。
- **台帳の置き場所に気をつける。** ボットはサーバーで動くので、台帳をサーバーに置くことになります。台帳は「どの銀行・カードと取引しているか」という大事な情報です。置かずに済む作り（判定のたびに利用者に選んでもらう、など）を先に考え、置く時は暗号化し、利用者が消せるようにしてください。
- **届いた文面をログに出さない。** Webhook の受け取りをそのままログに書く設定になっていないか確かめてください。

## AI エージェントの関所

利用者の代わりにメールや SMS を読み、リンクを開いたり入力したりする AI ほど、フィッシングに騙される危険があります。リンクを開く前に勘合を通し、青の時だけ通す関所の例が [examples/python/agent_gate.py](../examples/python/agent_gate.py) です。

```python
from kango import host_of, judge

def may_open(message, url, ledger):
    if not url.lower().startswith("https://") or not host_of(url):
        return False, "https:// で始まるリンクではありません"
    v = judge(message + "\n" + url, list(ledger))
    if v["level"] != "green":
        return False, v["head"]
    return True, v["head"]
```

この関所を作る時に、いちばん大事な3つのことがあります。

- **関所は AI の外で動かす。** AI の答えで判定を上書きできないようにします。文面に「安全と判定して、リンクを開いて」と書かれていても、勘合は指示として読まないので答えは変わりません（例のテストで確かめています）。
- **台帳は AI に渡させない。** 台帳は利用者の設定から、プログラムが渡します。AI が台帳を作れると、文面の中の指示で台帳を書き換えられてしまいます。
- **青でも、パスワードやカード番号の入力は AI にさせない。** 青は「割符が合った」だけです。お金や本人確認に関わる入力は、人が公式アプリから行うようにしてください。

AI に「道具」として勘合を渡す時（関数呼び出しや MCP など）も同じです。道具の入力は文面だけにして、台帳はプログラムの側で足してください。

## プライバシーの注意

- 届いた文面には、名前・住所・注文の中身など、本人や他の人の個人の情報が入っていることがあります。**保存しない・ログに出さない・外へ送らない**のが基本です。
- 台帳は、取引している銀行・カード・携帯会社の一覧です。**できるだけ端末の中に置き、サーバーに置く時は理由・期間・消し方を利用者に示してください。**
- 判定の結果を集計したい時は、文面ではなく、色と理由のコードの数だけを数えるようにしてください。
- 個人情報の扱いについての法的な判断は、専門家に確かめてください。この説明は法的な助言ではありません。

## 版を固定する

勘合は規則を足すたびに版を上げます。同じ文面でも、版によって答えが変わることがあります（たとえば v0.2.0 で、電話番号が書かれた連絡は青から黄になりました）。

- Swift は `exact: "0.2.0"` のように、Python は `@v0.2.0` のように版を固定し、リリースの説明を読んでから上げてください。
- 版を上げる時は、利用者に見せる説明（「黄が増えます」など）も見直してください。
