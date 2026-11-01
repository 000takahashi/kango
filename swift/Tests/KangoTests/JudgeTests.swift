import XCTest
@testable import Kango

/// python/tests/test_judge.py と同じ見本で、同じ判定になることを固定する。
final class JudgeTests: XCTestCase {
    let ledger: Set<String> = ["amazon", "rakuten", "docomo", "yucho"]

    func codes(_ v: Verdict) -> [String] { v.reasons.map(\.code) }

    func testCatalogLoads() {
        XCTAssertTrue(Catalog.bundled.contains { $0.id == "amazon" })
        XCTAssertTrue(Catalog.bundled.contains { $0.id == "yamato" && $0.kind == .everyone })
    }

    func testFakeAmazonLookalikeIsRed() {
        let v = Judge.judge(text: "【Amazon】24時間以内にお支払い情報を更新しないと停止 https://amazon-co-jp.account-verify.top/login", ledger: ledger)
        XCTAssertEqual(v.level, .red)
        XCTAssertTrue(codes(v).contains("mimic"))
        XCTAssertTrue(codes(v).contains("pressure"))
    }

    func testDigitLookalikeIsRed() {
        let v = Judge.judge(text: "お荷物のお届けについて https://rakut3n-pay.com/", ledger: ledger)
        XCTAssertEqual(v.level, .red)
        XCTAssertTrue(codes(v).contains("mimic"))
    }

    func testDeliveryWithoutNameButMimicHostIsRed() {
        let v = Judge.judge(text: "お荷物を持ち帰りました。 http://kuroneko-yamato.delivery-jp.xyz/track", ledger: ledger)
        XCTAssertEqual(v.level, .red)
    }

    func testBrandNotInLedgerIsRed() {
        let v = Judge.judge(text: "【三菱UFJ銀行】口座が凍結されています https://www.bk.mufg.jp/", ledger: ledger)
        XCTAssertEqual(v.level, .red)
        XCTAssertTrue(codes(v).contains("not_in_ledger"))
    }

    func testOfficialAndInLedgerIsGreenWithoutAssertingGenuine() {
        let v = Judge.judge(text: "【楽天カード】ご請求額が確定しました https://www.rakuten-card.co.jp/e-navi/", ledger: ledger)
        XCTAssertEqual(v.level, .green)
        XCTAssertTrue(v.helplines.isEmpty)
        let words = v.head + v.todo + v.reasons.map(\.text).joined()
        XCTAssertFalse(words.contains("本物"))
        XCTAssertFalse(words.contains("安全"))
    }

    func testOfficialSubsidiaryDomainsAreNotRed() {
        // 各社の公式ページで確かめた住所（2026-10-31）＝ここが赤になると本物の連絡を偽物と言ってしまう（Python と同じ見本）
        let all = Set(Catalog.bundled.map(\.id))
        let cases: [(String, String)] = [
            ("三井住友カード", "contact.vpass.ne.jp"), ("楽天カード", "support.rakuten-card.jp"),
            ("PayPay", "paypay.co.jp"), ("JCB", "www.global.jcb"), ("ドコモ", "www.nttdocomo.co.jp"),
            ("au ID", "id.auone.jp"), ("ワイモバイル", "www.ymobile.jp"), ("メルペイ", "jp.merpay.com"),
        ]
        for (name, host) in cases {
            let v = Judge.judge(text: "【\(name)】ご確認 https://\(host)/", ledger: all)
            XCTAssertEqual(v.level, .green, "\(name) \(host)")
        }
    }

    func testShortenerAndIDN() {
        XCTAssertEqual(Judge.judge(text: "Amazon https://bit.ly/abc", ledger: ledger).level, .amber)
        XCTAssertEqual(Judge.judge(text: "Amazon https://xn--amazn-mua.com/", ledger: ledger).level, .red)
    }

    func testFullWidthTextIsNormalized() {
        // 全角で書かれた名乗りとURLも同じに読む
        let v = Judge.judge(text: "【ＡＭＡＺＯＮ】ご注文 ｈｔｔｐｓ://ａｍａｚｏｎ.ｃｏ.ｊｐ/", ledger: ledger)
        XCTAssertEqual(v.level, .green)
    }

    func testPhoneNumberIsAmberEvenForLedgerBrand() {
        // 番号が本物かは確かめられない＝台帳にある会社を名乗っていても青にしない
        for text in [
            "【楽天カード】ご利用確認のため、0120-123-456 までお電話ください",
            "【楽天カード】お問い合わせは０１２０－１２３－４５６へ",
            "【楽天カード】(03) 1234-5678 までお電話ください",
            "【楽天カード】海外からは +81-3-1234-5678 へ",
            "【ヤマト運輸】お荷物のお届けについて、090-1234-5678 までご連絡ください",
        ] {
            let v = Judge.judge(text: text, ledger: ledger)
            XCTAssertEqual(v.level, .amber, text)
            XCTAssertTrue(codes(v).contains("phone"), text)
        }
    }

