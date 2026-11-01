# 勘合の参考書

勘合（kango）を使う人・組み込む人・育てる人のための説明書です。判定の規則そのものは [SPEC.md](../SPEC.md) が正で、ここにはその背景と使い方を書いています。

| 知りたいこと | ページ |
|---|---|
| なぜこの作りなのか（2つの割符・AI を使わない理由・断定しない理由） | [設計の考え方](design.md) |
| どの手口に、どう答えるのか。どこから先は守れないのか | [守れる範囲](threat-model.md) |
| アプリ・サーバー・LINE ボット・AI エージェントに組み込むには | [組み込み方](integration.md) |
| 会社や規則を足す・直すには | [会社と規則の足し方](extending.md) |
| 別の言語に移すには・答えを確かめる見本 | [共通の見本](../conformance/README.md) |
| 会社のアプリやサービスで使うには（ライセンス） | [商用で使う](commercial-use.md) |
| 言葉の意味 | [用語集](glossary.md) |

## この説明書の約束

- **書いてある判定は、本物の実行結果です。** [守れる範囲](threat-model.md) の表と [共通の見本](../conformance/README.md) は、Python と Swift のテストが毎回読み込み、勘合を動かして確かめています。[組み込み方](integration.md) の Python の例も、CI が毎回動かしています。
- **できないことも書きます。** 守れない範囲を知らずに使うのが、いちばん危ないからです。
- **SPEC.md と食い違ったら、SPEC.md が正しいです。** 説明の誤りに気づいたら、Issue でお知らせください。

---

These pages are written in Japanese. The rules live in [SPEC.md](../SPEC.md). The verdict table in [threat-model.md](threat-model.md) and the language-neutral test vectors in [conformance/cases.json](../conformance/cases.json) are executed by both test suites (Python and Swift) on every CI run, and the Python examples in [examples/python/](../examples/python/) are run by CI as well.
