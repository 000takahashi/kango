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
}