    func testNumbersThatAreNotPhoneNumbers() {
        // 日付・郵便番号・時刻・金額・注文番号・リンクの中の数字は、電話番号として数えない
        for text in [
            "【楽天カード】ご請求額が確定しました（2026-11-01）〒060-0001 受付 9:00-18:00 ¥10,000 https://www.rakuten-card.co.jp/",
            "【楽天カード】ご確認 https://www.rakuten-card.co.jp/e-navi/?id=0312345678",
            "【楽天カード】注文番号 012345678901234 https://www.rakuten-card.co.jp/",
            "【Amazon】ご注文 250-1234567-1234567 https://www.amazon.co.jp/",
        ] {
            let v = Judge.judge(text: text, ledger: ledger)
            XCTAssertEqual(v.level, .green, text)
            XCTAssertFalse(codes(v).contains("phone"), text)
        }
    }

    func testNothingToCheckIsAmber() {
        // 配送・郵便・国税庁（誰にでも届く会社）はリンクの住所でしか確かめられない＝リンクが無ければ何も照合していない＝青にしない
        for text in [
            "【ヤマト運輸】お荷物のお届けについてのお知らせです",
            "【ヤマト運輸】お荷物のお届けについて、LINEで「yamato-help」を友だち追加してください",
            "【国税庁】還付金があります。このメールに返信してください",
            "【日本郵便】お届けについてご案内します。このメッセージに返信してください",
        ] {
            let v = Judge.judge(text: text, ledger: ledger)
            XCTAssertEqual(v.level, .amber, text)
            XCTAssertEqual(codes(v), ["nothing_to_check"], text)
        }
    }

    func testSomethingMatchedStaysGreen() {
        // 何か1つでも割符が合えば これまでどおり青（台帳にある会社・公式の住所）
        for (text, code) in [
            ("【楽天カード】いつもご利用ありがとうございます", "in_ledger"),
            ("【ヤマト運輸】お届け予定のお知らせ https://www.kuronekoyamato.co.jp/", "official"),
        ] {
            let v = Judge.judge(text: text, ledger: ledger)
            XCTAssertEqual(v.level, .green, text)
            XCTAssertEqual(codes(v), [code], text)
        }
    }

    func testDisguisedLinksShowTheRealDestination() {
        // 「@」や「\」で本当の行き先をごまかす書き方・壊れた住所＝ブラウザが実際に開く住所で照合する
        let cases: [(String, String, String)] = [
            ("【楽天カード】ご確認 https://www.rakuten-card.co.jp:443@evil.example/login", "evil.example", "disguised"),
            ("【楽天カード】ご確認 https://evil.example\\@www.rakuten-card.co.jp/login", "evil.example", "disguised"),
            ("【楽天カード】ご確認 https://evil.example@www.rakuten-card.co.jp/login", "www.rakuten-card.co.jp", "disguised"),
            ("【楽天カード】ご確認 https:/evil.example/login", "evil.example", "off_domain"),
            ("【楽天カード】ご確認 https://evil.example%2f.rakuten-card.co.jp/login", "evil.example%2f.rakuten-card.co.jp", "idn"),
        ]
        for (text, host, code) in cases {
            let v = Judge.judge(text: text, ledger: ledger)
            XCTAssertEqual(v.level, .red, text)
            XCTAssertTrue(codes(v).contains(code), text)
            XCTAssertEqual(v.hosts, [host], text)
        }
    }

    func testLinksWithoutSchemeAreChecked() {
        // https:// の無いリンクも、メッセージアプリでは押せる＝住所として照合する
        let cases: [(String, Verdict.Level, String)] = [
            ("【楽天カード】ご利用確認はこちら rakuten-card-login.com", .red, "mimic"),
            ("【楽天カード】ご利用確認 www.rakuten-card.co.jp.evil.example/abc", .red, "mimic"),
            ("【Amazon】ご注文の確認は Amazon.co.jp で", .green, "official"),
        ]
        for (text, level, code) in cases {
            let v = Judge.judge(text: text, ledger: ledger)
            XCTAssertEqual(v.level, level, text)
            XCTAssertTrue(codes(v).contains(code), text)
        }
    }

    func testThingsThatAreNotLinks() {
        // ファイル名・メールアドレス・略語・文末の「。」「、」・https:// の無いリンクの中の数字は、読み違えない
        for text in [
            "【楽天カード】明細（meisai.pdf）をご確認ください",
            "【楽天カード】お問い合わせは support@rakuten-card.co.jp まで",
            "【楽天カード】ver.2.0 の新機能。e.g. や No.1 など",
            "【楽天カード】詳しくはこちら：https://www.rakuten-card.co.jp。",
            "【楽天カード】ご確認 https://www.rakuten-card.co.jp、ご不明点はアプリで",
            "【楽天カード】ご確認 rakuten-card.co.jp/e-navi/?id=0312345678",
        ] {
            let v = Judge.judge(text: text, ledger: ledger)
            XCTAssertEqual(v.level, .green, text)
        }
    }
}
