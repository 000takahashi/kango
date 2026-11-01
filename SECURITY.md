# セキュリティの問題を見つけた時

勘合は、偽物の連絡を見分けるための部品です。**偽物の連絡が青（割符が合いました）になってしまう抜け道**は、悪用されると、利用者が偽サイトに入力してしまう危険につながります。見つけた時は**公開の Issue には書かず**、次の方法で、非公開でお知らせください。

## 知らせ方

1. このリポジトリの「**Security**」タブを開き、「**Report a vulnerability**」から送ってください。GitHub の非公開の報告の仕組みで、報告した人と管理者だけが読めます。
2. 「Report a vulnerability」が見当たらない時は、公開の Issue に「セキュリティについて非公開で連絡したい」とだけ書いてください（中身は書かないでください）。非公開の連絡方法をお伝えします。

## セキュリティの問題として扱うもの

- 偽物の連絡が、青になる（リンクの書き方の工夫で、勘合が照らし合わせる住所と、ブラウザが実際に開く住所がずれる、など）
- 会社の一覧（`data/brands.csv`）に、その会社のものではない住所が入っている
- 勘合を使うと、文面や台帳が外へ送られたり、保存されたりする
- 勘合の配布物（Python の部品・Swift の部品）が改ざんされている疑い

## 公開の Issue でよいもの

- 本物の連絡が、黄や赤になる（誤った黄・赤）
- 偽物の連絡が、赤ではなく黄になる（黄も「確かめきれません」と注意を促すため）
- 会社の追加・修正の希望、説明のまちがい

## 知らせる時のお願い

- 文面に入っている、実在の人の名前・電話番号・住所・カード番号などは、消してから送ってください。
- 偽サイトの住所は、そのまま書いてください（照らし合わせに必要です）。ご自身では開かないでください。
- 勘合のどの版で起きたか（例：v0.2.0）を書いてください。

## こちらからのお返事

- 提供元は小さな会社のため、お返事までの日数はお約束できませんが、できるだけ早く確かめます。
- 直したら新しい版を出し、[変更の記録](CHANGELOG.md) とリリースの説明でお知らせします。ご希望があれば、見つけた方のお名前を載せます。
- 報奨金の制度はありません。

## 直す版

いちばん新しい版だけを直します。古い版を使っている時は、新しい版に上げてください。

## 勘合の外のこと

- 勘合を組み込んだアプリやサービスの問題は、そのアプリやサービスの提供元へお知らせください。
- 詐欺の被害にあった・あいそうな時は、警察相談専用電話（#9110）や消費者ホットライン（188）、カード会社・銀行へご相談ください。

---

## English

Please do not report security issues in public issues. Use **Security → Report a vulnerability** (GitHub private vulnerability reporting). If that button is not available, open a public issue that only says you would like to report a security issue privately, without any details.

Security issues include: a phishing message judged green; a domain in `data/brands.csv` that does not belong to that company; message text or the ledger leaving the device or being stored; tampered distributions. False amber or red verdicts can be reported publicly. Please remove personal information from samples, keep attacker domains as they are, and do not open them. Only the latest version receives fixes. There is no bug bounty.
