# 勘合（kango）

届いたメール・SMS・LINE の文面を、**「自分がどの会社と契約しているか（契約台帳）」**と**「会社ごとの公式ドメイン」**の2つの割符で照合し、青・黄・赤で返すフィッシング判定の部品です。

迷惑メールフィルターは「文面」や「送信元」で見ます。勘合は「**あなたとの契約**」で見ます。AI が自然な日本語で書いた詐欺文でも、割符が合わなければ赤になります。

```
【三菱UFJ銀行】口座が凍結されています https://www.bk.mufg.jp/
  → 赤：「三菱UFJ銀行」を名乗っていますが、あなたの割符（契約している会社）にありません。

【Amazon】お支払い情報を更新 https://amazon-co-jp.account-verify.top/
  → 赤：リンク先は「Amazon」に似せた住所ですが、公式の住所ではありません。

【楽天カード】ご請求額が確定しました https://www.rakuten-card.co.jp/e-navi/
  → 青：割符が合いました（「本物です」とは言いません）
```

## 守る線

- **AI を使いません。** 決まった規則での照合だけです。同じ入力には必ず同じ答えを返します。
- **断定しません。** 青は「割符が合いました」まで。「本物です」「安全です」とは言いません。
- **文面を保存せず、外へ送りません。** 端末の中だけで判定できます。
- **リンク先へアクセスしません。** 相手のサーバーには一切触れず、文字列だけを照合します。

## 使い方

### Python

```python
from kango import judge

r = judge("【楽天カード】ご請求額が確定しました https://www.rakuten-card.co.jp/", ledger=["rakuten"])
r["level"]    # "green" / "amber" / "red"
r["reasons"]  # [{"code": "in_ledger", "text": "..."}, ...]
```

### Swift（iOS 17 / macOS 13 以降）

Swift Package Manager で `swift/` を追加し、

```swift
import Kango

let v = Judge.judge(text: message, ledger: ["rakuten", "docomo"])
v.level   // .green / .amber / .red
```

### AI エージェントに組み込む

利用者の代わりにメールを読んだりリンクを開いたりする AI ほど、フィッシングに騙される危険があります。リンクを開く前・入力する前に `judge` を通し、赤ならその操作を止めて人に確かめてください。

## 判定の規則

[SPEC.md](SPEC.md) にすべて書いてあります。理由のコード（`not_in_ledger`・`mimic` など）も一覧にしています。

## 会社の一覧

[data/brands.csv](data/brands.csv) が正です。`checked` 列は、その会社の公式ページで住所を確かめた日付です。**空欄の会社は、まだ公式の一覧で確かめられていません。** 追加・修正の手順は [CONTRIBUTING.md](CONTRIBUTING.md) をご覧ください。

## 注意

この部品は判断の手がかりを示すものです。結果を保証するものではありません。少しでも不安な時は、リンクではなく公式アプリやいつものブックマークから開いて確かめ、警察相談専用電話（#9110）や消費者ホットライン（188）にご相談ください。

## 公式の配布元

勘合の公式の配布元は、このリポジトリ（github.com/000takahashi/kango）だけです。「勘合で安全と判定済み」などとうたう別のアプリやサイトは、提供元と関係がありません。

## ライセンス

Apache License 2.0（[LICENSE](LICENSE)）。

提供：株式会社MAMORUNE

---

## English (summary)

**kango** is a deterministic phishing check for Japanese messages. It verifies two "tallies": whether the brand a message claims is in *your own contract ledger*, and whether every link sits on that brand's *official domain* (with lookalike detection). No AI, no network access, no storage. Green means "the tallies match", never "this is genuine". Python and Swift implementations share the same rules ([SPEC.md](SPEC.md)) and test cases. Licensed under Apache-2.0.
