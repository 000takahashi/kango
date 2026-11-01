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


def test_phone_number_is_amber_even_for_ledger_brand():
    # 番号が本物かは確かめられない＝台帳にある会社を名乗っていても青にしない
    for text in ["【楽天カード】ご利用確認のため、0120-123-456 までお電話ください",
                 "【楽天カード】お問い合わせは０１２０－１２３－４５６へ",
                 "【楽天カード】(03) 1234-5678 までお電話ください",
                 "【楽天カード】海外からは +81-3-1234-5678 へ",
                 "【ヤマト運輸】お荷物のお届けについて、090-1234-5678 までご連絡ください"]:
        r = tr.judge(text, LEDGER)
        assert r["level"] == "amber" and "phone" in _codes(r), (text, r["reasons"])


def test_numbers_that_are_not_phone_numbers():
    # 日付・郵便番号・時刻・金額・注文番号・リンクの中の数字は、電話番号として数えない
    for text in ["【楽天カード】ご請求額が確定しました（2026-11-01）〒060-0001 受付 9:00-18:00 ¥10,000 https://www.rakuten-card.co.jp/",
                 "【楽天カード】ご確認 https://www.rakuten-card.co.jp/e-navi/?id=0312345678",
                 "【楽天カード】注文番号 012345678901234 https://www.rakuten-card.co.jp/",
                 "【Amazon】ご注文 250-1234567-1234567 https://www.amazon.co.jp/"]:
        r = tr.judge(text, LEDGER)
        assert r["level"] == "green" and "phone" not in _codes(r), (text, r["reasons"])


def test_nothing_to_check_is_amber():
    # 配送・郵便・国税庁（誰にでも届く会社）はリンクの住所でしか確かめられない＝リンクが無ければ何も照合していない＝青にしない
    for text in ["【ヤマト運輸】お荷物のお届けについてのお知らせです",
                 "【ヤマト運輸】お荷物のお届けについて、LINEで「yamato-help」を友だち追加してください",
                 "【国税庁】還付金があります。このメールに返信してください",
                 "【日本郵便】お届けについてご案内します。このメッセージに返信してください"]:
        r = tr.judge(text, LEDGER)
        assert r["level"] == "amber" and _codes(r) == ["nothing_to_check"], (text, r["reasons"])


def test_something_matched_stays_green():
    # 何か1つでも割符が合えば これまでどおり青（台帳にある会社・公式の住所）
    for text, code in [("【楽天カード】いつもご利用ありがとうございます", "in_ledger"),
                       ("【ヤマト運輸】お届け予定のお知らせ https://www.kuronekoyamato.co.jp/", "official")]:
        r = tr.judge(text, LEDGER)
        assert r["level"] == "green" and _codes(r) == [code], (text, r["reasons"])
