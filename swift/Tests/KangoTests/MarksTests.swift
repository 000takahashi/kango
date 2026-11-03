import Foundation
import XCTest
@testable import Kango

/// 行の印の共通の見本（conformance/marks.json）を、すべて動かして確かめる。
/// Python の python/tests/test_marks.py も、同じ見本を動かす。
final class MarksTests: XCTestCase {
    struct Cases: Decodable {
        let ledger: [String]
        let cases: [Case]
    }

    struct Case: Decodable {
        let note: String
        let lines: [String]
        let ledger: [String]?
        let marks: [Want]
    }

    struct Want: Decodable, Equatable {
        let line: Int
        let level: String
        let codes: [String]
    }

    static let names: [Verdict.Level: String] = [.green: "green", .amber: "amber", .red: "red"]

    func testEveryCase() throws {
        // このファイル（swift/Tests/KangoTests/MarksTests.swift）から4つ上がリポジトリのいちばん上
        let root = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent().deletingLastPathComponent()
            .deletingLastPathComponent().deletingLastPathComponent()
        let data = try Data(contentsOf: root.appendingPathComponent("conformance/marks.json"))
        let all = try JSONDecoder().decode(Cases.self, from: data)
        XCTAssertGreaterThanOrEqual(all.cases.count, 8, "見本が読めていません")
        for c in all.cases {
            let ledger = Set(c.ledger ?? all.ledger)
            let got = Judge.marks(lines: c.lines, ledger: ledger)
            XCTAssertEqual(got.map { Want(line: $0.line, level: Self.names[$0.level] ?? "", codes: $0.codes) }, c.marks, c.note)
            for m in got {
                XCTAssertNotEqual(m.level, .green, c.note)
                XCTAssertEqual(m.labels.count, m.codes.count, c.note)
            }
        }
    }
}
