import Foundation
import XCTest
@testable import Kango

/// 共通の見本（conformance/cases.json）を、すべて動かして確かめる。
/// Python の python/tests/test_conformance.py も、同じ見本を動かす。見本を足す時は cases.json に足す（説明は conformance/README.md）。
final class ConformanceTests: XCTestCase {
    struct Cases: Decodable {
        let ledger: [String]
        let cases: [Case]
    }

    struct Case: Decodable {
        let note: String
        let text: String
        let ledger: [String]?
        let level: String
        let codes: [String]
        let claimed: [String]
        let hosts: [String]
    }

    static let levels: [String: Verdict.Level] = ["green": .green, "amber": .amber, "red": .red]

    static func loadCases() throws -> Cases {
        // このファイル（swift/Tests/KangoTests/ConformanceTests.swift）から4つ上がリポジトリのいちばん上
        let root = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent().deletingLastPathComponent()
            .deletingLastPathComponent().deletingLastPathComponent()
        let data = try Data(contentsOf: root.appendingPathComponent("conformance/cases.json"))
        return try JSONDecoder().decode(Cases.self, from: data)
    }

    func testEveryCase() throws {
        let all = try Self.loadCases()
        XCTAssertGreaterThanOrEqual(all.cases.count, 40, "見本が読めていません")
        for c in all.cases {
            let label = "\(c.note)：\(c.text)"
            let want = try XCTUnwrap(Self.levels[c.level], label)
            let v = Judge.judge(text: c.text, ledger: Set(c.ledger ?? all.ledger))
            XCTAssertEqual(v.level, want, label)
            XCTAssertEqual(v.reasons.map(\.code), c.codes, label)
            XCTAssertEqual(v.claimed, c.claimed, label)
            XCTAssertEqual(v.hosts, c.hosts, label)
        }
    }
}
