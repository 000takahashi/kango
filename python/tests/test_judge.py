"""勘合の判定のテスト（swift/Tests/KangoTests/JudgeTests.swift と同じ見本で同じ判定になること）。"""
import kango as tr

LEDGER = ["amazon", "rakuten", "docomo", "yucho"]


def _codes(r):
    return [x["code"] for x in r["reasons"]]


def test_fake_amazon_lookalike_is_red():
    r = tr.judge("【Amazon】24時間以内にお支払い情報を更新しないと停止 https://amazon-co-jp.account-verify.top/login", LEDGER)
    assert r["level"] == "red" and "mimic" in _codes(r) and "pressure" in _codes(r)


def test_digit_lookalike_is_red():
    r = tr.judge("お荷物のお届けについて https://rakut3n-pay.com/", LEDGER)
    assert r["level"] == "red" and "mimic" in _codes(r)


def test_delivery_without_name_but_mimic_host_is_red():
    r = tr.judge("お荷物を持ち帰りました。 http://kuroneko-yamato.delivery-jp.xyz/track", LEDGER)
    assert r["level"] == "red"


def test_brand_not_in_ledger_is_red():
    r = tr.judge("【三菱UFJ銀行】口座が凍結されています https://www.bk.mufg.jp/", LEDGER)
    assert r["level"] == "red" and "not_in_ledger" in _codes(r)


def test_official_and_in_ledger_is_green_without_asserting_genuine():
    r = tr.judge("【楽天カード】ご請求額が確定しました https://www.rakuten-card.co.jp/e-navi/", LEDGER)
    assert r["level"] == "green" and r["helplines"] == []
    words = r["head"] + r["todo"] + "".join(x["text"] for x in r["reasons"])
    assert "本物" not in words and "安全" not in words


def test_shortener_and_idn():
    assert tr.judge("Amazon https://bit.ly/abc", LEDGER)["level"] == "amber"
    assert tr.judge("Amazon https://xn--amazn-mua.com/", LEDGER)["level"] == "red"


def test_official_subsidiary_domains_are_not_red():
    # 各社の公式ページで確かめた住所（2026-10-31）＝ここが赤になると本物の連絡を偽物と言ってしまう
    ledger = [b["id"] for b in tr.BRANDS]
    for name, host in [("三井住友カード", "contact.vpass.ne.jp"), ("楽天カード", "support.rakuten-card.jp"),
                       ("PayPay", "paypay.co.jp"), ("JCB", "www.global.jcb"), ("ドコモ", "www.nttdocomo.co.jp"),
                       ("au ID", "id.auone.jp"), ("ワイモバイル", "www.ymobile.jp"), ("メルペイ", "jp.merpay.com")]:
        r = tr.judge(f"【{name}】ご確認 https://{host}/", ledger)
        assert r["level"] == "green", (name, host, r["reasons"])
