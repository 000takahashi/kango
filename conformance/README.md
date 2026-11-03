# 共通の見本（cases.json）

勘合の答えを、言語によらず同じに保つための見本です。[cases.json](cases.json) には、文面と、勘合が返すべき答え（色・理由のコード・名乗った会社・リンク先）を書いています。

- **Python と Swift のテストは、どちらもこのファイルを読み込み、すべての見本で同じ答えになることを確かめています**（`python/tests/test_judge.py`・`swift/Tests/KangoTests/ConformanceTests.swift`）。片方だけ答えが変わると、CI が落ちます。
- **勘合を別の言語（JavaScript・Kotlin・Go など）に移す時は、この見本をすべて通してください。** 規則は [SPEC.md](../SPEC.md)、会社の一覧は [data/brands.csv](../data/brands.csv) です。

## 形

```json
{
  "ledger": ["amazon", "rakuten", "docomo", "yucho"],
  "cases": [
    {"note": "似せた住所：数字で似せる（e を 3 に）。会社を名乗らなくても赤",
     "text": "お荷物のお届けについて https://rakut3n-pay.com/",
     "level": "red", "codes": ["no_claim", "mimic"], "claimed": [], "hosts": ["rakut3n-pay.com"]}
  ]
}
```

| 項目 | 意味 |
|---|---|
| `ledger`（いちばん上） | 見本に台帳が書かれていない時に使う台帳 |
| `note` | 何を確かめる見本か |
| `text` | 文面 |
| `ledger`（見本の中・省略可） | この見本だけで使う台帳 |
| `level` | 色（`green`・`amber`・`red`） |
| `codes` | 理由のコード。**並び順も含めて**一致すること（並び順は SPEC.md の「並び順」） |
| `claimed` | 名乗った会社の `id`（`data/brands.csv` の行の順） |
| `hosts` | リンク先（ブラウザが実際に開く住所）。並び順も含めて一致すること |

理由の文言（`reasons` の `text`）は比べません。製品や言語ごとに、言い回しを変えられるようにするためです。

ラテン文字と見分けのつかない文字（キリル文字の `а` など）は、ファイルの中でも分かるように `а` の形で書いています。

## 見本を足す時

- **答えは、SPEC.md から先に考えて書きます。** 今の勘合の答えを写すのではありません。考えた答えと勘合の答えが食い違ったら、どちらが正しいかを確かめます。今の答えは `python -m kango --json --ledger amazon,rakuten,docomo,yucho` に文面を渡すと見られます。
- **「こうなるべき」見本と、「本物の連絡が誤って黄・赤にならない」見本の両方を足します。**
- 実在の人の名前・住所・電話番号は入れません。番号は `0120-123-456` のような明らかな例に、攻撃する側の住所は `example`（`evil.example` など、例のために取っておかれた住所）にします。
- 会社を足した時は、その会社の本物の住所が青になる見本を1件足します（台帳はその会社だけ）。

## 行の印の見本（marks.json）

[marks.json](marks.json) は、行の印（SPEC.md の「行に印を付ける」）の見本です。見本ごとに `lines`（行に分けた文面）と、返すべき `marks`（印のある行の `line`・`level`・`codes`）を書いています。`ledger` の扱いは cases.json と同じです。`labels` の言い回しは比べません。Python は `python/tests/test_marks.py`、Swift は `swift/Tests/KangoTests/MarksTests.swift` が、すべての見本を動かします。

---

## English

[cases.json](cases.json) holds language-neutral test vectors: each case is a message (`text`) with the expected `level`, reason `codes` (in order), `claimed` brand ids, and `hosts` (the real destinations, in order). An optional per-case `ledger` overrides the top-level one. Reason texts are not compared, so ports may localize them. Both the Python and Swift test suites run every case; a port to another language should pass all of them. The rules are in [SPEC.md](../SPEC.md) and the brand list in [data/brands.csv](../data/brands.csv).
