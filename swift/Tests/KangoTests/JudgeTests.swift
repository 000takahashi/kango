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
}
