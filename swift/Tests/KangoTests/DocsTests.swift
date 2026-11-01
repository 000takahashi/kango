import Foundation
import XCTest
@testable import Kango

/// docs/threat-model.md の表（手口と勘合の答え）が、勘合の本当の答えと同じかを確かめる。
/// 表を直したのに勘合と食い違っていたら、ここで落ちる（python/tests/test_docs.py と同じ確かめ方）。
final class DocsTests: XCTestCase {
    let ledger: Set<String> = ["amazon", "rakuten", "docomo", "yucho"]
    let levels: [String: Verdict.Level] = ["青": .green, "黄": .amber, "赤": .red]

    func testThreatModelTableMatchesJudge() throws {
        // このファイル（swift/Tests/KangoTests/DocsTests.swift）から4つ上がリポジトリのいちばん上
        let root = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent().deletingLastPathComponent()
            .deletingLastPathComponent().deletingLastPathComponent()
        let doc = try String(contentsOf: root.appendingPathComponent("docs/threat-model.md"), encoding: .utf8)
        var rows = 0
        // | 手口 | `文面の例` | 答え | `理由のコード` … | の行を読む
        for line in doc.components(separatedBy: "\n") where line.hasPrefix("|") {
            let cells = line.components(separatedBy: "|").map { $0.trimmingCharacters(in: .whitespaces) }
            guard cells.count >= 6, let level = levels[cells[3]] else { continue }
            let example = cells[2].components(separatedBy: "`")
            guard example.count >= 3 else { continue }
            let text = example[1]
            let codes = cells[4].components(separatedBy: "`").enumerated().filter { $0.offset % 2 == 1 }.map(\.element)
            let v = Judge.judge(text: text, ledger: ledger)
            XCTAssertEqual(v.level, level, text)
            XCTAssertEqual(v.reasons.map(\.code), codes, text)
            rows += 1
        }
        XCTAssertGreaterThanOrEqual(rows, 20, "表が読めていません")
    }
}
