# kango（Python）

勘合の判定を Python から使うための部品です。判定の規則と会社一覧は、リポジトリの [README](https://github.com/mamorune-com/kango) と [SPEC.md](https://github.com/mamorune-com/kango/blob/main/SPEC.md) をご覧ください。

```sh
pip install "git+https://github.com/mamorune-com/kango@v0.1.0#subdirectory=python"
```

```python
from kango import judge

r = judge("【楽天カード】ご請求額が確定しました https://www.rakuten-card.co.jp/", ledger=["rakuten"])
r["level"]  # "green" / "amber" / "red"
```

PyPI にある `kango` は、この部品とは関係のない別のものです。`pip install kango` では入りません。
