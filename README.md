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

```sh
pip install "git+https://github.com/mamorune-com/kango@v0.2.0#subdirectory=python"
```

PyPI にある `kango` は、この部品とは関係のない別のものです。`pip install kango` では入りません。

```python
from kango import judge

r = judge("【楽天カード】ご請求額が確定しました https://www.rakuten-card.co.jp/", ledger=["rakuten"])
r["level"]    # "green" / "amber" / "red"
r["reasons"]  # [{"code": "in_ledger", "text": "..."}, ...]
```

### Swift（iOS 17 / macOS 13 以降）

Xcode の「File → Add Package Dependencies…」で `https://github.com/mamorune-com/kango` を入れるか、`Package.swift` の dependencies に次の1行を足します。

```swift
.package(url: "https://github.com/mamorune-com/kango", from: "0.1.0")
```

使う側では、

```swift
import Kango

let v = Judge.judge(text: message, ledger: ["rakuten", "docomo"])
v.level   // .green / .amber / .red
```

### AI エージェントに組み込む

利用者の代わりにメールを読んだりリンクを開いたりする AI ほど、フィッシングに騙される危険があります。リンクを開く前・入力する前に `judge` を通し、赤ならその操作を止めて人に確かめてください。

## 判定の規則

[SPEC.md](SPEC.md) にすべて書いてあります。理由のコード（`not_in_ledger`・`mimic` など）も一覧にしています。

## 考え方の出どころ

勘合は新しい発明ではありません。パスワード管理アプリは、登録したサイトの本物の住所でだけパスワードを自動入力します。パスキー（FIDO2 / WebAuthn）も、登録したドメインでしか使えません。どちらも「本物の住所と照らし合わせる」という、すでに実績のある原理です。勘合は、この原理を、届いたメール・SMS・LINE の文面に当てはめたものです。

赤と青を分けるのは文章のうまさではなく、攻撃する側が偽れないもの（あなたの契約台帳と、相手が持っていない公式ドメイン）です。そのため、AI で文章をどれだけ自然にしても、それだけで赤が青に変わることはありません。

## なぜ広まっていないのか（私たちの見立て）

- **契約台帳が要ります。** 「この人はどの会社と契約しているか」を事業者が集めると、それ自体が大きなプライバシーの問題になります。勘合は台帳を利用者の端末の中だけに置き、外へ送りません。
- **お金になりにくい仕組みです。** 広告や手数料を生みにくく、事業として取り組む理由が小さいものです。
- **これまでの対策は「危ない住所の一覧（ブロックリスト）」が中心でした。** 一覧はとても大切ですが、作られたばかりの偽サイトには追いつけません。勘合は「本物の住所の一覧」と照らし合わせるので、会社を名乗った連絡なら、作られたばかりの偽サイトでも「公式の住所ではない」と分かります。ブロックリストに代わるものではなく、組み合わせて使うものです。

## できないこと

勘合が見ているのは、文面の中の会社名・リンクの住所・急かす言葉だけです。次のことはできません。

- **黄（確かめきれない）は、よく出ます。** 短縮 URL（行き先が見えない）、どの会社を名乗っているか読み取れない連絡、照らし合わせられるものが無い連絡（配送・郵便・国税庁を名乗っていて、リンクが無いもの）は、それだけでは青にも赤にもできず、黄になります。
- **一覧にない会社は見分けられません（黄になります）。** 会社の一覧はまだ 18 社で、そのうち 5 社は公式の住所を確かめきれていません（`checked` 列が空欄）。
- **台帳の登録漏れは、誤った赤になります。** 契約しているのに台帳に入れていない会社からの本物の連絡は、赤になります。
- **電話番号は照合できません。** 番号が本物かは確かめられないので、電話番号が書かれている連絡は、名乗った会社が台帳にあっても黄にします（青にはしません）。
- **本物の住所が悪用された場合は、すり抜けます。** 会社のアカウントやサイトそのものが乗っ取られた場合や、公式の住所の中にある転送の仕組み（オープンリダイレクト）を使われた場合は、青になりえます。
- **会社を名乗らない詐欺は、黄までです。** SNS 型投資詐欺やロマンス詐欺のように、会社を名乗らない連絡は赤にできません。
- **受け取るのは文字だけです。** 画像の中の文字や QR コードは、呼び出す側で文字にしてから渡してください。電話の音声や、端末に入り込むウイルスは扱えません。

## 会社の一覧

[data/brands.csv](data/brands.csv) が正です。`checked` 列は、その会社の公式ページで住所を確かめた日付です。**空欄の会社は、まだ公式の一覧で確かめられていません。** 追加・修正の手順は [CONTRIBUTING.md](CONTRIBUTING.md) をご覧ください。

## 注意

この部品は判断の手がかりを示すものです。結果を保証するものではありません。少しでも不安な時は、リンクではなく公式アプリやいつものブックマークから開いて確かめ、警察相談専用電話（#9110）や消費者ホットライン（188）にご相談ください。

## 公式の配布元

勘合の公式の配布元は、このリポジトリ（github.com/mamorune-com/kango）だけです。「勘合で安全と判定済み」などとうたう別のアプリやサイトは、提供元と関係がありません。

## ライセンス

Apache License 2.0（[LICENSE](LICENSE)）。

提供：株式会社MAMORUNE

---

## English (summary)

**kango** is a deterministic phishing check for Japanese messages. It verifies two "tallies": whether the brand a message claims is in *your own contract ledger*, and whether every link sits on that brand's *official domain* (with lookalike detection). No AI, no network access, no storage. Green means "the tallies match", never "this is genuine". Python and Swift implementations share the same rules ([SPEC.md](SPEC.md)) and test cases. Licensed under Apache-2.0.

**Not a new idea.** kango applies the principle behind password-manager autofill (only on the registered domain) and passkeys / WebAuthn (credentials bound to the domain) to incoming messages. Red and green are decided by things an attacker cannot fake (your own ledger, and domains they do not own), not by how convincing the text is, so making the text more natural with AI does not, by itself, turn red into green.

**Why isn't this common? (our view)** It needs a per-user contract ledger, which is a privacy problem for any provider to collect; kango keeps it on the device. It earns little. And the industry has mostly invested in blocklists, which lag behind newly created phishing sites. kango complements blocklists rather than replacing them.

**Limits.** Amber is common by design. A message with nothing to check (for example, one that names a delivery company or the tax agency but has no link) is amber, never green. Brands missing from the list (18 so far, 5 not yet verified) are not covered, and a company you use but did not add to your ledger shows red. Phone numbers cannot be verified, so a message that contains one is never green, even if the claimed brand is in your ledger. A genuinely compromised official account or site, or an open redirect on an official domain, can pass as green. Scams that claim no brand (investment, romance) stay amber. Input is text only.
