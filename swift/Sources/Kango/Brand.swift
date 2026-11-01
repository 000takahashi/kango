import Foundation

/// 会社（名乗られる側）。一覧の正は data/brands.csv（scripts/sync_brands.py で写す）。
public struct Brand: Codable, Hashable, Identifiable, Sendable {
    public enum Kind: String, Codable, Sendable {
        /// 契約がなければ名乗る理由がない会社（銀行・カード・通販・携帯）
        case contract
        /// だれにでも連絡が来うる相手（配送・郵便・役所）＝台帳を見ずにリンク先だけで判定
        case everyone
    }

    public let id: String
    public let name: String
    public let kind: Kind
    public let words: [String]
    public let domains: [String]
    public let stems: [String]
    /// 公式ドメインを各社のサイトで確かめた日（未確認は nil）
    public let checked: String?
}

public enum Catalog {
    /// アプリに同梱した会社一覧
    public static let bundled: [Brand] = {
        guard let url = Bundle.module.url(forResource: "brands", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let brands = try? JSONDecoder().decode([Brand].self, from: data) else { return [] }
        return brands
    }()
}
