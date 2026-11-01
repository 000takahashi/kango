import XCTest
@testable import Kango

/// 見本の形では書けない約束を確かめる（python/tests/test_judge.py と同じこと）。
/// 色と理由のコードは、ConformanceTests.swift が共通の見本（conformance/cases.json）で確かめている。
final class JudgeTests: XCTestCase {
    func verdicts() throws -> [(text: String, verdict: Verdict)] {
        let all = try ConformanceTests.loadCases()
        return all.cases.map { c in (text: c.text, verdict: Judge.judge(text: c.text, ledger: Set(c.ledger ?? all.ledger))) }
    }

    func testCatalogLoads() {
        XCTAssertTrue(Catalog.bundled.contains { $0.id == "amazon" && $0.kind == .contract })
        XCTAssertTrue(Catalog.bundled.contains { $0.id == "yamato" && $0.kind == .everyone })
    }

    func testGreenNeverSaysGenuineOrSafe() throws {
        // 青は「割符が合いました」まで。「本物です」「安全です」とは言わない
        for (text, v) in try verdicts() where v.level == .green {
            let words = v.head + v.todo + v.reasons.map(\.text).joined()
            XCTAssertFalse(words.contains("本物"), text)
            XCTAssertFalse(words.contains("安全"), text)
        }
    }

    func testHelplinesUnlessGreen() throws {
        // 青以外では、相談先（#9110・188）を添える
        for (text, v) in try verdicts() {
            XCTAssertEqual(v.helplines.map(\.tel), v.level == .green ? [] : ["#9110", "188"], text)
        }
    }
}
